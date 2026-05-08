#!/bin/bash
set -e

java -jar Lavalink.jar &

# Wait up to 90s for Lavalink (first run downloads the YouTube plugin)
echo "Waiting for Lavalink on port 2333..."
for i in $(seq 1 45); do
    if python3 -c "import socket; s=socket.socket(); s.settimeout(1); s.connect(('localhost',2333)); s.close()" 2>/dev/null; then
        echo "Lavalink ready."
        break
    fi
    if [ "$i" -eq 45 ]; then
        echo "Lavalink did not start in time, exiting."
        exit 1
    fi
    sleep 2
done

exec python3 bot.py
