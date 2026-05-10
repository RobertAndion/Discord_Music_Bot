from discord.ext import commands
import discord
import asyncio
import psutil


class cpu(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name='serverinfo', description="Permanent server hardware information")
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
        cpu_percent = await asyncio.to_thread(psutil.cpu_percent, 1)
        embed.description = str(cpu_percent) + "% CPU Usage \n"

        try:
            temps = psutil.sensors_temperatures(fahrenheit=False)
            if temps:
                for key in ("coretemp", "k10temp", "cpu_thermal"):
                    if key in temps:
                        embed.description += str(temps[key][0][1]) + " C \n"
                        break
                else:
                    embed.description += "Temperature: N/A\n"
            else:
                embed.description += "Temperature: N/A\n"
        except AttributeError:
            embed.description += "Temperature: N/A\n"

        embed.description += str(psutil.getloadavg()
                                 [1]) + " average load over the last 5 minutes"
        await ctx.channel.send(embed=embed)


async def setup(bot):
    await bot.add_cog(cpu(bot))
