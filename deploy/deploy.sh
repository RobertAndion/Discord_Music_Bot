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

# Repo-scoped image name; tag each build with the git SHA plus :latest.
IMAGE_NAME="discord-music-bot"
GIT_SHA="$(git rev-parse --short HEAD 2>/dev/null || echo latest)"

echo "==> Building image (${IMAGE_NAME}:${GIT_SHA})"
# --progress=plain gives line-oriented output that streams cleanly over SSH.
docker build -f Docker/Dockerfile --progress=plain \
    -t "${IMAGE_NAME}:${GIT_SHA}" \
    -t "${IMAGE_NAME}:latest" \
    .

echo "==> Restarting container"
docker stop musicbot 2>/dev/null || true
docker rm musicbot 2>/dev/null || true
./run.sh

echo "==> Cleaning up old ${IMAGE_NAME} images"
# Remove every tag of this image except the two we just built (:latest and the
# current SHA), so old builds don't pile up on the droplet.
docker images "${IMAGE_NAME}" --format '{{.Repository}}:{{.Tag}}' | while read -r ref; do
    case "$ref" in
        "${IMAGE_NAME}:latest"|"${IMAGE_NAME}:${GIT_SHA}") ;;   # keep current build
        *) echo "    removing ${ref}"; docker rmi -f "$ref" >/dev/null 2>&1 || true ;;
    esac
done
# Drop the pre-rename 'musicbot' image if it's lingering, plus any dangling layers.
docker rmi -f musicbot >/dev/null 2>&1 || true
docker image prune -f >/dev/null 2>&1 || true

echo "==> Deploy complete"
docker ps --filter "name=musicbot" --format "table {{.Names}}\t{{.Status}}\t{{.Image}}"
