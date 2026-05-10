# Discord Music Bot

## Setup

### Prerequisites

- A Discord bot token ([Discord Developer Portal](https://discord.com/developers/applications))
- Docker (recommended), **or** Java 21+ and Python 3 for a manual install

---

## Docker Setup (Recommended)

### 1. Configure your environment

Copy the example env file and add your token:
```
cp .env.example .env
```
Edit `.env` and replace `your_discord_bot_token_here` with your Discord bot token.

### 2. Build the image

Run from the root of the project:
```
docker build -f Docker/Dockerfile -t musicbot .
```

### 3. Create persistent volumes

These volumes keep your playlists, song logs, and Lavalink plugins across container rebuilds:
```
docker volume create musicbot-playlists
docker volume create musicbot-songlogs
docker volume create musicbot-plugins
```

If you have existing playlists, copy them into the volume before starting:
```
docker run --rm -v musicbot-playlists:/data -v $(pwd)/Playlist:/src alpine cp -r /src/. /data/
```

### 4. Start the container

```
sh run.sh
```

The `run.sh` script runs the container with:
- `--restart unless-stopped` — auto-restarts on crash or server reboot (no crontab needed)
- `--read-only` filesystem with tmpfs for `/tmp` and logs
- Resource limits (1 GB RAM, 1 CPU)
- All capabilities dropped, no-new-privileges enforced
- Persistent volume mounts for Playlist, SongLog, and plugins
- Token loaded from `.env` via `--env-file`

The container starts Lavalink, waits for it to be ready, then launches the bot.

### Stopping and restarting

```
docker stop musicbot
docker start musicbot
```

### Updating the bot

1. Back up playlists from Discord with `.backupPlaylists` (the bot will DM you a zip)
2. Rebuild the image: `docker build -f Docker/Dockerfile -t musicbot .`
3. Remove the old container: `docker rm musicbot`
4. Start fresh: `sh run.sh`
5. Place any backed-up `.json` playlist files back into the volume if needed

### Viewing logs

```
docker logs -f musicbot
```

---

## Manual Setup (No Docker)

### 1. Install Java 21+

Required to run Lavalink.

##### Ubuntu:
```
sudo apt-get install openjdk-21-jre-headless
```

##### Arch:
```
sudo pacman -S jre21-openjdk-headless
```

### 2. Install Python dependencies

```
pip3 install -r requirements.txt
```

### 3. Download Lavalink

Download `Lavalink.jar` from the [Lavalink releases page](https://github.com/lavalink-devs/Lavalink/releases) and place it in the root of the project.

### 4. Configure your environment

```
cp .env.example .env
```
Edit `.env` and add your Discord bot token.

### 5. Run the bot

To run with reboot command support (requires `tmux`):
```
sh startup.sh
```

To run manually in two separate terminals:
```
java -jar Lavalink.jar
```
```
python3 bot.py
```

---

## Configuration

### Lavalink password

The default Lavalink password is `changeme123`. If you change it in `application.yml`, also update the `password` field in `Cogs/music.py` and `playlist.py`.

### Role configuration

Edit `Resources/config.json` to set which Discord roles can use music commands:
```json
{
    "roles": [
        "Dj",
        "Administrator",
        "DJ"
    ]
}
```

Replace, add, or remove role names to match your server's setup.

---

## Preparing to use the bot

Create a role in your Discord server matching one of the names in `config.json` (e.g. `DJ`) and assign it to users you want to control music playback.

---

## COMMAND DOCUMENTATION
### NOTE:
Anything in <> is an argument required by the function. Anything in () are alternate command shortcuts/names

```
.reboot
```
This command will stop the bot process. When running in Docker with `--restart unless-stopped`, the container will automatically restart both Lavalink and the bot.
This command is tied to the owner's Discord ID so only the server owner may use it.

```
.backupPlaylists
```
This command will only work for the bot owner and will private message them a zip file of all playlists.
Useful before rebuilding a Docker image to preserve playlists across updates.

```
.play <SONG-NAME>
```
If the person using the command is in a voice channel and the bot has access to that channel it will connect and play the song listed.
This is also the command to continue adding songs to the queue, it covers both functions. The bot will auto disconnect
when the end of the queue is reached.

```
.skip <OPTIONAL amount>
```
If the bot is playing a song it will skip to the next song as long as the person is in the same
voice channel as the bot. If there are no songs after the bot will automatically disconnect.
The argument can be used to say how many songs to skip.

```
.clear
```
This will clear all songs including now playing and the queue. This is the best way to disconnect the bot,
because it flushes everything first.

```
.pause (ps)
```
This command is a useful one to pause the bot. The command has now been updated.
It will now unpause automatically after 7 minutes of being paused. This can be changed
manually under the pause command. Change the sleep(number of seconds here) to any amount of time.
Other commands can still be used including unpause during this "wait" period.

```
.unpause (resume,start,up)
```
This will unpause a currently paused bot. (Should come after a pause command)
This will automatically happen after 7 minutes after a pause command by default.

```
.queue <OPTIONAL page number> (playlist,songlist,upnext)
```
This will list all songs to be played next in pages of 10 with the currently playing
song at the top of page 1 labeled as NP. The current page and total pages are displayed
at the bottom, like so, Page: 5/6 means you are on page 5 out of a total of 6 pages.
No argument assumes page one, negative or 0 goes to page 1 and a page larger than the total
goes to the last page.

```
.shuffle
```
Shuffles all currently queued songs.
Custom implementation — shuffles in a finalized form viewable in the queue command.

```
.removequeue <position number> (rq)
```
Removes a specific song from the queue by its position number.
The position number matches the numbering shown by the `.queue` command (1 = first song after the currently playing track).
Has no effect on the currently playing song.

## PLAYLIST COMMANDS:
### NOTE:
All playlists are stored by the Discord user ID with file extension `.json`. All servers share the same folder.

```
.viewplaylist <Playlist name (case sensitive), OPTIONAL page number> (vpl)
```
Lists the songs in the specified playlist in pages of 20.
Nothing needs to be playing to use this command.

```
.listplaylists <OPTIONAL page number> (lpl)
```
Lists all of the user's playlists in pages of 10 whether or not the user is in a voice channel.

```
.deleteplaylist <Playlist name> (dpl)
```
Deletes the entire playlist with no confirmation. Permanent.

```
.deletefromplaylist <Song number, Playlist name>
```
Removes a specific song from a playlist. The song number maps to the numbering in `.viewplaylist`.
Parameters are separated by a space.

```
.createplaylist <Playlist name> (cpl)
```
Creates a new playlist using the currently playing song as the first entry.
Fails if nothing is playing.

```
.addtoplaylist <Playlist name> (atp)
```
Adds the currently playing song to the given playlist. Case sensitive.
Fails if the playlist does not exist or no song is playing.

```
.playfromlist <Playlist name> (playl)
```
Plays the entire named playlist. Case sensitive. Prints a message when all songs are loaded.

```
.renameplaylist <current name,new name> (rpl)
```
Renames an existing playlist. Names must be separated by a comma with no spaces around it.

```
.addqueuetolist <Playlist name> (aqtp)
```
Adds the entire queue to a given playlist. Does not add the currently playing song.

## CPU Commands:
##### If this functionality is undesired you can delete cpu.py from the Cogs folder. psutil is still listed in requirements.txt and can be removed if not needed.

```
.cpu_info <> (cpu)
```
Shows current CPU information such as % usage, load, and temperature.
Temperature output may require adjustment. To find the right sensor, temporarily change line 29 in `cpu.py` to:
```python
embed.description += str(psutil.sensors_temperatures(fahrenheit=False)) + " C \n"
```
This prints all available sensors so you can identify the correct one.

```
.server_info <> (serverinfo)
```
Shows permanent system information such as thread count, total RAM, and available RAM.

## Misc.

Check out our other project written in Node.js: https://github.com/RobertAndion/DiscordMusicBotNode

