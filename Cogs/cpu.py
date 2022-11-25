from discord.ext import commands
from discord.utils import get
import discord
import psutil


class cpu(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name='serverinfo', description="Permanant server hardware information")
    async def server_info(self, ctx):
        embed = discord.Embed(color=discord.Color.blurple())
        embed.title = 'Server Information'
        data = ""
        data += str(psutil.cpu_count()) + " total threads \n"
        data += f"{psutil.virtual_memory().total / 2**30:.2f}" + \
            " GB Total Memory \n"
        data += f"{psutil.virtual_memory().available / 2**30:.2f}" + \
            " GB Available Currently \n"
        embed.description = data
        await ctx.channel.send(embed=embed)

    @commands.command(name='cpu', description="Cpu Information")
    async def cpu_info(self, ctx):
        embed = discord.Embed(color=discord.Color.blurple())
        embed.title = 'CPU Information'
        embed.description = str(psutil.cpu_percent(
            interval=1)) + "% CPU Usage \n"
        # embed.description += str(psutil.sensors_temperatures(fahrenheit=False)["k10temp"][0][1]) + " C \n" Manjaro version
        # This works on Ubuntu. You will have to change this for your hardware, remove ["coretemp"][0][1] to print the full package and then pick.
        embed.description += str(psutil.sensors_temperatures(
            fahrenheit=False)["coretemp"][0][1]) + " C \n"
        embed.description += str(psutil.getloadavg()
                                 [1]) + " average load over the last 5 minutes"
        await ctx.channel.send(embed=embed)


async def setup(bot):
    await bot.add_cog(cpu(bot))
