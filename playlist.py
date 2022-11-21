from discord.ext import commands
import discord
import lavalink
import asyncio
from discord import utils
from discord import Embed
import fileRead
import re
url_rx = re.compile(r'https?://(?:www\.)?.+')


class playlist(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="viewplaylist", aliases=["vpl"], description="Views all songs inside of a given playlist.")
    @commands.has_any_role("DJ", 'Dj', 'Administrator')
    async def view_playlist(self, ctx, *, list_name):
        list_collection = fileRead.playlist_read(list_name, ctx)
        if list_collection:
            try:
                embed = Embed()
                double = ''
                x = 1
                for section in list_collection:
                    double += section

                    if x % 2 == 0:
                        embed.description = double
                        await ctx.channel.send(embed=embed)
                        await asyncio.sleep(1)
                        double = ''
                    x = x + 1

                if len(list_collection) % 2 != 0:
                    embed.description = double
                    await ctx.channel.send(embed=embed)

            except:
                await ctx.channel.send("Playlist not found.")
        else:
            await ctx.channel.send("Playlist is empty or does not exist.")

    @commands.command(name="listplaylists", aliases=["lpl"], description="Lists all of a users playlists")
    @commands.has_any_role("Dj", "DJ", "Administrator")
    async def list_playlists(self, ctx, page=1):
        # Stop here if the page is not a valid number (save processing time).
        if not isinstance(page, int):
            return ctx.channel.send("Please enter a valid number.")

        list_collection = fileRead.list_playlist(ctx)
        if list_collection:
            try:
                selection = page - 1
                embed = Embed()
                if int(selection) < 0:  # handle negative number
                    list_collection[0] += "'\n' + Page: 1/" + \
                        str(len(list_collection))
                    embed.description = list_collection[0]
                # Handle a case where the index is greater than page amount
                elif int(selection) > len(list_collection) - 1:
                    list_collection[len(list_collection) - 1] += "'\n' + Page: " + str(
                        len(list_collection)) + "/" + str(len(list_collection))
                    embed.description = list_collection[len(
                        list_collection) - 1]
                else:  # Handle a valid input case.
                    list_collection[selection] += '\n' + "Page: " + \
                        str(page) + "/" + str(len(list_collection))
                    embed.description = list_collection[selection]

                await ctx.channel.send(embed=embed)
            except:
                await ctx.channel.send("Failed to list playlists.")
        else:
            await ctx.channel.send("No playlists found, do you have any?")

    @commands.command(name="deleteplaylist", aliases=["dpl"], description="Used to delete an entire playlist.")
    @commands.has_any_role("DJ", "Dj", "Administrator")
    async def delete_playlist(self, ctx, *, playlist):
        result = fileRead.delete_playlist(ctx, playlist)
        if result == "Done":
            await ctx.channel.send("Playlist deleted.")
        elif result == "Not-Found":
            await ctx.channel.send("Playlist not found. Check that it is spelled correctly or if it has already been deleted.")
        elif result == "No-Playlists":
            await ctx.channel.send("You have no playlists.")

    @commands.command(name="deletefromplaylist", aliases=["dfp"], description="Delete song from playlist based on its number in the playlist.")
    @commands.has_any_role("Dj", "DJ", "Administrator")
    async def delete_from_playlist(self, ctx, value, *, playlist):
        try:
            result = fileRead.delete_from_playlist(ctx, playlist, int(value))
            if result == "Done":
                await ctx.channel.send("Song deleted from playlist.")
            elif result == "Not-Found":
                await ctx.channel.send("Song not found.")
            elif result == "No-Playlists":
                await ctx.channel.send("You have no playlists.")
        except:
            await ctx.channel.send("Playlist not found.")

    @commands.command(name="createplaylist", aliases=['cpl'], description="Uses the currently playing song to start a new playlist with the inputted name")
    @commands.has_any_role("DJ", "Dj", "Administrator")
    async def create_playlist(self, ctx, *, playlist_name):
        player = self.bot.lavalink.player_manager.get(ctx.guild.id)
        if player.is_playing:
            songname = player.current['title']
            fileRead.new_playlist(ctx, playlist_name, songname)
            await ctx.channel.send(playlist_name + ", created.")

        else:
            await ctx.channel.send("Please have the first song you want to add playing to make a new playlist.")

    @commands.command(name="addtoplaylist", aliases=["atp"], description="Adds currently playing song to the given playlist name as long as it exists.")
    @commands.has_any_role("DJ", "Dj", "Administrator")
    async def add_to_playlist(self, ctx, *, playlist_name):
        player = self.bot.lavalink.player_manager.get(ctx.guild.id)
        if player.is_playing:
            songname = player.current['title']
            passfail = fileRead.add_to_playlist(ctx, playlist_name, songname)
            if passfail:
                await ctx.channel.send("Song added")
            else:
                await ctx.channel.send("Playlist needs to be created before you can add to it.")
        else:
            await ctx.channel.send("Need the song to add currently playing.")

    @commands.command(name="renameplaylist", aliases=["rpl"], description="Renames a current list. Input as: current name,new name")
    @commands.has_any_role("Dj", "DJ", "Administrator")
    async def rename_playlist(self, ctx, *, raw_name):
        status = fileRead.rename_playlist(ctx, raw_name)
        if status == "Success":
            await ctx.channel.send("Playlist name updated.")
        elif status == "No-List":
            await ctx.channel.send("Operation failed. You either have no playlists or no playlist by the given name.")
        elif status == "Invalid-Input":
            await ctx.channel.send("Please format the command properly. .rpl current name,new name (MANDATORY COMMA)")

    @commands.command(name="addqueuetolist", aliases=["aqtp"], description="Adds the entire queue to a playlist.")
    @commands.has_any_role("Dj", "DJ", "Administrator")
    async def add_queue_to_list(self, ctx, *, listname):
        player = self.bot.lavalink.player_manager.get(ctx.guild.id)
        if player.is_playing:
            songlist = player.queue
            for song in songlist:
                check = fileRead.add_to_playlist(
                    ctx, listname, f"{song['title']}")
                if not check:
                    return await ctx.channel.send("Operation failed. Make sure the playlist name is valid.")
            await ctx.channel.send("Queue added to " + str(listname) + ".")
        else:
            await ctx.channel.send("There is nothing playing.")


async def setup(bot):
    await bot.add_cog(playlist(bot))
