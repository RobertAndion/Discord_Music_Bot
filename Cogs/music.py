import os
import re
import random
import time
import logging
import json
import discord
import lavalink
from discord.ext import commands
from lavalink.errors import ClientError
from lavalink.events import QueueEndEvent, TrackExceptionEvent, TrackStuckEvent
from lavalink.server import LoadType
import asyncio
import fileProcessing
from typing import List, Dict

log = logging.getLogger(__name__)

url_rx = re.compile(r'https?://(?:www\.)?.+')

# Enhanced search configuration with fallbacks (no ytsearch - datacenter IP blocks)
SEARCH_SOURCES = ['scsearch:', 'bandcamp:', 'http:']
PRIMARY_SEARCH_PREFIX = 'scsearch:'

# Exponential backoff retry configuration
MAX_RETRIES = 5
INITIAL_BACKOFF = 1.0
MAX_BACKOFF = 10.0
CIRCUIT_BREAKER_THRESHOLD = 3
CIRCUIT_BREAKER_TIMEOUT = 60

# Server-specific data storage paths
DATA_DIR = "ServerData"
HISTORY_FILE = "play_history.json"
VOLUME_FILE = "volume_settings.json"
QUEUE_FILE = "saved_queues.json"

config = fileProcessing.read_config()
roles = config["roles"]
voice_permissions_check_list = config["voice_permission_check_list"]
lavalink_password = os.getenv('LAVALINK_PASSWORD', 'changeme123')

@dataclass
class ServerData:
    """Per-server data management"""
    guild_id: int

    def get_data_path(self) -> str:
        return os.path.join(DATA_DIR, str(self.guild_id))

    def get_history_path(self) -> str:
        return os.path.join(self.get_data_path(), HISTORY_FILE)

    def get_volume_path(self) -> str:
        return os.path.join(self.get_data_path(), VOLUME_FILE)

    def get_queue_path(self) -> str:
        return os.path.join(self.get_data_path(), QUEUE_FILE)

class CircuitBreaker:
    """Circuit breaker for failing search sources"""
    def __init__(self):
        self.failures: Dict[str, int] = {}
        self.last_failure: Dict[str, float] = {}

    def record_success(self, source: str):
        self.failures[source] = 0
        self.last_failure.pop(source, None)

    def record_failure(self, source: str):
        self.failures[source] = self.failures.get(source, 0) + 1
        self.last_failure[source] = asyncio.get_event_loop().time()

    def is_available(self, source: str) -> bool:
        if self.failures.get(source, 0) < CIRCUIT_BREAKER_THRESHOLD:
            return True
        last_fail = self.last_failure.get(source, 0)
        current_time = asyncio.get_event_loop().time()
        return (current_time - last_fail) > CIRCUIT_BREAKER_TIMEOUT


class ServerDataManager:
    """Manages per-server data storage"""
    def __init__(self):
        self.circuit_breaker = CircuitBreaker()
        self._ensure_data_dir()

    def _ensure_data_dir(self):
        if not os.path.exists(DATA_DIR):
            os.makedirs(DATA_DIR)

    def get_server_data(self, guild_id: int) -> ServerData:
        server_path = os.path.join(DATA_DIR, str(guild_id))
        if not os.path.exists(server_path):
            os.makedirs(server_path)
        return ServerData(guild_id)

    def save_volume(self, guild_id: int, volume: int):
        server_data = self.get_server_data(guild_id)
        volume_data = {}
        if os.path.exists(server_data.get_volume_path()):
            try:
                with open(server_data.get_volume_path(), 'r') as f:
                    volume_data = json.load(f)
            except (json.JSONDecodeError, IOError):
                volume_data = {}
        volume_data[str(guild_id)] = volume
        try:
            with open(server_data.get_volume_path(), 'w') as f:
                json.dump(volume_data, f, indent=2)
        except IOError:
            log.error("Failed to save volume for guild %s", guild_id)

    def load_volume(self, guild_id: int) -> int:
        server_data = self.get_server_data(guild_id)
        if os.path.exists(server_data.get_volume_path()):
            try:
                with open(server_data.get_volume_path(), 'r') as f:
                    volume_data = json.load(f)
                    return volume_data.get(str(guild_id), 100)
            except (json.JSONDecodeError, IOError):
                log.error("Failed to load volume for guild %s", guild_id)
        return 100

    def add_to_history(self, guild_id: int, user_id: int, track_title: str, track_url: str):
        server_data = self.get_server_data(guild_id)
        history = []
        if os.path.exists(server_data.get_history_path()):
            try:
                with open(server_data.get_history_path(), 'r') as f:
                    history = json.load(f)
            except (json.JSONDecodeError, IOError):
                history = []

        # Add new entry (max 100 per server) - use wall-clock time
        history.insert(0, {
            'title': track_title,
            'url': track_url,
            'user_id': user_id,
            'timestamp': time.time()  # Wall-clock time, not monotonic
        })

        # Keep only last 100 entries
        history = history[:100]

        try:
            with open(server_data.get_history_path(), 'w') as f:
                json.dump(history, f, indent=2)
        except IOError:
            log.error("Failed to write history for guild %s", guild_id)

    def get_history(self, guild_id: int, limit: int = 10) -> List[Dict]:
        server_data = self.get_server_data(guild_id)
        if os.path.exists(server_data.get_history_path()):
            try:
                with open(server_data.get_history_path(), 'r') as f:
                    history = json.load(f)
                    return history[:limit]
            except (json.JSONDecodeError, IOError):
                log.error("Failed to read history for guild %s", guild_id)
        return []

class LavalinkVoiceClient(discord.VoiceProtocol):
    def __init__(self, client: discord.Client, channel: discord.abc.Connectable):
        self.client = client
        self.channel = channel
        self.guild_id = channel.guild.id
        self._destroyed = False

        if not hasattr(self.client, 'lavalink'):
            self.client.lavalink = lavalink.Client(client.user.id)
            self.client.lavalink.add_node(
                host='localhost',
                port=2333,
                password=lavalink_password,
                region='us',
                name='default-node'
            )

        self.lavalink = self.client.lavalink

    async def on_voice_server_update(self, data):
        lavalink_data = {
            't': 'VOICE_SERVER_UPDATE',
            'd': data
        }
        await self.lavalink.voice_update_handler(lavalink_data)

    async def on_voice_state_update(self, data):
        channel_id = data['channel_id']

        if not channel_id:
            await self._destroy()
            return

        channel = self.client.get_channel(int(channel_id))
        if channel is not None:
            self.channel = channel

        lavalink_data = {
            't': 'VOICE_STATE_UPDATE',
            'd': data
        }
        await self.lavalink.voice_update_handler(lavalink_data)

    async def connect(self, *, timeout: float, reconnect: bool, self_deaf: bool = False, self_mute: bool = False) -> None:
        self.lavalink.player_manager.create(guild_id=self.channel.guild.id)
        await self.channel.guild.change_voice_state(channel=self.channel, self_mute=self_mute, self_deaf=self_deaf)

    async def disconnect(self, *, force: bool = False) -> None:
        player = self.lavalink.player_manager.get(self.channel.guild.id)

        if player is None or (not force and not player.is_connected):
            return

        await self.channel.guild.change_voice_state(channel=None)

        player.channel_id = None
        await self._destroy()

    async def _destroy(self):
        self.cleanup()

        if self._destroyed:
            return

        self._destroyed = True

        try:
            await self.lavalink.player_manager.destroy(self.guild_id)
        except ClientError:
            pass


class music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._auto_unpause_guilds: set = set()
        self.server_manager = ServerDataManager()
        self.loop_modes = {}  # guild_id -> 'none' | 'song' | 'queue'

        if not hasattr(bot, 'lavalink'):
            bot.lavalink = lavalink.Client(bot.user.id)
            bot.lavalink.add_node(
                host='127.0.0.1', port=2333, password=lavalink_password, region='us', name='default-node')

        self.lavalink: lavalink.Client = bot.lavalink
        self.lavalink.add_event_hooks(self)

    def cog_unload(self):
        self.lavalink._event_hooks.clear()

    async def cog_before_invoke(self, ctx):
        guild_check = ctx.guild is not None

        if guild_check:
            await self.ensure_voice(ctx)

        return guild_check

    async def cog_command_error(self, ctx, error):
        if isinstance(error, commands.CommandInvokeError):
            await ctx.send(error.original)

    async def ensure_voice(self, ctx):
        player = self.bot.lavalink.player_manager.create(ctx.guild.id)

        should_connect = ctx.command.name in voice_permissions_check_list

        if not ctx.author.voice or not ctx.author.voice.channel:
            raise commands.CommandInvokeError('Join a voicechannel first.')

        v_client = ctx.voice_client
        if not v_client:
            if not should_connect:
                raise commands.CommandInvokeError('Not connected.')

            permissions = ctx.author.voice.channel.permissions_for(ctx.me)

            if not permissions.connect or not permissions.speak:
                raise commands.CommandInvokeError(
                    'I need the `CONNECT` and `SPEAK` permissions.')

            player.store('channel', ctx.channel.id)
            await ctx.author.voice.channel.connect(cls=LavalinkVoiceClient)
        else:
            if v_client.channel.id != ctx.author.voice.channel.id:
                raise commands.CommandInvokeError(
                    'You need to be in my voicechannel.')

    def _player_channel(self, player):
        """The text channel a player was started from, if we still can see it."""
        channel_id = player.fetch('channel')
        return self.bot.get_channel(channel_id) if channel_id else None

    async def _load_tracks(self, player, query, use_fallbacks=True):
        """Load tracks with enhanced retry logic and fallback sources.

        Args:
            player: Lavalink player
            query: Search query or URL
            use_fallbacks: Whether to try alternative sources if primary fails

        Returns results object or None if all attempts fail.
        """
        # Check if this is a direct URL - if so, don't use search prefixes
        is_url = bool(url_rx.match(query))

        if is_url:
            # Direct URL - no search prefixes, just retry logic
            for attempt in range(MAX_RETRIES):
                try:
                    results = await player.node.get_tracks(query)
                    if results and results.tracks:
                        return results
                    elif results and not results.tracks:
                        return None  # URL returned no results
                    else:
                        raise Exception("No results returned from Lavalink")

                except Exception as exc:
                    log.warning(
                        "URL load error for %r (attempt %d/%d): %s",
                        query, attempt + 1, MAX_RETRIES, exc)

                    if attempt < MAX_RETRIES - 1:
                        backoff = min(INITIAL_BACKOFF * (2 ** attempt), MAX_BACKOFF)
                        await asyncio.sleep(backoff)
            return None

        # Extract search source if present
        search_source = None
        base_query = query
        for source in SEARCH_SOURCES:
            if query.startswith(source):
                search_source = source
                base_query = query[len(source):]
                break

        # Build list of sources to try - always use fallbacks for searches
        sources_to_try = []
        if search_source and not use_fallbacks:
            sources_to_try = [search_source]
        elif search_source:
            # If source specified but fallbacks enabled, include all sources starting with specified
            sources_to_try = [search_source] + [s for s in SEARCH_SOURCES if s != search_source]
        elif use_fallbacks:
            sources_to_try = SEARCH_SOURCES.copy()
        else:
            sources_to_try = [PRIMARY_SEARCH_PREFIX]

        # Try each source with exponential backoff
        for source in sources_to_try:
            # Check circuit breaker
            if not self.server_manager.circuit_breaker.is_available(source):
                log.warning("Source %s is circuit-breaked, skipping", source)
                continue

            full_query = f"{source}{base_query}"

            for attempt in range(MAX_RETRIES):
                try:
                    results = await player.node.get_tracks(full_query)

                    if results and results.tracks:
                        self.server_manager.circuit_breaker.record_success(source)
                        return results
                    elif results and not results.tracks:
                        # No results for this search, try next source
                        log.info("No results from %s for query: %s", source, base_query)
                        break
                    else:
                        raise Exception("No results returned from Lavalink")

                except Exception as exc:
                    log.warning(
                        "Track load error from %s for %r (attempt %d/%d): %s",
                        source, base_query, attempt + 1, MAX_RETRIES, exc)

                    # Exponential backoff
                    if attempt < MAX_RETRIES - 1:
                        backoff = min(INITIAL_BACKOFF * (2 ** attempt), MAX_BACKOFF)
                        await asyncio.sleep(backoff)
                    else:
                        # Max retries reached, record failure and try next source
                        self.server_manager.circuit_breaker.record_failure(source)
                        log.error("All retries exhausted for %s with source %s", base_query, source)
                        break

        return None

    async def _apply_volume(self, player, guild_id: int):
        """Apply server-specific volume setting to player"""
        volume = self.server_manager.load_volume(guild_id)
        await player.set_volume(volume)

    async def _notify_skip(self, player, track, reason):
        """Tell the channel we're skipping a track that couldn't be played."""
        title = getattr(track, 'title', None) or 'that track'
        log.warning("Skipping %s: %s", title, reason)
        channel = self._player_channel(player)
        if channel is not None:
            try:
                await channel.send(
                    f"⚠️ Couldn't play **{title}** ({reason}). Skipping.")
            except discord.HTTPException:
                pass

    @lavalink.listener(TrackExceptionEvent)
    async def on_track_exception(self, event: TrackExceptionEvent):
        """Handle track streaming failures with enhanced logging"""
        await self._notify_skip(
            event.player, event.track,
            getattr(event, 'message', None) or 'stream error')

    @lavalink.listener(TrackStuckEvent)
    async def on_track_stuck(self, event: TrackStuckEvent):
        """Handle stuck tracks"""
        await self._notify_skip(event.player, event.track, 'stalled')
        try:
            await event.player.skip()
        except Exception as exc:
            log.warning("Failed to skip stuck track: %s", exc)

    @lavalink.listener(QueueEndEvent)
    async def on_queue_end(self, event: QueueEndEvent):
        """Handle queue end with loop mode support"""
        guild_id = event.player.guild_id
        loop_mode = self.loop_modes.get(guild_id, 'none')

        # Handle loop modes
        if loop_mode == 'song' and event.player.current:
            # Re-add current song to queue
            track = event.player.current
            track.extra["requester"] = track.extra.get("requester", 0)
            event.player.add(track=track)
            await event.player.play()
            return

        guild = self.bot.get_guild(guild_id)
        if guild is not None and guild.voice_client is not None:
            await guild.voice_client.disconnect(force=True)

    @commands.command(name='play', description="Play a song by name or URL")
    @commands.has_any_role(*roles)
    async def play_song(self, ctx, *, query: str):
        """Play a song with enhanced retry logic and fallbacks"""
        fileProcessing.logUpdate(ctx, query)
        player = self.bot.lavalink.player_manager.get(ctx.guild.id)
        player.store('channel', ctx.channel.id)
        query = query.strip('<>')

        # Don't prepend search prefix to URLs - let _load_tracks handle them
        if not url_rx.match(query):
            query = f'{PRIMARY_SEARCH_PREFIX}{query}'

        results = await self._load_tracks(player, query, use_fallbacks=True)

        if results is None:
            return await ctx.send("❌ The music server isn't responding right now — try again in a moment.")

        if not results.tracks:
            return await ctx.send('🔍 No results found!')

        embed = discord.Embed(color=discord.Color.blurple())

        if results.load_type == LoadType.PLAYLIST:
            tracks = results.tracks
            for track in tracks:
                track.extra["requester"] = ctx.author.id
                player.add(track=track)

            embed.title = '📋 Playlist Enqueued!'
            embed.description = f'**{results.playlist_info.name}** — {len(tracks)} tracks'
        else:
            track = results.tracks[0]
            embed.title = '🎵 Track Enqueued'
            embed.description = f'[{track.title}]({track.uri})'

            track.extra["requester"] = ctx.author.id
            player.add(track=track)

            # Add to server history
            self.server_manager.add_to_history(ctx.guild.id, ctx.author.id, track.title, track.uri)

        await ctx.send(embed=embed)

        if not player.is_playing:
            await self._apply_volume(player, ctx.guild.id)
            await player.play()

    @commands.command(name='search', description="Search for songs and choose from results")
    @commands.has_any_role(*roles)
    async def search_song(self, ctx, *, query: str):
        """Search for songs with interactive results"""
        player = self.bot.lavalink.player_manager.get(ctx.guild.id)
        player.store('channel', ctx.channel.id)

        search_query = f'{PRIMARY_SEARCH_PREFIX}{query}'
        results = await self._load_tracks(player, search_query, use_fallbacks=False)

        if not results or not results.tracks:
            return await ctx.send('🔍 No results found!')

        # Show top 5 results
        embed = discord.Embed(color=discord.Color.blurple())
        embed.title = f'🔍 Search Results: {query}'
        embed.description = "Choose a number (1-5) or `cancel`\n"

        for i, track in enumerate(results.tracks[:5], 1):
            duration = f"{track.length // 60000}:{(track.length % 60000) // 1000:02d}"
            embed.description += f"`{i}.` **{track.title}** (`{duration}`)\n"

        search_msg = await ctx.send(embed=embed)

        # Wait for user response
        try:
            response = await self.bot.wait_for(
                'message',
                check=lambda m: m.author == ctx.author and m.channel == ctx.channel,
                timeout=30.0
            )

            if response.content.lower() == 'cancel':
                await search_msg.delete()
                return await ctx.send('❌ Search cancelled.')

            choice = int(response.content) - 1
            if 0 <= choice < min(5, len(results.tracks)):
                track = results.tracks[choice]
                track.extra["requester"] = ctx.author.id
                player.add(track=track)

                # Add to history
                self.server_manager.add_to_history(ctx.guild.id, ctx.author.id, track.title, track.uri)

                embed = discord.Embed(color=discord.Color.blurple())
                embed.title = '🎵 Track Enqueued'
                embed.description = f'[{track.title}]({track.uri})'
                await ctx.send(embed=embed)

                if not player.is_playing:
                    await self._apply_volume(player, ctx.guild.id)
                    await player.play()
            else:
                await ctx.send('❌ Invalid choice.')
        except (ValueError, asyncio.TimeoutError):
            await ctx.send('❌ Invalid input or timeout.')

    @commands.command(name='volume', description="Set volume (0-200, default 100)")
    @commands.has_any_role(*roles)
    async def set_volume(self, ctx, volume: int):
        """Set volume per server (0-200%)"""
        if not 0 <= volume <= 200:
            return await ctx.send('❌ Volume must be between 0 and 200.')

        player = self.bot.lavalink.player_manager.get(ctx.guild.id)

        # Safety check - ensure bot is connected
        if not ctx.voice_client:
            return await ctx.send('❌ Bot is not connected to voice.')

        await player.set_volume(volume)
        self.server_manager.save_volume(ctx.guild.id, volume)

        await ctx.send(f'🔊 Volume set to **{volume}%**')

    @commands.command(name='loop', description="Enable looping: song, queue, or disable")
    @commands.has_any_role(*roles)
    async def set_loop(self, ctx, mode: str = None):
        """Set loop mode (song/queue/disable)"""
        guild_id = ctx.guild.id
        current_mode = self.loop_modes.get(guild_id, 'none')

        if not mode:
            return await ctx.send(f'🔄 Current loop mode: **{current_mode}**')

        mode = mode.lower()
        if mode not in ['song', 'queue', 'disable', 'none']:
            return await ctx.send('❌ Usage: `.loop [song/queue/disable]`')

        if mode in ['disable', 'none']:
            self.loop_modes[guild_id] = 'none'
            await ctx.send('🔄 Loop disabled.')
        elif mode in ['song', 'queue']:
            self.loop_modes[guild_id] = mode
            await ctx.send(f'🔄 Loop mode set to **{mode}**')

    @commands.command(name='history', description="Show play history for this server")
    @commands.has_any_role(*roles)
    async def show_history(self, ctx, limit: int = 10):
        """Show server-specific play history"""
        if not 1 <= limit <= 50:
            return await ctx.send('❌ Limit must be between 1 and 50.')

        history = self.server_manager.get_history(ctx.guild.id, limit)

        if not history:
            return await ctx.send('📭 No play history for this server.')

        embed = discord.Embed(color=discord.Color.blurple())
        embed.title = f'📜 Play History (Last {len(history)} tracks)'
        embed.description = ""  # Initialize to prevent TypeError

        for i, entry in enumerate(history, 1):
            embed.description += f"`{i}.` **{entry['title']}**\n"

        await ctx.send(embed=embed)

    @commands.command(name='resume', aliases=['unpause', 'start', 'up'], description="Resume paused playback")
    @commands.has_any_role(*roles)
    async def unpause_bot(self, ctx):
        """Resume playback with clearer name"""
        player = self.bot.lavalink.player_manager.get(ctx.guild.id)
        if not player:
            raise commands.CommandInvokeError("Nothing playing.")
        if player.paused:
            await ctx.send("▶️ Resuming playback.")
            await player.set_pause(False)
        else:
            raise commands.CommandInvokeError("Nothing is paused to resume.")

    @commands.command(name='stop', description="Stop playback and clear queue")
    @commands.has_any_role(*roles)
    async def stop_bot(self, ctx):
        """Stop playback (more intuitive than .clear)"""
        player = self.bot.lavalink.player_manager.get(ctx.guild.id)

        if not ctx.voice_client:
            return await ctx.send('Not connected.')

        if not ctx.author.voice or (player.is_connected and ctx.author.voice.channel.id != int(player.channel_id)):
            return await ctx.send('You\'re not in my voicechannel!')

        await player.stop()
        await ctx.voice_client.disconnect(force=True)
        await ctx.send('⏹️ Playback stopped and bot disconnected.')

    @commands.command(name='remove', aliases=['rq'], description="Remove song from queue by position")
    @commands.has_any_role(*roles)
    async def remove_from_queue(self, ctx, position: int):
        """Remove song from queue (shorter command name)"""
        player = self.bot.lavalink.player_manager.get(ctx.guild.id)

        if not player or not player.is_playing:
            return await ctx.send("Nothing is queued.")

        queue_length = len(player.queue)
        if queue_length == 0:
            return await ctx.send("There are no queued songs to remove.")

        if position < 1 or position > queue_length:
            return await ctx.send(f"Please provide a position between 1 and {queue_length}.")

        removed = player.queue.pop(position - 1)
        await ctx.send(f"🗑️ Removed **{removed.title}** from the queue.")

    @commands.command(name="playfromlist", aliases=["pfpl", "playl"], description="Loads a playlist into the queue to be played.")
    @commands.has_any_role(*roles)
    async def play_from_list(self, ctx, *, playlist_name):
        """Play from playlist with enhanced retry logic"""
        fileProcessing.logUpdate(ctx, playlist_name)
        songlist = fileProcessing.play_playlist(ctx, playlist_name)
        if songlist is False:
            return await ctx.send("❌ Playlist not found.")

        player = self.bot.lavalink.player_manager.get(ctx.guild.id)
        skipped = 0

        # Load first song
        results = await self._load_tracks(player, f'{PRIMARY_SEARCH_PREFIX}{songlist[0]}')
        if results and results.tracks:
            track = results.tracks[0]
            track.extra["requester"] = ctx.author.id
            player.add(track=track)

            # Add to history
            self.server_manager.add_to_history(ctx.guild.id, ctx.author.id, track.title, track.uri)

            if not player.is_playing:
                await self._apply_volume(player, ctx.guild.id)
                await player.play()
        else:
            skipped += 1

        songlist.pop(0)

        # Load remaining songs
        for song in songlist:
            results = await self._load_tracks(player, f'{PRIMARY_SEARCH_PREFIX}{song}')
            if results is None or not results.tracks:
                skipped += 1
                continue
            track = results.tracks[0]
            track.extra["requester"] = ctx.author.id
            player.add(track=track)

        message = f"📋 **{playlist_name}** loaded successfully."
        if skipped:
            message += f" ({skipped} song(s) couldn't be found and were skipped.)"
        await ctx.send(message)

    @commands.command(name='skip', description="Skip currently playing song (or multiple)")
    @commands.has_any_role(*roles)
    async def skip_song(self, ctx, amount: int = 1):
        """Skip current song with better feedback"""
        try:
            player = self.bot.lavalink.player_manager.get(ctx.guild.id)
            skipped_count = 0

            while amount > 0:
                amount -= 1
                if not player.is_playing:
                    if skipped_count == 0:
                        raise commands.CommandInvokeError("Nothing playing to skip.")
                    break

                await player.skip()
                skipped_count += 1

                if amount > 0:
                    await asyncio.sleep(.1)

            if skipped_count > 0:
                await ctx.send(f"⏭️ Skipped **{skipped_count}** song(s).")

        except Exception:
            if amount > 0:
                return await ctx.send("⏭️ All songs skipped.")

    @commands.command(name='clear', description="Clear all songs and disconnect")
    @commands.has_any_role(*roles)
    async def clear_queue(self, ctx):
        """Clear queue (alias for stop)"""
        await self.stop_bot(ctx)

    @commands.command(name='pause', aliases=["ps"], description="Pauses a song if one is playing.")
    @commands.has_any_role(*roles)
    async def pause_bot(self, ctx):
        player = self.bot.lavalink.player_manager.get(ctx.guild.id)
        if not player:
            raise commands.CommandInvokeError("Unable to retrieve player...")
        if not player.is_playing:
            return await ctx.send("No song is playing to be paused.")
        if ctx.guild.id in self._auto_unpause_guilds:
            return await ctx.send("Song is already paused.")

        self._auto_unpause_guilds.add(ctx.guild.id)
        await player.set_pause(True)
        await ctx.send("Song has been paused.")
        try:
            for _ in range(84):
                await asyncio.sleep(5)
                if not player.paused:
                    break
            else:
                if player.is_playing:
                    await player.set_pause(False)
                    await ctx.send("Automatically unpaused.")
        finally:
            self._auto_unpause_guilds.discard(ctx.guild.id)

    @commands.command(name='queue', aliases=['playlist', 'songlist', 'upnext'], description="Shows songs up next in order")
    @commands.has_any_role(*roles)
    async def queue(self, ctx, page=1):
        """Show queue with improved formatting"""
        if not isinstance(page, int):
            raise commands.CommandInvokeError("Please enter a valid number.")

        player = self.bot.lavalink.player_manager.get(ctx.guild.id)
        if not player.is_playing:
            return await ctx.send("📭 Nothing is queued.")

        songlist = player.queue
        list_collection = []
        complete_list = ''

        # Add currently playing track
        current = player.current
        loop_mode = self.loop_modes.get(ctx.guild.id, 'none')
        loop_indicator = "🔁 " if loop_mode == 'song' else ("🔁 " if loop_mode == 'queue' else "")

        complete_list = f"{loop_indicator}**NP:** {current.title}\n"

        i = 0
        for song in songlist:
            complete_list += f"`{i + 1}.` {song.title}\n"
            i += 1
            if i % 10 == 0:
                list_collection.append(complete_list)
                complete_list = ''

        if i % 10 != 0 or i == 0:
            list_collection.append(complete_list)

        selection = int(page - 1)
        embed = discord.Embed(color=discord.Color.blurple())
        embed.title = f'🎵 Queue ({len(songlist)} songs)'

        if selection < 0:
            list_collection[0] += f"\nPage: 1/{len(list_collection)}"
            embed.description = list_collection[0]
        elif selection > len(list_collection) - 1:
            list_collection[len(list_collection) - 1] += f"\nPage: {len(list_collection)}/{len(list_collection)}"
            embed.description = list_collection[len(list_collection) - 1]
        else:
            list_collection[selection] += f"\nPage: {page}/{len(list_collection)}"
            embed.description = list_collection[selection]

        await ctx.send(embed=embed)

    @commands.command(name="shuffle", description="Shuffles the current queue")
    @commands.has_any_role(*roles)
    async def shuffle(self, ctx):
        """Shuffle queue with better feedback"""
        player = self.bot.lavalink.player_manager.get(ctx.guild.id)
        if not player or not player.is_playing:
            return await ctx.send("❌ Nothing playing to shuffle.")
        if not player.queue:
            return await ctx.send("❌ Nothing queued to shuffle.")

        random.shuffle(player.queue)
        await ctx.send("🔀 Queue shuffled.")


async def setup(bot):
    await bot.add_cog(music(bot))
