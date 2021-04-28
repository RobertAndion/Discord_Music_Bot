import re
import random
import discord
import lavalink
from discord.ext import commands
import asyncio
import fileRead
url_rx = re.compile(r'https?://(?:www\.)?.+')
"""
Robert A. USF Computer Science
A cog to hold all of the functions used to play music for the bot.
"""

class music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        if not hasattr(bot, 'lavalink'):  # This ensures the client isn't overwritten during cog reloads.
            bot.lavalink = lavalink.Client(bot.user.id)
            bot.lavalink.add_node('127.0.0.1', 2333, 'changeme123', 'na', 'local_music_node')  # PASSWORD HERE MUST MATCH YML
            bot.add_listener(bot.lavalink.voice_update_handler, 'on_socket_response')

        lavalink.add_event_hook(self.track_hook)

    def cog_unload(self):
        """ Cog unload handler. This removes any event hooks that were registered. """
        self.bot.lavalink._event_hooks.clear()

    async def cog_before_invoke(self, ctx):
        """ Command before-invoke handler. """
        guild_check = ctx.guild is not None
        #  This is essentially the same as `@commands.guild_only()`
        #  except it saves us repeating ourselves (and also a few lines).

        if guild_check:
            await self.ensure_voice(ctx)
            #  Ensure that the bot and command author share a mutual voicechannel.

        return guild_check

    async def cog_command_error(self, ctx, error):
        if isinstance(error, commands.CommandInvokeError):
            await ctx.send(error.original)
            # The above handles errors thrown in this cog and shows them to the user.

    async def ensure_voice(self, ctx):
        """ This check ensures that the bot and command author are in the same voicechannel. """
        player = self.bot.lavalink.player_manager.create(ctx.guild.id, endpoint=str(ctx.guild.region))

        should_connect = ctx.command.name in ('play','playfromlist')

        if not ctx.author.voice or not ctx.author.voice.channel:
            # Our cog_command_error handler catches this and sends it to the voicechannel.
            # Exceptions allow us to "short-circuit" command invocation via checks so the
            # execution state of the command goes no further.
            raise commands.CommandInvokeError('Join a voicechannel first.')

        if not player.is_connected:
            if not should_connect:
                raise commands.CommandInvokeError('Not connected.')

            permissions = ctx.author.voice.channel.permissions_for(ctx.me)

            if not permissions.connect or not permissions.speak:
                raise commands.CommandInvokeError('I need the `CONNECT` and `SPEAK` permissions.')

            player.store('channel', ctx.channel.id)
            await ctx.guild.change_voice_state(channel=ctx.author.voice.channel)
        else:
            if int(player.channel_id) != ctx.author.voice.channel.id:
                raise commands.CommandInvokeError('You need to be in my voicechannel.')

    async def track_hook(self, event):
        if isinstance(event, lavalink.events.QueueEndEvent):
            # When this track_hook receives a "QueueEndEvent" from lavalink.py
            # it indicates that there are no tracks left in the player's queue.
            # To save on resources, we can tell the bot to disconnect from the voicechannel.
            guild_id = int(event.player.guild_id)
            guild = self.bot.get_guild(guild_id)
            await guild.change_voice_state(channel=None)

    @commands.command(name = 'play', description=".play {song name} to play a song, will connect the bot.") #Allows for a song to be played, does not make sure people are in the same chat.
    @commands.has_any_role('Dj','Administrator','DJ')
    async def play_song(self, ctx, *, query):
        """ Searches and plays a song from a given query. """
        # Get the player for this guild from cache.
        player = self.bot.lavalink.player_manager.get(ctx.guild.id)
        query = query.strip('<>')
        # Check if the user input might be a URL. If it isn't, we can Lavalink do a YouTube search for it instead.
        if not url_rx.match(query):
            query = f'ytsearch:{query}'

        # Get the results for the query from Lavalink.
        results = await player.node.get_tracks(query)

        # Results could be None if Lavalink returns an invalid response (non-JSON/non-200 (OK)).
        # ALternatively, resullts['tracks'] could be an empty array if the query yielded no tracks.
        if not results or not results['tracks']:
            return await ctx.send('Nothing found!')

        embed = discord.Embed(color=discord.Color.blurple())

        # Valid loadTypes are:
        #   TRACK_LOADED    - single video/direct URL)
        #   PLAYLIST_LOADED - direct URL to playlist)
        #   SEARCH_RESULT   - query prefixed with either ytsearch: or scsearch:.
        #   NO_MATCHES      - query yielded no results
        #   LOAD_FAILED     - most likely, the video encountered an exception during loading.
        if results['loadType'] == 'PLAYLIST_LOADED':
            tracks = results['tracks']

            for track in tracks:
                # Add all of the tracks from the playlist to the queue.
                player.add(requester=ctx.author.id, track=track)

            embed.title = 'Playlist Enqueued!'
            embed.description = f'{results["playlistInfo"]["name"]} - {len(tracks)} tracks'
        else:
            track = results['tracks'][0]
            embed.title = 'Track Enqueued'
            embed.description = f'[{track["info"]["title"]}]({track["info"]["uri"]})'

            track = lavalink.models.AudioTrack(track, ctx.author.id, recommended=True)
            player.add(requester=ctx.author.id, track=track)

        await ctx.send(embed=embed)

        if not player.is_playing:
            await player.play()

    @commands.command(name="playfromlist",aliases = ["pfpl","playl"],description="Loads a playlist into the queue to be played.")
    @commands.has_any_role("Dj","DJ","Administrator")
    async def play_from_list(self,ctx,*,playlist_name):
        """ Searches and plays a song from a given query. """
        # Get the player for this guild from cache.
        songlist = fileRead.play_playlist(ctx,playlist_name) 
        if songlist == False:
            return await ctx.channel.send("Playlist not found.")

        player = self.bot.lavalink.player_manager.get(ctx.guild.id)
        # This is to play a song up front so you dont have to wait for whole queue to hear music
        #Need to use this in a try catch to make the player disconnect or something.
        query = songlist[0]
        songlist.pop(0)
        query = f'ytsearch:{query}'
        results = await player.node.get_tracks(query)
        track = results['tracks'][0]
        track = lavalink.models.AudioTrack(track, ctx.author.id, recommended=True)
        player.add(requester=ctx.author.id, track=track)

        if not player.is_playing:
            await player.play()

        for track in songlist: # Add all remaining songs to list.
            try:
                query = f'ytsearch:{track}'
                results = await player.node.get_tracks(query)
                track = results['tracks'][0]
                track = lavalink.models.AudioTrack(track, ctx.author.id, recommended=True)
                player.add(requester=ctx.author.id, track=track)
            except Exception as error: # Catches song not found
                print(error)

        await ctx.send("Playlist loaded successfully.")

        if not player.is_playing:
            await player.play()

    @commands.command(name = 'skip',description="Skips currently playing song.") #skips currently playing song
    @commands.has_any_role('Dj','Administrator','DJ')
    async def skip_song(self, ctx,amount = 1):
        try:
            player = self.bot.lavalink.player_manager.get(ctx.guild.id)

            x = 0
            while (x < amount):
                x = x + 1
                if ctx.author.voice is not None and ctx.author.voice.channel.id == int(player.channel_id):
                    if not player.is_playing:
                        return await ctx.channel.send("Nothing playing to skip.")
                    else:
                        await player.skip()
                        if x == 1: # make sure song skipped only prints once.
                            await ctx.channel.send("Song skipped.")
                else:
                    return await ctx.channel.send("Please join the same voice channel as me.")
        except:
            return await ctx.channel.send("Nothing playing.")

    @commands.command(name = "clear",description="Clears all of the currently playing songs and makes the bot disconnect.")
    @commands.has_any_role("Dj","DJ","Administrator")
    async def clear_queue(self,ctx):
        try:
            player = self.bot.lavalink.player_manager.get(ctx.guild.id)
            if ctx.author.voice is not None and ctx.author.voice.channel.id == int(player.channel_id):
                if player.is_playing:
                    while player.is_playing:
                        await player.skip()
                    await ctx.channel.send("Songs Cleared.")
                else:
                    await ctx.channel.send("Nothing playing to clear.")
            else: 
                await ctx.channel.send("Please join the same voice channel as me.")
        except:
            await ctx.channel.send("Nothing playing.")

    # Began the removal of this function as clear is a better alternative.
    #@commands.command(name = 'disconnect', aliases = ['dc'],description="Force disconnects the bot from a voice channel") #bad practice, better to use clear.
    #@commands.has_any_role('Dj','Administrator','DJ')
    #async def disconnect_bot(self,ctx):
    #    try:
    #        player = self.bot.lavalink.player_manager.get(ctx.guild.id)
    #        if ctx.author.voice is not None and ctx.author.voice.channel.id == int(player.channel_id):
    #            if not player.is_connected:
    #                await ctx.channel.send("No bot is connected.")
    #            else:
    #                await ctx.channel.send("Bot disconnected.")
    #                guild_id = int(player.guild_id)
    #                await self.connect_to(guild_id,None)
    #        else: 
    #            await ctx.channel.send("Please join the same voice channel as me.")
    #    except:
    #        await ctx.channel.send("Nothing playing.")


    @commands.command(name='pause',aliases=["ps"],description="Pauses a song if one is playing.") #command to pause currently playing music
    @commands.has_any_role('Dj','Administrator','DJ')
    async def pause_bot(self,ctx):
        try:
            player = self.bot.lavalink.player_manager.get(ctx.guild.id)
            if ctx.author.voice is not None and ctx.author.voice.channel.id == int(player.channel_id):
                if player.is_playing:
                    status = True
                    await ctx.channel.send("Song has been paused.")
                    await player.set_pause(True)
                    i = 0
                    while i < 84: # This will periodically check to see if it has been unpaused
                        await asyncio.sleep(5) 
                        i = i + 1
                        if not player.paused: # If its been unpaused no need to keep counting. (Also fixes some issues)
                            status = False
                            break

                    if player.paused and player.is_playing and status is True:
                        await player.set_pause(False) # If paused unpause.
                        await ctx.channel.send("Automatically unpaused.")

                else:
                    await ctx.channel.send("No song is playing to be paused.")
            else:
                await ctx.channel.send("Please join the same voice channel as me.")
        except:
            await ctx.channel.send("Nothing playing.")

    @commands.command(name='unpause', aliases=['resume','start','up'],description="Unpauses a paused song.") #command to unpause currently paused music
    @commands.has_any_role('Dj','Administrator','DJ')
    async def unpause_bot(self,ctx):
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


    @commands.command(name='queue',aliases=['playlist','songlist','upnext'],description="Shows songs up next in order, with the currently playing at the top.") # display the songs in the order they are waiting to play
    @commands.has_any_role('Dj','Administrator','DJ')
    async def queue(self,ctx, page = 1):
        if not isinstance(page, int): # Stop here if the page is not a valid number (save processing time).
            return ctx.channel.send("Please enter a valid number.")

        player = self.bot.lavalink.player_manager.get(ctx.guild.id)
        if player.is_playing:
            songlist = player.queue
            list_collection = []
            complete_list = ''
            complete_list = complete_list + "NP: " +  player.current['title'] + "\n"
            i = 0
            for song in songlist:
                complete_list = complete_list + f"{i + 1}: {song['title']}\n"
                i = i + 1
                if i % 10 == 0: # Break into pages of 10 and add to a collection
                    list_collection.append(complete_list)
                    complete_list = ''

            if i % 10 != 0 or i == 0: # Check for the case where it is not a perfect multiple, add "half page" (< 10) or if there is only one song playing
                list_collection.append(complete_list)

            selection = page - 1
            embed = discord.Embed()
            embed.title = 'Queue'
            # add an inital if to check if it is an int then do page -1 if its not int default to page 0
            if int(selection) < 0: # handle negative number
                list_collection[0] += "Page: 1/" + str(len(list_collection))
                embed.description = list_collection[0]
            elif int(selection) > len(list_collection) - 1: # Handle a case where the index is greater than page amount
                list_collection[len(list_collection) - 1] += "Page: " + str(len(list_collection)) + "/" + str(len(list_collection))
                embed.description = list_collection[len(list_collection) - 1]
            else: # Handle a valid input case.
                list_collection[selection] += "Page: " + str(page) + "/" + str(len(list_collection))
                embed.description = list_collection[selection]
            await ctx.channel.send(embed=embed)
        else:
            await ctx.channel.send("Nothing is queued.")
    # This needs to be tested more thoroughly. Broke my bot again.
    @commands.command(name = "shuffle",description = "New shuffle function that has to be called once and makes a new queue. Result is shown on \"queue\" commands now..")
    @commands.has_any_role("Dj","DJ","Administrator")
    async def shuffle(self,ctx):
        try:
            player = self.bot.lavalink.player_manager.get(ctx.guild.id)
            if ctx.author.voice is not None and ctx.author.voice.channel.id == int(player.channel_id):
                if player.is_playing:
                    songlist = player.queue
                    random.shuffle(songlist)
                    await ctx.channel.send("Finished.")
                else:
                    await ctx.channel.send("Nothing playing!")
            else:
                await ctx.channel.send("Please join the same voice channel as me and ensure something is playing.")
        except Exception as error:
            print(error)
    # This function has not been updated to the latest API and is not currently recommended. May add back in a future update.
    #@commands.command(name = 'clearbotcache', description="Used to clear the bot cache, only use after reading the Readme file. This can have negative consequences and should be avoided.") 
    #@commands.has_permissions(ban_members=True, kick_members=True, manage_roles=True, administrator=True)
    #async def disconnect_player(self, ctx):
    #    player = self.bot.lavalink.player_manager.create(ctx.guild.id, endpoint=str(ctx.guild.region))
    #    await self.bot.lavalink.player_manager.destroy(int(ctx.guild.id))
    #    await ctx.channel.send("Bot player has been cleared successfully.")
        
def setup(bot):
    bot.add_cog(music(bot))