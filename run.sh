#!/bin/bash
set -euo pipefail

# Where persistent data (playlists, song logs, Lavalink plugins) lives:
#   MUSICBOT_DATA_DIR set   -> bind-mount subdirs of that path, e.g. a mounted
#                              DigitalOcean Block Storage volume. Create and
#                              chown those dirs first with deploy/setup-volume.sh
#                              (they must be owned by the container user, uid 999).
#   MUSICBOT_DATA_DIR unset -> Docker named volumes (default). These persist
#                              across deploys but live on the droplet's boot disk.
if [[ -n "${MUSICBOT_DATA_DIR:-}" ]]; then
    PLUGINS_MOUNT="${MUSICBOT_DATA_DIR}/plugins"
    PLAYLIST_MOUNT="${MUSICBOT_DATA_DIR}/Playlist"
    SONGLOG_MOUNT="${MUSICBOT_DATA_DIR}/SongLog"
else
    PLUGINS_MOUNT="musicbot-plugins"
    PLAYLIST_MOUNT="musicbot-playlists"
    SONGLOG_MOUNT="musicbot-songlogs"
fi

docker run -d \
  --name musicbot \
  --restart unless-stopped \
  --memory=1g \
  --cpus=1 \
  --pids-limit=200 \
  --log-driver=json-file \
  --log-opt max-size=10m \
  --log-opt max-file=3 \
  --cap-drop=ALL \
  --security-opt no-new-privileges \
  --read-only \
  --tmpfs /tmp \
  --tmpfs /MusicBot/logs:uid=999,gid=999,size=48m \
  -v "${PLUGINS_MOUNT}:/MusicBot/plugins" \
  -v "${PLAYLIST_MOUNT}:/MusicBot/Playlist" \
  -v "${SONGLOG_MOUNT}:/MusicBot/SongLog" \
  --env-file .env \
  discord-music-bot:latest
