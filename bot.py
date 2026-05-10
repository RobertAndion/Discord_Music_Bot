import discord
from discord.ext import commands
import os
import asyncio
import subprocess
import shlex
import signal
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
    extensions_to_load = ['playlist'] + [
        f'Cogs.{f[:-3]}' for f in os.listdir("./Cogs") if f.endswith(".py")
    ]
    for ext in extensions_to_load:
        if ext not in client.extensions:
            await client.load_extension(ext)

# TODO: Refactor so that shell files can go into a folder

@client.command(name="reboot")
@commands.is_owner()
async def reboot(ctx):
    await ctx.send("Rebooting")
    os.kill(os.getpid(), signal.SIGTERM)


@client.command(name="backupPlaylists")
@commands.is_owner()
async def backup_playlists(ctx):
    await ctx.send("Backing up playlists and will send as a personal message.")
    backup_path = '/tmp/backup.zip'
    if os.path.isfile(backup_path):
        os.remove(backup_path)

    zipCommand = shlex.split(f"zip -r {backup_path} ./Playlist")
    outcome = subprocess.Popen(zipCommand)
    waitCounter = 10
    while outcome.poll() is None and waitCounter > 0:
        await asyncio.sleep(1)
        waitCounter -= 1

    if outcome.returncode != 0:
        return await ctx.send("Backup failed.")

    if os.path.isfile(backup_path):
        await ctx.author.send(file=discord.File(backup_path))
        os.remove(backup_path)

client.run(TOKEN)
