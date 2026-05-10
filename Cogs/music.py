import re
import random
import discord
import lavalink
from discord.ext import commands
from lavalink.errors import ClientError
from lavalink.events import QueueEndEvent
from lavalink.server import LoadType
import asyncio
import fileProcessing

url_rx = re.compile(r'https?://(?:www\.)?.+')

config = fileProcessing.read_config()
roles = config["roles"]
voice_permissions_check_list = config["voice_permission_check_list"]


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
                password='changeme123',
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

        if not hasattr(bot, 'lavalink'):
            bot.lavalink = lavalink.Client(bot.user.id)
            bot.lavalink.add_node(
                host='127.0.0.1', port=2333, password='changeme123', region='us', name='default-node')

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
        query = query.strip('<>')

        if not url_rx.match(query):
            query = f'ytsearch:{query}'

        results = await player.node.get_tracks(query)

        if not results or not results.tracks:
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
        if songlist == False:
            return await ctx.send("Playlist not found.")
        await ctx.invoke(self.bot.get_command('play'), query=songlist[0])
        songlist.pop(0)

        player = self.bot.lavalink.player_manager.get(ctx.guild.id)
        for song in songlist:
            try:
                query = f'ytsearch:{song}'
                results = await player.node.get_tracks(query)
                if not results or not results.tracks:
                    continue
                track = results.tracks[0]
                track.extra["requester"] = ctx.author.id
                player.add(track=track)
            except Exception as error:
                print(error)

        await ctx.send(str(playlist_name) + " loaded successfully.")

        if not player.is_playing:
            await player.play()

    @commands.command(name='skip', description="Skips currently playing song.")
    @commands.has_any_role(*roles)
    async def skip_song(self, ctx, amount: int = 1):
        try:
            player = self.bot.lavalink.player_manager.get(ctx.guild.id)
            while (amount > 0):
                amount -= 1
                if not player.is_playing:
                    raise commands.CommandInvokeError(
                        "Nothing playing to skip.")
                else:
                    if amount % 2 == 0:
                        await asyncio.sleep(.1)
                    await player.skip()
                    if amount == 0:
                        await ctx.send("Song skipped.")
        except:
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
        try:
            player = self.bot.lavalink.player_manager.get(ctx.guild.id)
            if player.is_playing:
                status = True
                await ctx.send("Song has been paused.")
                await player.set_pause(True)
                for i in range(84):
                    await asyncio.sleep(5)
                    if not player.paused:
                        status = False
                        break

                if player.paused and player.is_playing and status is True:
                    await player.set_pause(False)
                    await ctx.send("Automatically unpaused.")

            else:
                await ctx.send("No song is playing to be paused.")
        except:
            raise commands.CommandInvokeError("Unable to retrieve player...")

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
        try:
            player = self.bot.lavalink.player_manager.get(ctx.guild.id)
            if player.is_playing:
                songlist = player.queue
                size = len(songlist)
                for x in range(0, size):
                    if (x % 8 == 0):
                        await asyncio.sleep(0.1)
                    temp = songlist[x]
                    randnum = random.randint(0, size - 1)
                    songlist[x] = songlist[randnum]
                    songlist[randnum] = temp
                await ctx.send("Finished.")
            else:
                raise commands.CommandInvokeError("Nothing playing!")

        except Exception:
            await ctx.send("Shuffle failed. Nothing may be queued.")

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
