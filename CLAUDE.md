# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Running the Bot

**Docker (recommended):**
```bash
cp .env.example .env          # add DISCORD_TOKEN and LAVALINK_PASSWORD
docker build -f Docker/Dockerfile -t musicbot .
docker volume create musicbot-playlists
docker volume create musicbot-songlogs
docker volume create musicbot-plugins
sh run.sh
```

**Manual (requires Java 21+ and Python 3):**
```bash
pip3 install -r requirements.txt
# Download Lavalink.jar and place it in the project root
cp .env.example .env
sh startup.sh                 # starts Lavalink + bot; needs tmux for .reboot support
```

**Dependency install only:**
```bash
pip3 install -r requirements.txt
```

There is no test suite or linter configured.

## Architecture

The bot has two runtime processes that must both be running:
1. **Lavalink** — a Java audio server on `localhost:2333` that handles audio streaming
2. **bot.py** — the Python Discord bot that connects to Lavalink via the `lavalink` Python client

`startup.sh` launches Lavalink in the background, waits for it to be reachable on port 2333, then starts `bot.py`. The Docker container does the same automatically.

### Extension Loading

`bot.py` loads extensions on `on_ready`:
- `playlist` — loaded directly from `playlist.py` in the project root
- `Cogs.*` — every `.py` file in the `Cogs/` directory is auto-loaded (currently `music.py` and `cpu.py`)

To add a new cog, drop a `.py` file into `Cogs/` with a standard `async def setup(bot)` function. It will be picked up automatically on next start.

### Module Responsibilities

| File | Role |
|------|------|
| `bot.py` | Bot entry point, owner-only commands (`.reboot`, `.backupPlaylists`), extension loading |
| `Cogs/music.py` | All playback commands; owns the `LavalinkVoiceClient` and `lavalink.Client` instance |
| `playlist.py` | Playlist management commands; delegates all I/O to `fileProcessing` |
| `fileProcessing.py` | Pure file I/O — playlists, song logs, config; no Discord objects except `ctx` for author ID |
| `Cogs/cpu.py` | Optional system info commands; can be deleted if not needed |
| `Resources/config.json` | Role names that can use music commands + list of commands that trigger voice channel joining |

### Lavalink Client Lifecycle

`LavalinkVoiceClient` (in `Cogs/music.py`) is the Discord `VoiceProtocol` implementation. It initializes `bot.lavalink` on first connection. The `music` cog also initializes `bot.lavalink` in `__init__` as a fallback. Both guards check `hasattr(bot, 'lavalink')` so only one `lavalink.Client` is ever created. The client is stored on `bot` so `playlist.py` can access it via `self.bot.lavalink`.

### Data Storage

- **Playlists**: `Playlist/<discord_user_id>.json` — a dict mapping playlist name → list of song title strings
- **Song logs**: `SongLog/<discord_user_id>.txt` — append-only log of played song names/queries
- **Config**: `Resources/config.json` — roles and voice-gating command list

### Role and Voice Gating

All music and playlist commands require the user to have one of the roles listed in `config.json["roles"]`. Commands in `config.json["voice_permission_check_list"]` additionally require the caller to be in a voice channel and will make the bot join that channel. Commands not in that list (e.g. `.queue`, `.viewplaylist`) only need the user to already be in the bot's channel.

## Key Configuration Points

- **Lavalink password**: Set in `.env` as `LAVALINK_PASSWORD` (default `changeme123`). Must match `application.yml` → `lavalink.server.password`. The Python side reads it via `os.getenv('LAVALINK_PASSWORD', 'changeme123')` in `Cogs/music.py`.
- **Allowed roles**: Edit `Resources/config.json` `"roles"` list. Names are case-sensitive and matched against Discord role names.
- **Auto-unpause timeout**: In `Cogs/music.py` `pause_bot`, the loop runs 84 × 5 s = 420 s (7 minutes) before auto-unpausing. Adjust the `range(84)` or `sleep(5)` values to change the timeout.
- **YouTube plugin**: `application.yml` uses `dev.lavalink.youtube:youtube-plugin` because native YouTube source is disabled. Plugin is downloaded on first Lavalink startup into the `plugins/` volume.
