import discord
from discord.ext import commands
import os
import asyncio
import subprocess
import shlex
from dotenv import load_dotenv
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

client = commands.Bot(command_prefix='.', intents=intents)


@client.event
async def on_ready():
    print("Bot is live")
    await client.load_extension('playlist')
    for file in os.listdir("./Cogs"):
        if file.endswith(".py"):
            await client.load_extension(f'Cogs.{file[:-3]}')

# TODO: Refactor so that shell files can go into a folder

@client.command(name="reboot")
@commands.is_owner()
async def reboot(ctx):
    await ctx.send("Rebooting")
    subprocess.call(["sh", "./autorestart.sh"])


@client.command(name="backupPlaylists")
@commands.is_owner()
async def backup_playlists(ctx):
    await ctx.send("Backing up playlists and will send as a personal message.")
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
