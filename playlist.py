from discord.ext import commands
import discord
import lavalink
import asyncio
from discord import utils
from discord import Embed
import re
import fileProcessing

url_rx = re.compile(r'https?://(?:www\.)?.+')

config = fileProcessing.read_config()
roles = config["roles"]


class playlist(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cog_command_error(self, ctx, error):
        if isinstance(error, commands.CommandInvokeError):
            await ctx.send(error.original)

    @commands.command(name="viewplaylist", aliases=["vpl"], description="Views all songs inside of a given playlist.")
    @commands.has_any_role(*roles)
    async def view_playlist(self, ctx, *, list_name):
        list_collection = fileProcessing.playlist_read(list_name, ctx)
        if list_collection:
            try:
                embed = Embed()
                double = ''
                x = 1
                for section in list_collection:
                    double += section

                    if x % 2 == 0:
                        embed.description = double
                        await ctx.send(embed=embed)
                        await asyncio.sleep(1)
                        double = ''
                    x = x + 1

                if len(list_collection) % 2 != 0:
                    embed.description = double
                    await ctx.send(embed=embed)
            except:
                await ctx.send("Playlist not found.")
        else:
            raise commands.CommandInvokeError(
                "Playlist is empty or does not exist.")

    @commands.command(name="listplaylists", aliases=["lpl"], description="Lists all of a users playlists")
    @commands.has_any_role(*roles)
    async def list_playlists(self, ctx, page=1):
        # Stop here if the page is not a valid number (save processing time).
        if not isinstance(page, int):
            raise commands.CommandInvokeError("Please enter a valid number.")

        list_collection = fileProcessing.list_playlists(ctx)
        if list_collection:
            try:
                selection = page - 1
                embed = Embed()
                if int(selection) < 0:
                    list_collection[0] += "'\n' + Page: 1/" + \
                        str(len(list_collection))
                    embed.description = list_collection[0]

                elif int(selection) > len(list_collection) - 1:
                    list_collection[len(list_collection) - 1] += "'\n' + Page: " + str(
                        len(list_collection)) + "/" + str(len(list_collection))
                    embed.description = list_collection[len(
                        list_collection) - 1]
                else:  # Valid input
                    list_collection[selection] += '\n' + "Page: " + \
                        str(page) + "/" + str(len(list_collection))
                    embed.description = list_collection[selection]

                await ctx.send(embed=embed)
            except:
                raise commands.CommandInvokeError(
                    "Failed to list playlists...")
        else:
            await ctx.send("No playlists found, do you have any?")

    @commands.command(name="deleteplaylist", aliases=["dpl"], description="Used to delete an entire playlist.")
    @commands.has_any_role(*roles)
    async def delete_playlist(self, ctx, *, playlist):
        result = fileProcessing.delete_playlist(ctx, playlist)
        if result == "Done":
            await ctx.send("Playlist deleted.")
        elif result == "Not-Found":
            await ctx.send("Playlist not found. Check that it is spelled correctly or if it has already been deleted.")
        elif result == "No-Playlists":
            await ctx.send("You have no playlists.")

    @commands.command(name="deletefromplaylist", aliases=["dfp"], description="Delete song from playlist based on its number in the playlist.")
    @commands.has_any_role(*roles)
    async def delete_from_playlist(self, ctx, value, *, playlist):
        try:
            result = fileProcessing.delete_from_playlist(
                ctx, playlist, int(value))
            if result == "Done":
                await ctx.send("Song deleted from playlist.")
            elif result == "Not-Found":
                await ctx.send("Song not found.")
            elif result == "No-Playlists":
                await ctx.send("You have no playlists.")
        except:
            await ctx.send("Playlist not found.")

    @commands.command(name="createplaylist", aliases=['cpl'], description="Uses the currently playing song to start a new playlist with the inputted name")
    @commands.has_any_role(*roles)
    async def create_playlist(self, ctx, *, playlist_name):
        player = self.bot.lavalink.player_manager.get(ctx.guild.id)
        if player.is_playing:
            songname = player.current['title']
            fileProcessing.new_playlist(ctx, playlist_name, songname)
            await ctx.send(playlist_name + ", created.")
        else:
            await ctx.send("Please have the first song you want to add playing to make a new playlist.")

    @commands.command(name="addtoplaylist", aliases=["atp"], description="Adds currently playing song to the given playlist name as long as it exists.")
    @commands.has_any_role(*roles)
    async def add_to_playlist(self, ctx, *, playlist_name):
        player = self.bot.lavalink.player_manager.get(ctx.guild.id)
        if player.is_playing:
            songname = player.current['title']
            passfail = fileProcessing.add_to_playlist(
                ctx, playlist_name, songname)
            if passfail:
                await ctx.send("Song added")
            else:
                await ctx.send("Playlist needs to be created before you can add to it.")
        else:
            await ctx.send("Please have the first song you want to add playing to add it to the playlist.")

    @commands.command(name="renameplaylist", aliases=["rpl"], description="Renames a current list. Input as: current name,new name")
    @commands.has_any_role(*roles)
    async def rename_playlist(self, ctx, *, raw_name):
        status = fileProcessing.rename_playlist(ctx, raw_name)
        if status == "Success":
            await ctx.send("Playlist name updated.")
        elif status == "No-List":
            await ctx.send("Operation failed. You either have no playlists or no playlist by the given name.")
        elif status == "Invalid-Input":
            await ctx.send("Please format the command properly. .rpl current name,new name (MANDATORY COMMA)")

    @commands.command(name="addqueuetolist", aliases=["aqtp"], description="Adds the entire queue to a playlist.")
    @commands.has_any_role(*roles)
    async def add_queue_to_list(self, ctx, *, listname):
        player = self.bot.lavalink.player_manager.get(ctx.guild.id)
        if player.is_playing:
            songlist = player.queue
            for song in songlist:
                check = fileProcessing.add_to_playlist(
                    ctx, listname, f"{song['title']}")
                if not check:
                    return await ctx.send("Operation failed. Make sure the playlist name is valid.")
            await ctx.send("Queue added to " + str(listname) + ".")
        else:
            raise commands.CommandInvokeError("There is nothing playing.")


async def setup(bot):
    await bot.add_cog(playlist(bot))
