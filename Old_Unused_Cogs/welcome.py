import discord
from discord.ext import commands
from discord.utils import get

class welcome(commands.Cog):
    def __init__(self,bot):
        self.bot=bot

    @commands.Cog.listener()
    async def on_member_join(self, member):
        serverrolename = 'Example' #Name of the role you have made for the bot to give
        servername = str(member.guild) # Grabs the server name
        role = get(member.guild.roles, name = serverrolename) #Remove this line and below to not add a role to a new user
        await member.add_roles(role)                          #Remove me if you remove the line above.
        channel = get(member.guild.text_channels, name = 'general') # Change 'general' to the exact channel you want the message to be sent to.
        await channel.send("Hello! " + str(member.display_name) + ", welcome to " + servername + "!") #You can customize this message.
        

async def setup(bot):
    await bot.add_cog(welcome(bot))
