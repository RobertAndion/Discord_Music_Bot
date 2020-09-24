from discord.ext import commands
import discord
import lavalink
from discord import utils
from discord import Embed
import fileRead
"""
Robert A. Computer Science USF, cog with playlist functions related to music.py

"""
class playlist(commands.Cog):
    def __init__(self,bot):
        self.bot = bot
        self.bot.music = lavalink.Client(self.bot.user.id)
        self.bot.music.add_node('localhost',2333,'changeme123','na','local_music_node') # PASSWORD HERE MUST MATCH YML
        self.bot.add_listener(self.bot.music.voice_update_handler, 'on_socket_response')
        self.bot.music.add_event_hook(self.track_hook)



    @commands.command(name = "viewplaylist", aliases = ["vpl"],description="Views all songs inside of a given playlist.")
    @commands.has_any_role("DJ",'Dj','Administrator')
    async def view_playlist(self,ctx,*,list_name):
        formattedString = fileRead.playlist_read(list_name,ctx)
        if formattedString != "Failed-Process":
            try: 
                embed = Embed()
                embed.description = formattedString
                await ctx.channel.send(embed=embed)
            except Exception as error:
                await ctx.channel.send("Playlist not found.")
        else:
            await ctx.channel.send("Playlist is empty or does not exist.")


    @commands.command(name="listplaylists",aliases=["lpl"],description="Lists all of a users playlists")
    @commands.has_any_role("Dj","DJ","Administrator")
    async def list_playlists(self,ctx):
        output = fileRead.list_playlist(ctx)
        if output != "Failed-Process":
            try:
                embed = Embed()
                embed.description = output
                await ctx.channel.send(embed=embed)
            except Exception as error:
                await ctx.channel.send("Failed to list playlists.")
        else:
            await ctx.channel.send("No playlists found, do you have any?")


    @commands.command(name="deleteplaylist",aliases=["dpl"],description="Used to delete an entire playlist.")
    @commands.has_any_role("DJ","Dj","Administrator")
    async def delete_playlist(self,ctx,*,playlist):
        result = fileRead.delete_playlist(ctx,playlist)
        if result == "Done":
            await ctx.channel.send("Playlist deleted.")
        elif result == "Not-Found":
            await ctx.channel.send("Playlist not found. Check that it is spelled correctly or if it has already been deleted.")
        elif result == "No-Playlists":
            await ctx.channel.send("You have no playlists.")


    @commands.command(name="deletefromplaylist",aliases=["dfp"],description="Delete song from playlist based on its number in the playlist.")
    @commands.has_any_role("Dj","DJ","Administrator")
    async def delete_from_playlist(self,ctx,value,*,playlist):
        try: 
            result = fileRead.delete_from_playlist(ctx,playlist,int(value))
            if result == "Done":
                await ctx.channel.send("Song deleted from playlist.")
            elif result == "Not-Found":
                await ctx.channel.send("Song not found.")
            elif result == "No-Playlists":
                await ctx.channel.send("You have no playlists.")
        except Exception as error:
            await ctx.channel.send("Playlist not found.")
       

    @commands.command(name = "createplaylist", aliases = ['cpl'],description="Uses the currently playing song to start a new playlist with the inputted name")
    @commands.has_any_role("DJ","Dj","Administrator")
    async def create_playlist(self,ctx,*,playlist_name):
        player = self.bot.music.player_manager.get(ctx.guild.id)
        if player.is_playing:
            songname = player.current['title']
            fileRead.new_playlist(ctx,playlist_name,songname)
            await ctx.channel.send(playlist_name + ", created.")

        else:
            await ctx.channel.send("Please have the first song you want to add playing to make a new playlist.")


    @commands.command(name="addtoplaylist",aliases=["atp"],description="Adds currently playing song to the given playlist name as log as it exists.")
    @commands.has_any_role("DJ","Dj","Administrator")
    async def add_to_playlist(self,ctx,*,playlist_name):
        player = self.bot.music.player_manager.get(ctx.guild.id)
        if player.is_playing:
            songname = player.current['title']
            passfail = fileRead.add_to_playlist(ctx,playlist_name,songname)
            if passfail:
                await ctx.channel.send("Song added")
            else:
                await ctx.channel.send("Playlist needs to be created before you can add to it.")
        else:
            await ctx.channel.send("Need the song to add currently playing.")


    @commands.command(name="playfromlist",aliases = ["pfpl","playl"],description="Loads a playlist into the queue to be played.")
    @commands.has_any_role("Dj","DJ","Administrator")
    async def play_from_list(self,ctx,*,playlist_name):
        songlist = fileRead.play_playlist(ctx,playlist_name) 
        if songlist == False:
            await ctx.channel.send("Playlist not found.")
        else:
            try:
                i = 0
                for query in songlist:
                    if i < 1: #only need to connect the player and do checks on first run. Using an else to save system resources.
                        member = utils.find(lambda m: m.id == ctx.author.id, ctx.guild.members) # This will connect the bot if it is not already connected.
                        if member is not None and member.voice is not None:
                            vc = member.voice.channel
                            player = self.bot.music.player_manager.create(ctx.guild.id, endpoint=str(ctx.guild.region))
                            if not player.is_connected: #heres where check actually happens. may be a waste of resources. look into.
                                player.store('channel',ctx.channel.id)
                                await self.connect_to(ctx.guild.id, str(vc.id))

                        try:
                            if ctx.author.voice is not None:
                                query = f'ytsearch:{query}'
                                results = await player.node.get_tracks(query)
                                try:
                                    track = results['tracks'][0]
                                    player.add(requester=ctx.author.id, track=track)
                                    track_title = track["info"]["title"]
                                    if not player.is_playing:
                                        await player.play()
                                    fileRead.logUpdate(member,track_title) # Add the song to the log
                                    i = i + 1
                                except Exception as error:
                                    await ctx.channel.send("Song not found. (or title has emojis/symbols)")
                            else:
                                await ctx.channel.send("Please join a voice chat to play a song.")
                                break

                        except Exception as error:
                            print(error)
                    else: #resource saving addition of songs after the first.
                        player = self.bot.music.player_manager.create(ctx.guild.id, endpoint=str(ctx.guild.region))
                        query = f'ytsearch:{query}'
                        results = await player.node.get_tracks(query)
                        try:
                            track = results['tracks'][0]
                            player.add(requester=ctx.author.id, track=track)
                        except Exception as error:
                            await ctx.channel.send("Song not found. (or title has emojis/symbols)")


                await ctx.channel.send("Playlist added to queue.")
            except Exception as error:
                await ctx.channel.send("Playlist not found.")

    async def track_hook(self,event): #disconnects bot when song list is complete.
        if isinstance(event, lavalink.events.QueueEndEvent):
            guild_id = int(event.player.guild_id)
            await self.connect_to(guild_id,None)

    async def connect_to(self, guild_id: int, channel_id: str):
        ws = self.bot._connection._get_websocket(guild_id)
        await ws.voice_state(str(guild_id), channel_id)



def setup(bot):
    bot.add_cog(playlist(bot))