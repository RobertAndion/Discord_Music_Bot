import os
import re
import random
import logging
import discord
import lavalink
from discord.ext import commands
from lavalink.errors import ClientError
from lavalink.events import QueueEndEvent, TrackExceptionEvent, TrackStuckEvent
from lavalink.server import LoadType
import asyncio
import fileProcessing

log = logging.getLogger(__name__)

url_rx = re.compile(r'https?://(?:www\.)?.+')

# Default source for plain (non-URL) searches. SoundCloud, because YouTube
# blocks datacenter IPs. Keep this as the single source of truth so switching
# sources later is a one-line change.
SEARCH_PREFIX = 'scsearch:'

# Transient node/network hiccups when loading a track are common; retry a few
# times with a short backoff before giving up.
TRACK_LOAD_RETRIES = 2
TRACK_LOAD_BACKOFF = 0.5

config = fileProcessing.read_config()
roles = config["roles"]
voice_permissions_check_list = config["voice_permission_check_list"]
lavalink_password = os.getenv('LAVALINK_PASSWORD', 'changeme123')


class LavalinkVoiceClient(discord.VoiceProtocol):
    def __init__(self, client: discord.Client, channel: discord.abc.Connectable):
        self.client = client
        self.channel = channel
        self.guild_id = channel.guild.id
        self._destroyed = False

        if not hasattr(self.client, 'lavalink'):
            self.client.lavalink = lavalink.Client(client.user.id)
            self.client.lavalink.add_node(
                host='localhost',
                port=2333,
                password=lavalink_password,
                region='us',
                name='default-node'
            )

        self.lavalink = self.client.lavalink

    async def on_voice_server_update(self, data):
        lavalink_data = {
            't': 'VOICE_SERVER_UPDATE',
            'd': data
        }
        await self.lavalink.voice_update_handler(lavalink_data)

    async def on_voice_state_update(self, data):
        channel_id = data['channel_id']

        if not channel_id:
            await self._destroy()
            return

        channel = self.client.get_channel(int(channel_id))
        if channel is not None:
            self.channel = channel

        lavalink_data = {
            't': 'VOICE_STATE_UPDATE',
            'd': data
        }
        await self.lavalink.voice_update_handler(lavalink_data)

    async def connect(self, *, timeout: float, reconnect: bool, self_deaf: bool = False, self_mute: bool = False) -> None:
        self.lavalink.player_manager.create(guild_id=self.channel.guild.id)
        await self.channel.guild.change_voice_state(channel=self.channel, self_mute=self_mute, self_deaf=self_deaf)

    async def disconnect(self, *, force: bool = False) -> None:
        player = self.lavalink.player_manager.get(self.channel.guild.id)

        if player is None or (not force and not player.is_connected):
            return

        await self.channel.guild.change_voice_state(channel=None)

        player.channel_id = None
        await self._destroy()

    async def _destroy(self):
        self.cleanup()

        if self._destroyed:
            return

        self._destroyed = True

        try:
            await self.lavalink.player_manager.destroy(self.guild_id)
        except ClientError:
            pass


class music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._auto_unpause_guilds: set = set()

        if not hasattr(bot, 'lavalink'):
            bot.lavalink = lavalink.Client(bot.user.id)
            bot.lavalink.add_node(
                host='127.0.0.1', port=2333, password=lavalink_password, region='us', name='default-node')

        self.lavalink: lavalink.Client = bot.lavalink
        self.lavalink.add_event_hooks(self)

    def cog_unload(self):
        self.lavalink._event_hooks.clear()

    async def cog_before_invoke(self, ctx):
        guild_check = ctx.guild is not None

        if guild_check:
            await self.ensure_voice(ctx)

        return guild_check

    async def cog_command_error(self, ctx, error):
        if isinstance(error, commands.CommandInvokeError):
            await ctx.send(error.original)

    async def ensure_voice(self, ctx):
        player = self.bot.lavalink.player_manager.create(ctx.guild.id)

        should_connect = ctx.command.name in voice_permissions_check_list

        if not ctx.author.voice or not ctx.author.voice.channel:
            raise commands.CommandInvokeError('Join a voicechannel first.')

        v_client = ctx.voice_client
        if not v_client:
            if not should_connect:
                raise commands.CommandInvokeError('Not connected.')

            permissions = ctx.author.voice.channel.permissions_for(ctx.me)

            if not permissions.connect or not permissions.speak:
                raise commands.CommandInvokeError(
                    'I need the `CONNECT` and `SPEAK` permissions.')

            player.store('channel', ctx.channel.id)
            await ctx.author.voice.channel.connect(cls=LavalinkVoiceClient)
        else:
            if v_client.channel.id != ctx.author.voice.channel.id:
                raise commands.CommandInvokeError(
                    'You need to be in my voicechannel.')

    def _player_channel(self, player):
        """The text channel a player was started from, if we still can see it."""
        channel_id = player.fetch('channel')
        return self.bot.get_channel(channel_id) if channel_id else None

    async def _load_tracks(self, player, query):
        """Load tracks for a query, retrying transient node/network failures.

        Returns the results object (which may still have no tracks for a search
        that genuinely found nothing) or None if every attempt raised.
        """
        for attempt in range(TRACK_LOAD_RETRIES + 1):
            try:
                return await player.node.get_tracks(query)
            except Exception as exc:
                log.warning(
                    "Track load error for %r (attempt %d/%d): %s",
                    query, attempt + 1, TRACK_LOAD_RETRIES + 1, exc)
                if attempt < TRACK_LOAD_RETRIES:
                    await asyncio.sleep(TRACK_LOAD_BACKOFF * (attempt + 1))
        return None

    async def _notify_skip(self, player, track, reason):
        """Tell the channel we're skipping a track that couldn't be played."""
        title = getattr(track, 'title', None) or 'that track'
        log.warning("Skipping %s: %s", title, reason)
        channel = self._player_channel(player)
        if channel is not None:
            try:
                await channel.send(
                    f"⚠️ Couldn't play **{title}** ({reason}). Skipping.")
            except discord.HTTPException:
                pass

    @lavalink.listener(TrackExceptionEvent)
    async def on_track_exception(self, event: TrackExceptionEvent):
        # A track failed to stream (e.g. a SoundCloud 404). Lavalink ends it
        # with LOAD_FAILED and auto-advances to the next queued track, so we
        # only need to let the users know why it was skipped.
        await self._notify_skip(
            event.player, event.track,
            getattr(event, 'message', None) or 'source error')

    @lavalink.listener(TrackStuckEvent)
    async def on_track_stuck(self, event: TrackStuckEvent):
        # Stuck tracks don't auto-advance, so skip past them ourselves.
        await self._notify_skip(event.player, event.track, 'stalled')
        try:
            await event.player.skip()
        except Exception as exc:
            log.warning("Failed to skip stuck track: %s", exc)

    @lavalink.listener(QueueEndEvent)
    async def on_queue_end(self, event: QueueEndEvent):
        guild_id = event.player.guild_id
        guild = self.bot.get_guild(guild_id)

        if guild is not None and guild.voice_client is not None:
            await guild.voice_client.disconnect(force=True)

    @commands.command(name='play', description=".play {song name} to play a song, will connect the bot.")
    @commands.has_any_role(*roles)
    async def play_song(self, ctx, *, query: str):
        fileProcessing.logUpdate(ctx, query)
        player = self.bot.lavalink.player_manager.get(ctx.guild.id)
        # Keep the channel current so skip/failure notices land where the user
        # is actually talking, even across reconnects.
        player.store('channel', ctx.channel.id)
        query = query.strip('<>')

        if not url_rx.match(query):
            query = f'{SEARCH_PREFIX}{query}'

        results = await self._load_tracks(player, query)

        if results is None:
            return await ctx.send("The music server isn't responding right now — try again in a moment.")

        if not results.tracks:
            return await ctx.send('Nothing found!')

        embed = discord.Embed(color=discord.Color.blurple())

        if results.load_type == LoadType.PLAYLIST:
            tracks = results.tracks

            for track in tracks:
                track.extra["requester"] = ctx.author.id
                player.add(track=track)

            embed.title = 'Playlist Enqueued!'
            embed.description = f'{results.playlist_info.name} - {len(tracks)} tracks'
        else:
            track = results.tracks[0]
            embed.title = 'Track Enqueued'
            embed.description = f'[{track.title}]({track.uri})'

            track.extra["requester"] = ctx.author.id
            player.add(track=track)

        await ctx.send(embed=embed)

        if not player.is_playing:
            await player.play()

    @commands.command(name="playfromlist", aliases=["pfpl", "playl"], description="Loads a playlist into the queue to be played.")
    @commands.has_any_role(*roles)
    async def play_from_list(self, ctx, *, playlist_name):
        fileProcessing.logUpdate(ctx, playlist_name)
        songlist = fileProcessing.play_playlist(ctx, playlist_name)
        if songlist is False:
            return await ctx.send("Playlist not found.")
        await ctx.invoke(self.bot.get_command('play'), query=songlist[0])
        songlist.pop(0)

        player = self.bot.lavalink.player_manager.get(ctx.guild.id)
        skipped = 0
        for song in songlist:
            results = await self._load_tracks(player, f'{SEARCH_PREFIX}{song}')
            if results is None or not results.tracks:
                skipped += 1
                continue
            track = results.tracks[0]
            track.extra["requester"] = ctx.author.id
            player.add(track=track)

        message = f"{playlist_name} loaded successfully."
        if skipped:
            message += f" ({skipped} song(s) couldn't be found and were skipped.)"
        await ctx.send(message)

        if not player.is_playing:
            await player.play()

    @commands.command(name='skip', description="Skips currently playing song.")
    @commands.has_any_role(*roles)
    async def skip_song(self, ctx, amount: int = 1):
        try:
            player = self.bot.lavalink.player_manager.get(ctx.guild.id)
            while amount > 0:
                amount -= 1
                if not player.is_playing:
                    raise commands.CommandInvokeError("Nothing playing to skip.")
                if amount % 2 == 0:
                    await asyncio.sleep(.1)
                await player.skip()
                if amount == 0:
                    await ctx.send("Song skipped.")
        except Exception:
            if amount > 0:
                return await ctx.send("All songs skipped")

    @commands.command(name="clear", description="Clears all of the currently playing songs and makes the bot disconnect.")
    @commands.has_any_role(*roles)
    async def clear_queue(self, ctx):
        player = self.bot.lavalink.player_manager.get(ctx.guild.id)

        if not ctx.voice_client:
            return await ctx.send('Not connected.')

        if not ctx.author.voice or (player.is_connected and ctx.author.voice.channel.id != int(player.channel_id)):
            return await ctx.send('You\'re not in my voicechannel!')

        await player.stop()

        await ctx.voice_client.disconnect(force=True)
        await ctx.send('Queue was cleared.')

    @commands.command(name='pause', aliases=["ps"], description="Pauses a song if one is playing.")
    @commands.has_any_role(*roles)
    async def pause_bot(self, ctx):
        player = self.bot.lavalink.player_manager.get(ctx.guild.id)
        if not player:
            raise commands.CommandInvokeError("Unable to retrieve player...")
        if not player.is_playing:
            return await ctx.send("No song is playing to be paused.")
        if ctx.guild.id in self._auto_unpause_guilds:
            return await ctx.send("Song is already paused.")

        self._auto_unpause_guilds.add(ctx.guild.id)
        await player.set_pause(True)
        await ctx.send("Song has been paused.")
        try:
            for _ in range(84):
                await asyncio.sleep(5)
                if not player.paused:
                    break
            else:
                if player.is_playing:
                    await player.set_pause(False)
                    await ctx.send("Automatically unpaused.")
        finally:
            self._auto_unpause_guilds.discard(ctx.guild.id)

    @commands.command(name='unpause', aliases=['resume', 'start', 'up'], description="Unpauses a paused song.")
    @commands.has_any_role(*roles)
    async def unpause_bot(self, ctx):
        player = self.bot.lavalink.player_manager.get(ctx.guild.id)
        if not player:
            raise commands.CommandInvokeError("Nothing playing.")
        if player.paused:
            await ctx.send("Resuming song.")
            await player.set_pause(False)
        else:
            raise commands.CommandInvokeError(
                "Nothing is paused to resume.")

    @commands.command(name='queue', aliases=['playlist', 'songlist', 'upnext'], description="Shows songs up next in order, with the currently playing at the top.")
    @commands.has_any_role(*roles)
    async def queue(self, ctx, page=1):

        if not isinstance(page, int):
            raise commands.CommandInvokeError("Please enter a valid number.")

        player = self.bot.lavalink.player_manager.get(ctx.guild.id)
        if player.is_playing:
            songlist = player.queue
            list_collection = []
            complete_list = ''
            complete_list = complete_list + "NP: " + \
                player.current.title + "\n"
            i = 0
            for song in songlist:
                complete_list = complete_list + f"{i + 1}: {song.title}\n"
                i = i + 1
                if i % 10 == 0:
                    list_collection.append(complete_list)
                    complete_list = ''

            if i % 10 != 0 or i == 0:
                list_collection.append(complete_list)

            selection = int(page - 1)
            embed = discord.Embed()
            embed.title = 'Queue'
            if selection < 0:
                list_collection[0] += "Page: 1/" + str(len(list_collection))
                embed.description = list_collection[0]
            elif selection > len(list_collection) - 1:
                list_collection[len(list_collection) - 1] += "Page: " + \
                    str(len(list_collection)) + "/" + str(len(list_collection))
                embed.description = list_collection[len(list_collection) - 1]
            else:
                list_collection[selection] += "Page: " + \
                    str(page) + "/" + str(len(list_collection))
                embed.description = list_collection[selection]
            await ctx.send(embed=embed)
        else:
            await ctx.send("Nothing is queued.")

    @commands.command(name="shuffle", description="Shuffles the current queue.")
    @commands.has_any_role(*roles)
    async def shuffle(self, ctx):
        player = self.bot.lavalink.player_manager.get(ctx.guild.id)
        if not player or not player.is_playing:
            return await ctx.send("Nothing playing to shuffle.")
        if not player.queue:
            return await ctx.send("Nothing queued to shuffle.")
        random.shuffle(player.queue)
        await ctx.send("Finished.")

    @commands.command(name='removequeue', aliases=['rq'], description="Removes a song from the queue by its position number.")
    @commands.has_any_role(*roles)
    async def remove_from_queue(self, ctx, position: int):
        player = self.bot.lavalink.player_manager.get(ctx.guild.id)

        if not player or not player.is_playing:
            return await ctx.send("Nothing is queued.")

        queue_length = len(player.queue)
        if queue_length == 0:
            return await ctx.send("There are no queued songs to remove.")

        if position < 1 or position > queue_length:
            return await ctx.send(f"Please provide a position between 1 and {queue_length}.")

        removed = player.queue.pop(position - 1)
        await ctx.send(f"Removed **{removed.title}** from the queue.")


async def setup(bot):
    await bot.add_cog(music(bot))
