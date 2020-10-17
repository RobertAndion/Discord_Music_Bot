import os
import discord
import random
from dotenv import load_dotenv
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
from discord.ext import commands
## Robert A. USF Computer Science: 
## Python discord bot with limited administration commands and an array of
## music playing commands, along with a new welcome/auto role function.

Serverinformation = """
Discord Music Bot Version 1.1:
All commands need the prefix "." in order to run. use .help to see all commands and .help play ,
for example will show information about the play command.
To use the "Admin" functions the user must have "kick" "ban" permissions for some or a role by the name of "Administrator" for others.
** NOTICE: Most of the bots functions rely on a role permissions basis. **
To use the "Music" functions of the bot the role of: "Dj", "DJ", or "Administrator" needs to be made and given to the users to have this ability.
To make roles you enter server settings and click roles. From there the plus sign creates the new role.

"""
client = commands.Bot(command_prefix='.')

@client.event
async def on_ready():
    print("Bot is live")
    client.load_extension('Admin')
    client.load_extension('music')
    client.load_extension('playlist')
    client.load_extension('welcome')

@client.command(name="setup")
@commands.has_permissions(administrator=True)
async def setup(ctx):
    await ctx.author.send(Serverinformation)

client.run(TOKEN)