#!/usr/bin/env bash
#
# Runs ON the droplet. Invoked by the GitHub Actions deploy workflow after the
# repo has been synced to the target commit. Writes .env from environment
# variables (populated from GitHub secrets), builds the image, and restarts the
# container via run.sh.
#
# Required env: DISCORD_TOKEN
# Optional env: LAVALINK_PASSWORD (defaults to changeme123)
#
set -euo pipefail

# Always operate from the repo root (this script lives in deploy/).
cd "$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [[ -z "${DISCORD_TOKEN:-}" ]]; then
    echo "ERROR: DISCORD_TOKEN is not set." >&2
    exit 1
fi

echo "==> Writing .env"
umask 077
cat > .env <<EOF
DISCORD_TOKEN=${DISCORD_TOKEN}
LAVALINK_PASSWORD=${LAVALINK_PASSWORD:-changeme123}
EOF

echo "==> Building image (musicbot)"
docker build -f Docker/Dockerfile -t musicbot .

echo "==> Restarting container"
docker stop musicbot 2>/dev/null || true
docker rm musicbot 2>/dev/null || true
./run.sh

echo "==> Pruning dangling images"
docker image prune -f >/dev/null 2>&1 || true

echo "==> Deploy complete"
docker ps --filter "name=musicbot" --format "table {{.Names}}\t{{.Status}}"
