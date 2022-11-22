from discord.ext import commands
import os
import discord
import asyncio
import subprocess
import shlex
from dotenv import load_dotenv
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

Serverinformation = """
Discord Music Bot Version 1.3:
All commands need the prefix "." in order to run. use .help to see all commands and .help play ,
for example will show information about the play command.
To use the "Admin" functions the user must have "kick" "ban" permissions for some or a role by the name of "Administrator" for others.
** NOTICE: Most of the bots functions rely on a role permissions basis. **
To use the "Music" functions of the bot the role of: "Dj", "DJ", or "Administrator" needs to be made and given to the users to have this ability.
To make roles you enter server settings and click roles. From there the plus sign creates the new role.
"""

client = commands.Bot(command_prefix='.', intents=intents)


@client.event
async def on_ready():
    print("Bot is live")
    await client.load_extension('playlist')
    for file in os.listdir("./Cogs"):
        if file.endswith(".py"):
            await client.load_extension(f'Cogs.{file[:-3]}')


@client.command(name="setup")
@commands.has_permissions(administrator=True)
async def setup(ctx):
    await ctx.author.send(Serverinformation)


@client.command(name="reboot")
@commands.is_owner()  # Now only the bot owner can call reboot.
async def reboot(ctx):
    await ctx.channel.send("Rebooting")
    subprocess.call(["sh", "./autorestart.sh"])


@client.command(name="backupPlaylists")
@commands.is_owner()  # Now only the bot owner can call backupPlaylists.
async def backup_playlists(ctx):
    await ctx.channel.send("Backing up playlists and will send as a personal message.")
    if os.path.isfile('./backup.zip'):
        os.remove('./backup.zip')

    zipCommand = shlex.split("zip -r backup.zip ./Playlist")
    outcome = subprocess.Popen(zipCommand)
    waitCounter = 10
    while outcome.poll() is None and waitCounter > 0:
        await asyncio.sleep(1)
        waitCounter = waitCounter - 1

    if os.path.isfile('./backup.zip'):
        await ctx.author.send(file=discord.File(r'./backup.zip'))
        os.remove('./backup.zip')

client.run(TOKEN)
