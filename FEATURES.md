# New Features Documentation

## Enhanced SoundCloud Performance

### Retry Logic & Fallbacks
- **Exponential backoff**: 5 retries with increasing delays (1s → 10s max)
- **Circuit breaker**: Temporarily disables failing sources (3 failures → 60s timeout)
- **Smart fallbacks**: SoundCloud → Bandcamp → HTTP (no YouTube - datacenter blocked)
- **Per-source tracking**: Individual success/failure monitoring

### Configuration
```python
# Music cog constants
SEARCH_SOURCES = ['scsearch:', 'bandcamp:', 'http:']
MAX_RETRIES = 5
INITIAL_BACKOFF = 1.0
CIRCUIT_BREAKER_THRESHOLD = 3
```

## Per-Server Features

### Volume Control
```bash
.volume 80    # Set volume to 80% for this server
.volume 150   # Set volume to 150% (boosted)
```
- **Range**: 0-200% (default 100%)
- **Scope**: Server-specific (no cross-server interference)
- **Persistence**: Saved in `ServerData/{guild_id}/volume_settings.json`

### Play History
```bash
.history       # Show last 10 songs on this server
.history 25   # Show last 25 songs (max 50)
```
- **Storage**: `ServerData/{guild_id}/play_history.json`
- **Limit**: 100 songs per server (FIFO)
- **Isolation**: Completely server-separated

## New Commands

### Search & Discovery
```bash
.search lofi hip hop    # Shows 5 results, pick number 1-5
.history                # Show server play history
```

### Playback Control
```bash
.loop song              # Loop current track
.loop queue             # Loop entire queue
.loop disable           # Disable looping
.resume                 # Resume playback (was .unpause)
.stop                   # Stop and disconnect (was .clear)
.remove 3               # Remove 3rd song in queue
```

### Queue Management
```bash
.queue                  # Show queue with loop indicator
.shuffle                # Randomize queue order
```

## Data Structure

### Server Data Directory
```
ServerData/
├── {guild_id}/
│   ├── play_history.json      # Last 100 tracks
│   ├── volume_settings.json   # Per-server volume
│   └── saved_queues.json      # Queue persistence (future)
```

### History Entry Format
```json
{
  "title": "Song Name",
  "url": "https://soundcloud.com/...",
  "user_id": 123456789,
  "timestamp": 1234567890.12
}
```

## Error Handling Improvements

### Circuit Breaker Pattern
- Tracks failures per search source
- Temporarily disables problematic sources
- Auto-recovers after timeout period

### Enhanced User Feedback
- Clear error messages with emojis
- Specific failure reasons (network, source error, etc.)
- Actionable suggestions (try again, check spelling, etc.)

## Performance Monitoring

### Logging
- Structured logs with correlation IDs
- Performance metrics (latency, success rates)
- Circuit breaker state changes
- Search source performance

### Success Metrics
- SoundCloud success rate: ~85% → 98% (target)
- Average load time: ~3s → <1s (target)
- Error recovery: Automatic with fallbacks

## Migration Notes

### Command Changes
- `.unpause` → `.resume` (more intuitive)
- `.clear` → `.stop` (better naming)
- `.removequeue` → `.remove` (shorter)
- Aliases preserved for compatibility

### Data Migration
- Existing playlists: No changes needed
- Volume settings: Auto-created on first use
- History: Starts fresh, accumulates over time

## Future Enhancements

### Planned Features
- Audio filters (bassboost, nightcore, etc.)
- Queue move/reorder commands
- Duplicate detection
- Smart auto-play (similar tracks)
- Lyrics integration
- Admin features (blacklist, rate limiting)

### Discord Slash Commands
- Full autocomplete support
- Better validation
- Richer response types
- Integration with Discord's command UI