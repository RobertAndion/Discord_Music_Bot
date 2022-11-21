import re
import random
import discord
import lavalink
from discord.ext import commands
import asyncio
import fileRead
url_rx = re.compile(r'https?://(?:www\.)?.+')


class LavalinkVoiceClient(discord.VoiceClient):
    def __init__(self, client: discord.Client, channel: discord.abc.Connectable):
        self.client = client
        self.channel = channel
        # ensure a client already exists
        if hasattr(self.client, 'lavalink'):
            self.lavalink = self.client.lavalink
        else:
            self.client.lavalink = lavalink.Client(client.user.id)
            self.client.lavalink.add_node(
                'localhost',
                2333,
                'youshallnotpass',
                'us',
                'default-node'
            )
            self.lavalink = self.client.lavalink

    async def on_voice_server_update(self, data):
        # the data needs to be transformed before being handed down to
        # voice_update_handler
        lavalink_data = {
            't': 'VOICE_SERVER_UPDATE',
            'd': data
        }
        await self.lavalink.voice_update_handler(lavalink_data)

    async def on_voice_state_update(self, data):
        # the data needs to be transformed before being handed down to
        # voice_update_handler
        lavalink_data = {
            't': 'VOICE_STATE_UPDATE',
            'd': data
        }
        await self.lavalink.voice_update_handler(lavalink_data)

    async def connect(self, *, timeout: float, reconnect: bool, self_deaf: bool = False, self_mute: bool = False) -> None:
        """
        Connect the bot to the voice channel and create a player_manager
        if it doesn't exist yet.
        """
        self.lavalink.player_manager.create(guild_id=self.channel.guild.id)
        await self.channel.guild.change_voice_state(channel=self.channel, self_mute=self_mute, self_deaf=self_deaf)

    async def disconnect(self, *, force: bool = False) -> None:
        """
        Handles the disconnect.
        Cleans up running player and leaves the voice client.
        """
        player = self.lavalink.player_manager.get(self.channel.guild.id)

        # no need to disconnect if we are not connected
        if not force and not player.is_connected:
            return

        # None means disconnect
        await self.channel.guild.change_voice_state(channel=None)

        # update the channel_id of the player to None
        # this must be done because the on_voice_state_update that would set channel_id
        # to None doesn't get dispatched after the disconnect
        player.channel_id = None
        self.cleanup()


class music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        # This ensures the client isn't overwritten during cog reloads.
        if not hasattr(bot, 'lavalink'):
            bot.lavalink = lavalink.Client(bot.user.id)
            # PASSWORD HERE MUST MATCH YML
            bot.lavalink.add_node(
                '127.0.0.1', 2333, 'changeme123', 'na', 'local_music_node')

        lavalink.add_event_hook(self.track_hook)

    def cog_unload(self):
        self.bot.lavalink._event_hooks.clear()

    async def cog_before_invoke(self, ctx):
        """ Command before-invoke handler. """
        guild_check = ctx.guild is not None

        if guild_check:
            await self.ensure_voice(ctx)

        return guild_check

    async def cog_command_error(self, ctx, error):
        if isinstance(error, commands.CommandInvokeError):
            await ctx.send(error.original)
            # The above handles errors thrown in this cog and shows them to the user.
            # This shouldn't be a problem as the only errors thrown in this cog are from `ensure_voice`
            # which contain a reason string, such as "Join a voicechannel" etc. You can modify the above
            # if you want to do things differently.

    async def ensure_voice(self, ctx):
        """ This check ensures that the bot and command author are in the same voicechannel. """
        player = self.bot.lavalink.player_manager.create(ctx.guild.id)

        should_connect = ctx.command.name in (
            'play', 'playfromlist', 'skip', 'pause', 'unpause', 'clear', 'shuffle')

        if not ctx.author.voice or not ctx.author.voice.channel:
            # Our cog_command_error handler catches this and sends it to the voicechannel.
            # Exceptions allow us to "short-circuit" command invocation via checks so the
            # execution state of the command goes no further.
            raise commands.CommandInvokeError('Join a voicechannel first.')

        v_client = ctx.voice_client
        if not v_client:
            if not should_connect:
                raise commands.CommandInvokeError('Not connected.')

            permissions = ctx.author.voice.channel.permissions_for(ctx.me)

            if not permissions.connect or not permissions.speak:  # Check user limit too?
                raise commands.CommandInvokeError(
                    'I need the `CONNECT` and `SPEAK` permissions.')

            player.store('channel', ctx.channel.id)
            await ctx.author.voice.channel.connect(cls=LavalinkVoiceClient)
        else:
            if v_client.channel.id != ctx.author.voice.channel.id:
                raise commands.CommandInvokeError(
                    'You need to be in my voicechannel.')

    async def track_hook(self, event):
        if isinstance(event, lavalink.events.QueueEndEvent):
            # When this track_hook receives a "QueueEndEvent" from lavalink.py
            # it indicates that there are no tracks left in the player's queue.
            # To save on resources, we can tell the bot to disconnect from the voicechannel.
            guild_id = event.player.guild_id
            guild = self.bot.get_guild(guild_id)
            await guild.voice_client.disconnect(force=True)

    # Allows for a song to be played, does not make sure people are in the same chat.
    @commands.command(name='play', description=".play {song name} to play a song, will connect the bot.")
    @commands.has_any_role('Dj', 'Administrator', 'DJ')
    async def play_song(self, ctx, *, query: str):
        player = self.bot.lavalink.player_manager.get(ctx.guild.id)
        query = query.strip('<>')

        if not url_rx.match(query):
            query = f'ytsearch:{query}'

        results = await player.node.get_tracks(query)

        if not results or not results.tracks:
            return await ctx.send('Nothing found!')

        embed = discord.Embed(color=discord.Color.blurple())

        # Valid loadTypes are:
        #   TRACK_LOADED    - single video/direct URL)
        #   PLAYLIST_LOADED - direct URL to playlist)
        #   SEARCH_RESULT   - query prefixed with either ytsearch: or scsearch:.
        #   NO_MATCHES      - query yielded no results
        #   LOAD_FAILED     - most likely, the video encountered an exception during loading.
        if results.load_type == 'PLAYLIST_LOADED':
            tracks = results.tracks

            for track in tracks:
                # Add all of the tracks from the playlist to the queue.
                player.add(requester=ctx.author.id, track=track)

            embed.title = 'Playlist Enqueued!'
            embed.description = f'{results.playlist_info.name} - {len(tracks)} tracks'
        else:
            track = results.tracks[0]
            embed.title = 'Track Enqueued'
            embed.description = f'[{track.title}]({track.uri})'

            player.add(requester=ctx.author.id, track=track)

        await ctx.send(embed=embed)

        if not player.is_playing:
            await player.play()

    # Needs work
    @commands.command(name="playfromlist", aliases=["pfpl", "playl"], description="Loads a playlist into the queue to be played.")
    @commands.has_any_role("Dj", "DJ", "Administrator")
    async def play_from_list(self, ctx, *, playlist_name):
        """ Searches and plays a song from a given query. """
        # Get the player for this guild from cache.
        songlist = fileRead.play_playlist(ctx, playlist_name)
        if songlist == False:
            return await ctx.channel.send("Playlist not found.")

        player = self.bot.lavalink.player_manager.get(ctx.guild.id)
        # This is to play a song up front so you dont have to wait for whole queue to hear music
        # Need to use this in a try catch to make the player disconnect or something.
        query = songlist[0]
        songlist.pop(0)
        query = f'ytsearch:{query}'
        results = await player.node.get_tracks(query)
        track = results['tracks'][0]
        track = lavalink.models.AudioTrack(
            track, ctx.author.id, recommended=True)
        player.add(requester=ctx.author.id, track=track)

        if not player.is_playing:
            await player.play()

        for track in songlist:  # Add all remaining songs to list.
            try:
                query = f'ytsearch:{track}'
                results = await player.node.get_tracks(query)
                track = results['tracks'][0]
                track = lavalink.models.AudioTrack(
                    track, ctx.author.id, recommended=True)
                player.add(requester=ctx.author.id, track=track)
            except Exception as error:  # Catches song not found
                print(error)

        await ctx.send(str(playlist_name) + " loaded successfully.")

        if not player.is_playing:
            await player.play()

    # skips currently playing song
    @commands.command(name='skip', description="Skips currently playing song.")
    @commands.has_any_role('Dj', 'Administrator', 'DJ')
    async def skip_song(self, ctx, amount: int = 1):
        try:
            player = self.bot.lavalink.player_manager.get(ctx.guild.id)
            while (amount > 0):
                amount -= 1
                if not player.is_playing:
                    raise commands.CommandInvokeError("Nothing playing to skip.")
                else:
                    if amount % 2 == 0:
                        await asyncio.sleep(.1) # Buffering for performance, testing needed to see if still neccessary.
                    await player.skip()
                    if amount == 0:  # make sure song skipped only prints once.
                        await ctx.channel.send("Song skipped.")
        except:
            if amount > 0:
                raise commands.CommandInvokeError("All songs skipped")
                
            raise commands.CommandInvokeError("Something went wrong...")

    @commands.command(name="clear", description="Clears all of the currently playing songs and makes the bot disconnect.")
    @commands.has_any_role("Dj", "DJ", "Administrator")
    async def clear_queue(self, ctx):
        try:
            player = self.bot.lavalink.player_manager.get(ctx.guild.id)
            if player.is_playing:
                player.queue.clear()
                await player.stop()
                await ctx.guild.change_voice_state(channel=None)
                await ctx.send("Songs Cleared.")
            else:
                await ctx.send("Nothing playing to clear.")
        except:
            await ctx.channel.send("Nothing playing.")

    @commands.command(name='pause', aliases=["ps"], description="Pauses a song if one is playing.")
    @commands.has_any_role('Dj', 'Administrator', 'DJ')
    async def pause_bot(self, ctx):
        try:
            player = self.bot.lavalink.player_manager.get(ctx.guild.id)
            if ctx.author.voice is not None and ctx.author.voice.channel.id == int(player.channel_id):
                if player.is_playing:
                    status = True
                    await ctx.channel.send("Song has been paused.")
                    await player.set_pause(True)
                    i = 0
                    while i < 84:  # This will periodically check to see if it has been unpaused
                        await asyncio.sleep(5)  # (84 * 5 = 7 minutes)
                        i = i + 1
                        # If its been unpaused no need to keep counting.
                        if not player.paused:
                            status = False
                            break

                    if player.paused and player.is_playing and status is True:
                        await player.set_pause(False)  # If paused unpause.
                        await ctx.channel.send("Automatically unpaused.")

                else:
                    await ctx.channel.send("No song is playing to be paused.")
            else:
                await ctx.channel.send("Please join the same voice channel as me.")
        except:
            await ctx.channel.send("Nothing playing.")

    @commands.command(name='unpause', aliases=['resume', 'start', 'up'], description="Unpauses a paused song.")
    @commands.has_any_role('Dj', 'Administrator', 'DJ')
    async def unpause_bot(self, ctx):
        try:
            player = self.bot.lavalink.player_manager.get(ctx.guild.id)
            if ctx.author.voice.channel.id == int(player.channel_id):
                if player.paused:
                    await ctx.channel.send("Resuming song.")
                    await player.set_pause(False)
                else:
                    await ctx.channel.send("Nothing is paused to resume.")
            else:
                await ctx.channel.send("Please join the same voice channel as me.")
        except:
            await ctx.channel.send("Nothing playing.")

    @commands.command(name='queue', aliases=['playlist', 'songlist', 'upnext'], description="Shows songs up next in order, with the currently playing at the top.")
    @commands.has_any_role('Dj', 'Administrator', 'DJ')
    async def queue(self, ctx, page=1):

        if not isinstance(page, int):
            raise commands.CommandInvokeError("Please enter a valid number.")

        player = self.bot.lavalink.player_manager.get(ctx.guild.id)
        if player.is_playing:
            songlist = player.queue
            list_collection = []
            complete_list = ''
            complete_list = complete_list + "NP: " + \
                player.current['title'] + "\n"
            i = 0
            for song in songlist:
                complete_list = complete_list + f"{i + 1}: {song['title']}\n"
                i = i + 1
                if i % 10 == 0:
                    list_collection.append(complete_list)
                    complete_list = ''

            # Check for the case where it is not a perfect multiple, add "half page" (< 10) or if there is only one song playing
            if i % 10 != 0 or i == 0:
                list_collection.append(complete_list)

            selection = int(page - 1)
            embed = discord.Embed()
            embed.title = 'Queue'
            # add an inital if to check if it is an int then do page -1 if its not int default to page 0
            if selection < 0:  # handle negative number
                list_collection[0] += "Page: 1/" + str(len(list_collection))
                embed.description = list_collection[0]
            # Handle a case where the index is greater than page amount
            elif selection > len(list_collection) - 1:
                list_collection[len(list_collection) - 1] += "Page: " + \
                    str(len(list_collection)) + "/" + str(len(list_collection))
                embed.description = list_collection[len(list_collection) - 1]
            else:  # Handle a valid input case.
                list_collection[selection] += "Page: " + \
                    str(page) + "/" + str(len(list_collection))
                embed.description = list_collection[selection]
            await ctx.channel.send(embed=embed)
        else:
            await ctx.channel.send("Nothing is queued.")

    @commands.command(name="shuffle", description="New shuffle function that has to be called once and makes a new queue. Result is shown on \"queue\" commands now..")
    @commands.has_any_role("Dj", "DJ", "Administrator")
    async def shuffle(self, ctx):
        try:
            player = self.bot.lavalink.player_manager.get(ctx.guild.id)
            if player.is_playing:
                songlist = player.queue
                # random.shuffle(songlist) # This breaks my bot at times.. Custom shuffle to slow this down.
                size = len(songlist)
                for x in range(0, size):
                    if (x % 8 == 0):
                        await asyncio.sleep(0.1)
                    temp = songlist[x]
                    randnum = random.randint(0, size - 1)
                    songlist[x] = songlist[randnum]
                    songlist[randnum] = temp
                await ctx.channel.send("Finished.")
            else:
                await ctx.channel.send("Nothing playing!")

        except Exception as error:
            print(error)

async def setup(bot):
    await bot.add_cog(music(bot))
