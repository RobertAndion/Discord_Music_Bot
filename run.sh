#!/bin/bash
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
  --tmpfs /MusicBot/logs:uid=999,gid=999 \
  -v musicbot-plugins:/MusicBot/plugins \
  -v musicbot-playlists:/MusicBot/Playlist \
  -v musicbot-songlogs:/MusicBot/SongLog \
  --env-file .env \
  musicbot