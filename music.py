from discord.ext import commands
import discord
import lavalink
from discord import utils
from discord import Embed
import fileRead
import re
url_rx = re.compile(r'https?://(?:www\.)?.+')

"""
Robert A. USF Computer Science
A cog to hold all of the functions used to play music for the bot.
"""

class music(commands.Cog):
    def __init__(self,bot):
        self.bot = bot
        self.bot.music = lavalink.Client(self.bot.user.id)
        self.bot.music.add_node('localhost',2333,'changeme123','na','local_music_node') # PASSWORD HERE MUST MATCH YML
        self.bot.add_listener(self.bot.music.voice_update_handler, 'on_socket_response')
        self.bot.music.add_event_hook(self.track_hook)

    
    @commands.command(name = 'play', description=".play {song name} to play a song, will connect the bot.") #Allows for a song to be played, does not make sure people are in the same chat. Harder to implement.
    @commands.has_any_role('Dj','Administrator','DJ')
    async def play_song(self, ctx, *, query):
        member = utils.find(lambda m: m.id == ctx.author.id, ctx.guild.members) # This will connect the bot if it is not already connected.
        if member is not None and member.voice is not None:
            vc = member.voice.channel
            player = self.bot.music.player_manager.create(ctx.guild.id, endpoint=str(ctx.guild.region))
            if not player.is_connected:
                player.store('channel',ctx.channel.id) #used so we have the ctx.channel usage
                await self.connect_to(ctx.guild.id, str(vc.id))

        try:
            query = query.strip('<>')
            if not url_rx.match(query): # This and the line above and below allow for direct link play
                query = f'ytsearch:{query}'

            results = await player.node.get_tracks(query)
            try:
                track = results['tracks'][0]
                player.add(requester=ctx.author.id, track=track)
                track_title = track["info"]["title"]
                if not player.is_playing:
                    await player.play()
                fileRead.logUpdate(member,track_title) # Add the song to the log
                await ctx.channel.send(f"{track_title} added to queue.") 
            except Exception as error:
                await ctx.channel.send("Song not found. (or title has emojis/symbols)")

        except Exception as error:
            print(error)

    async def track_hook(self,event): #disconnects bot when song list is complete.
        if isinstance(event, lavalink.events.QueueEndEvent):
            guild_id = int(event.player.guild_id)
            await self.connect_to(guild_id,None)

    async def connect_to(self, guild_id: int, channel_id: str):
        ws = self.bot._connection._get_websocket(guild_id)
        await ws.voice_state(str(guild_id), channel_id)

    
    @commands.command(name = 'skip',description="Skips currently playing song.") #skips currently playing song
    @commands.has_any_role('Dj','Administrator','DJ')
    async def skip_song(self, ctx):
        try:
            player = self.bot.music.player_manager.get(ctx.guild.id)
            if ctx.author.voice is not None and ctx.author.voice.channel.id == int(player.channel_id):
                if not player.is_playing:
                    await ctx.channel.send("Nothing playing to skip.")
                else:
                    await player.skip()
                    await ctx.channel.send("Song skipped.")
            else:
                await ctx.channel.send("Please join the same voice channel as me.")
        except Exception as error:
            await ctx.channel.send("Nothing playing.")

    @commands.command(name = "clear",description="Clears all of the currently playing songs and makes the bot disconnect.")
    @commands.has_any_role("Dj","DJ","Administrator")
    async def clear_queue(self,ctx):
        try:
            player = self.bot.music.player_manager.get(ctx.guild.id)
            if ctx.author.voice is not None and ctx.author.voice.channel.id == int(player.channel_id):
                if player.is_playing:
                    while player.is_playing:
                        await player.skip()
                    await ctx.channel.send("Songs Cleared.")
                else:
                    await ctx.channel.send("Nothing playing to clear.")
            else: 
                await ctx.channel.send("Please join the same voice channel as me.")
        except Exception as error:
            await ctx.channel.send("Nothing playing.")



    @commands.command(name = 'stop',description="Stops the bot's audio") #stops all music to be played on bot
    @commands.has_any_role('Dj','Administrator','DJ')
    async def stop_song(self,ctx):
        try:
            player = self.bot.music.player_manager.get(ctx.guild.id)
            if ctx.author.voice is not None and ctx.author.voice.channel.id == int(player.channel_id):
                if not player.is_playing:
                    ctx.channel.send("Nothing playing to stop.")
                else:
                    await ctx.channel.send("Music stopped.")
                    await player.stop()
            else:
                await ctx.channel.send("Please join the same voice channel as me.")
        except Exception as error:
            await ctx.channel.send("Nothing playing.")


    @commands.command(name = 'disconnect', aliases = ['dc'],description="Force disconnects the bot from a voice channel") #disconnects bot from voice channel
    @commands.has_any_role('Dj','Administrator','DJ')
    async def disconnect_bot(self,ctx):
        try:
            player = self.bot.music.player_manager.get(ctx.guild.id)
            if ctx.author.voice is not None and ctx.author.voice.channel.id == int(player.channel_id):
                if not player.is_connected:
                    await ctx.channel.send("No bot is connected.")
                else:
                    await ctx.channel.send("Bot disconnected.")
                    guild_id = int(player.guild_id)
                    await self.connect_to(guild_id,None)
            else: 
                await ctx.channel.send("Please join the same voice channel as me.")
        except Exception as error:
            await ctx.channel.send("Nothing playing.")


    @commands.command(name='pause',aliases=["ps"],description="Pauses a song if one is playing.") #command to pause currently playing music
    @commands.has_any_role('Dj','Administrator','DJ')
    async def pause_bot(self,ctx):
        try:
            player = self.bot.music.player_manager.get(ctx.guild.id)
            if ctx.author.voice is not None and ctx.author.voice.channel.id == int(player.channel_id):
                if player.is_playing:
                    await ctx.channel.send("Song has been paused.")
                    await player.set_pause(True)
                else:
                    await ctx.channel.send("No song is playing to be paused.")
            else:
                await ctx.channel.send("Please join the same voice channel as me.")
        except Exception as error:
            await ctx.channel.send("Nothing playing.")

    @commands.command(name='unpause', aliases=['resume','start','up'],description="Unpauses a paused song.") #command to unpause currently paused music
    @commands.has_any_role('Dj','Administrator','DJ')
    async def unpause_bot(self,ctx):
        try:
            player = self.bot.music.player_manager.get(ctx.guild.id)
            if ctx.author.voice.channel.id == int(player.channel_id):
                if player.paused:
                    await ctx.channel.send("Resuming song.")
                    await player.set_pause(False)
                else:
                    await ctx.channel.send("Nothing is paused to resume.")
            else:
                await ctx.channel.send("Please join the same voice channel as me.")
        except Exception as error:
            await ctx.channel.send("Nothing playing.")


#    @commands.command(name='current',aliases = ['np','nowplaying'],description="Shows the currently playing song.") #display the currently playing song
#    @commands.has_any_role('Dj','Administrator','DJ')
#    async def now_playing(self,ctx):
#        player = self.bot.music.player_manager.get(ctx.guild.id) This is deprecated since queue now shows now playing.
#        if player.is_playing:
#            songname = player.current['title']
#            await ctx.channel.send(f"Now playing: {songname}") 
#        else:
#            await ctx.channel.send("Nothing currently playing.")


    @commands.command(name='queue',aliases=['playlist','songlist','upnext'],description="Shows songs up next in order, with the currently playing at the top.") # display the songs in the order they are waiting to play
    @commands.has_any_role('Dj','Administrator','DJ')
    async def queue(self,ctx):
        player = self.bot.music.player_manager.get(ctx.guild.id)
        if player.is_playing:
            songlist = player.queue
            complete_list = ''
            complete_list = complete_list + "NP: " +  player.current['title'] + "\n"
            i = 0
            for song in songlist:
                complete_list = complete_list + f"{i + 1}: {song['title']}\n"
                i = i + 1
            embed = Embed()
            embed.description = complete_list
            await ctx.channel.send(embed=embed)
        else:
            await ctx.channel.send("Nothing is queued.")

    
    @commands.command(name = "shuffle",description = "Indefinetely shuffles the songs to be played.")
    @commands.has_any_role("Dj","DJ","Administrator")
    async def shuffle(self,ctx):
        try:
            player = self.bot.music.player_manager.get(ctx.guild.id)
            if ctx.author.voice is not None and ctx.author.voice.channel.id == int(player.channel_id):
                if player.is_playing:
                    try:
                        player.shuffle = True
                        await ctx.channel.send("Currently playing has been shuffled.")
                    except Exception as error:
                        print(error)
                else:
                    await ctx.channel.send("No music playing.")
            else:
                await ctx.channel.send("Please join my channel to shuffle.")
        except Exception as error:
            await ctx.channel.send("Nothing playing.")

    @commands.command(name = "stopshuffle",aliases = ["unshuffle"],description="Ends the shuffling of all songs.")
    @commands.has_any_role("Dj","DJ","Administrator")
    async def unshuffle(self,ctx):
        try:
            player = self.bot.music.player_manager.get(ctx.guild.id)
            if ctx.author.voice is not None and ctx.author.voice.channel.id == int(player.channel_id):
                if player.is_playing:
                    try:
                        player.shuffle = False
                        await ctx.channel.send("Currently playing has been unshuffled")
                    except Exception as error:
                        print(error)
                else:
                    await ctx.channel.send("No music is playing.")
            else:
                await ctx.channel.send("Please join my channel to unshuffle.")
        except Exception as error:
            await ctx.channel.send("Nothing playing.")

def setup(bot):
    bot.add_cog(music(bot))