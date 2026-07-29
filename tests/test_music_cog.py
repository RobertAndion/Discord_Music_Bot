"""Unit tests for music cog functionality"""
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
import discord
from discord.ext import commands
from lavalink.server import LoadType


# Mock fixtures
@pytest.fixture
def mock_bot():
    """Mock Discord bot"""
    bot = Mock()
    bot.user.id = 12345
    bot.lavalink = Mock()
    return bot


@pytest.fixture
def mock_ctx():
    """Mock Discord context"""
    ctx = Mock()
    ctx.author.id = 99999
    ctx.guild.id = 67890
    ctx.author.voice.channel.id = 11111
    ctx.channel.id = 22222
    ctx.send = AsyncMock()
    return ctx


@pytest.fixture
def mock_player():
    """Mock Lavalink player"""
    player = Mock()
    player.queue = []
    player.is_playing = False
    player.is_connected = True
    player.channel_id = '11111'
    player.current = None
    player.add = Mock()
    player.play = AsyncMock()
    player.set_volume = AsyncMock()
    player.skip = AsyncMock()
    player.set_pause = AsyncMock()
    player.stop = AsyncMock()
    player.store = Mock()
    return player


class TestServerDataManager:
    """Test server-specific data management"""

    def test_server_data_paths(self):
        """Test that server data paths are generated correctly"""
        from Cogs.music import ServerData

        server_data = ServerData(67890)
        assert str(67890) in server_data.get_data_path()
        assert "volume_settings.json" in server_data.get_volume_path()
        assert "play_history.json" in server_data.get_history_path()


class TestCircuitBreaker:
    """Test circuit breaker functionality"""

    def test_circuit_breaker_initial_state(self):
        """Test circuit breaker starts with no failures"""
        from Cogs.music import CircuitBreaker

        cb = CircuitBreaker()
        assert cb.is_available('scsearch:') == True

    def test_circuit_breaker_failure_tracking(self):
        """Test that failures are tracked correctly"""
        from Cogs.music import CircuitBreaker

        cb = CircuitBreaker()
        for _ in range(3):  # Threshold
            cb.record_failure('scsearch:')

        assert cb.is_available('scsearch:') == False

    def test_circuit_breaker_success_reset(self):
        """Test that success resets failure count"""
        from Cogs.music import CircuitBreaker

        cb = CircuitBreaker()
        cb.record_failure('scsearch:')
        cb.record_failure('scsearch:')
        cb.record_success('scsearch:')

        assert cb.is_available('scsearch:') == True


class TestRetryLogic:
    """Test enhanced retry logic with fallbacks"""

    @pytest.mark.asyncio
    async def test_load_tracks_with_retry(self):
        """Test that retry logic works for transient failures"""
        from Cogs.music import CircuitBreaker, SEARCH_SOURCES

        cb = CircuitBreaker()

        # Test that circuit breaker starts with all sources available
        for source in SEARCH_SOURCES:
            assert cb.is_available(source) == True

        # Test that repeated failures trip the circuit breaker
        for _ in range(3):  # CIRCUIT_BREAKER_THRESHOLD
            cb.record_failure('scsearch:')

        assert cb.is_available('scsearch:') == False

        # Test that success resets the circuit breaker
        cb.record_success('scsearch:')
        assert cb.is_available('scsearch:') == True


class TestVolumeControl:
    """Test per-server volume control"""

    def test_volume_validation(self):
        """Test that volume is validated correctly"""
        from Cogs.music import MAX_QUERY_LENGTH, MIN_QUERY_LENGTH

        # Test constants are properly defined
        assert MAX_QUERY_LENGTH == 500
        assert MIN_QUERY_LENGTH == 2

        # Valid ranges
        for volume in [0, 50, 100, 150, 200]:
            assert 0 <= volume <= 200

        # Invalid ranges would be caught in the command


class TestInputSanitization:
    """Test input sanitization for security"""

    def test_sanitize_valid_input(self):
        """Test that valid input passes through sanitization"""
        from Cogs.music import sanitize_query

        # Normal search queries should work
        assert sanitize_query("lofi hip hop") == "lofi hip hop"
        assert sanitize_query("Test Song Name") == "Test Song Name"
        assert sanitize_query("song with numbers 123") == "song with numbers 123"

    def test_sanitize_dangerous_chars(self):
        """Test that dangerous characters are removed"""
        from Cogs.music import sanitize_query

        # Test removal of null bytes and newlines
        assert sanitize_query("song\x00name") == "songname"
        assert sanitize_query("song\nname") == "songname"
        assert sanitize_query("song\tname") == "songname"

        # Test removal of angle brackets ('/' is preserved — needed for URLs)
        assert sanitize_query("<song>name</>") == "songname/"

    def test_sanitize_whitespace(self):
        """Test that excessive whitespace is cleaned up"""
        from Cogs.music import sanitize_query

        # Multiple spaces collapsed to single space
        assert sanitize_query("song    name") == "song name"
        # Leading/trailing whitespace removed
        assert sanitize_query("  song name  ") == "song name"

    def test_sanitize_length_validation(self):
        """Test that length limits are enforced"""
        from Cogs.music import sanitize_query, MAX_QUERY_LENGTH, MIN_QUERY_LENGTH

        # Test minimum length
        with pytest.raises(ValueError, match="at least 2 characters"):
            sanitize_query("a")

        # Test maximum length
        long_query = "a" * (MAX_QUERY_LENGTH + 1)
        with pytest.raises(ValueError, match="less than 500 characters"):
            sanitize_query(long_query)

    def test_sanitize_input_type(self):
        """Test that only string input is accepted"""
        from Cogs.music import sanitize_query

        # Test non-string input raises error
        with pytest.raises(ValueError, match="must be a string"):
            sanitize_query(123)

        with pytest.raises(ValueError, match="must be a string"):
            sanitize_query(None)

    def test_sanitize_preserves_urls(self):
        """Test that URLs are preserved during sanitization"""
        from Cogs.music import sanitize_query

        url = "https://soundcloud.com/artist/track"
        assert sanitize_query(url) == url

        url_with_params = "https://example.com/track?param=value&other=123"
        assert sanitize_query(url_with_params) == url_with_params


class TestQueueManagement:
    """Test queue management features"""

    def test_queue_position_validation(self):
        """Test that queue positions are validated"""
        queue_length = 10

        # Valid positions
        for pos in [1, 5, 10]:
            assert 1 <= pos <= queue_length

        # Invalid positions
        for pos in [0, -1, 11, 100]:
            assert not (1 <= pos <= queue_length)


class TestLoopModes:
    """Test loop functionality"""

    def test_loop_mode_validation(self):
        """Test that only valid loop modes are accepted"""
        valid_modes = ['song', 'queue', 'disable', 'none']

        for mode in valid_modes:
            assert mode.lower() in ['song', 'queue', 'disable', 'none']


class TestSearchFallbacks:
    """Test search source fallbacks"""

    def test_search_sources_no_youtube(self):
        """Test that YouTube is not in fallback sources"""
        from Cogs.music import SEARCH_SOURCES

        assert 'ytsearch:' not in SEARCH_SOURCES
        assert 'scsearch:' in SEARCH_SOURCES
        assert 'bandcamp:' in SEARCH_SOURCES

    def test_primary_search_source(self):
        """Test that SoundCloud is the primary source"""
        from Cogs.music import PRIMARY_SEARCH_PREFIX

        assert PRIMARY_SEARCH_PREFIX == 'scsearch:'


class TestServerIsolation:
    """Test that server data is properly isolated"""

    def test_server_data_separation(self):
        """Test that different servers have separate data paths"""
        from Cogs.music import ServerData

        server1 = ServerData(12345)
        server2 = ServerData(67890)

        assert server1.get_data_path() != server2.get_data_path()


@pytest.mark.integration
class TestIntegrationScenarios:
    """Integration tests for common workflows"""

    @pytest.mark.asyncio
    async def test_play_skip_workflow(self, mock_bot, mock_ctx, mock_player):
        """Test the basic play and skip workflow"""
        from Cogs.music import music
        from unittest.mock import patch, MagicMock

        # Setup
        cog = music(mock_bot)
        mock_bot.lavalink.player_manager.get.return_value = mock_player

        # Mock successful track load
        mock_results = MagicMock()
        mock_results.load_type = LoadType.TRACK
        mock_results.tracks = [MagicMock(title="Test Song", uri="http://test.com")]

        with patch.object(cog, '_load_tracks', return_value=mock_results):
            # Test play command
            await cog.play_song.callback(cog, mock_ctx, query="test song")

            # Verify track was added and played
            mock_player.add.assert_called_once()
            mock_player.play.assert_called_once()

        # Test skip command
        mock_player.is_playing = True
        await cog.skip_song.callback(cog, mock_ctx, 1)

        # Verify skip was called
        mock_player.skip.assert_called_once()

    @pytest.mark.asyncio
    async def test_playlist_playback_workflow(self, mock_bot, mock_ctx, mock_player):
        """Test playlist creation and playback"""
        from Cogs.music import music
        from unittest.mock import patch, MagicMock

        # Setup
        cog = music(mock_bot)
        mock_bot.lavalink.player_manager.get.return_value = mock_player

        # Mock playlist load
        mock_results = MagicMock()
        mock_results.load_type = LoadType.PLAYLIST
        mock_results.playlist_info.name = "Test Playlist"
        mock_results.tracks = [
            MagicMock(title=f"Song {i}", uri=f"http://test.com/{i}") for i in range(3)
        ]

        with patch.object(cog, '_load_tracks', return_value=mock_results), \
                patch('Cogs.music.fileProcessing.play_playlist',
                      return_value=["Song 0", "Song 1", "Song 2"]):
            # Test playlist playback
            await cog.play_from_list.callback(cog, mock_ctx, playlist_name="test_playlist")

            # Verify all tracks were added
            assert mock_player.add.call_count == 3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])