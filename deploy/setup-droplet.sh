#!/usr/bin/env bash
#
# DigitalOcean Droplet Bootstrap
#
# - Installs Git, Curl, Docker
# - Creates an unprivileged deploy user
# - Adds deploy user to the docker group
# - Clones (or updates) the Discord Music Bot repository
#
# Safe to run multiple times.
#
# Run as root:   bash setup-droplet.sh
# Custom fork:   REPO_URL=git@github.com:you/Discord_Music_Bot.git bash setup-droplet.sh
#

set -euo pipefail

# ---------- Configuration ----------
REPO_URL="${REPO_URL:-https://github.com/RobertAndion/Discord_Music_Bot.git}"
DEPLOY_USER="${DEPLOY_USER:-deploy}"
DEPLOY_PATH="${DEPLOY_PATH:-/opt/musicbot}"
DEPLOY_BRANCH="${DEPLOY_BRANCH:-master}"

# ---------- Ensure we're root ----------
if [[ "$EUID" -ne 0 ]]; then
    echo "ERROR: This script must be run as root."
    exit 1
fi

echo "==> Waiting for cloud-init/apt to finish..."
while fuser /var/lib/dpkg/lock >/dev/null 2>&1 \
   || fuser /var/lib/dpkg/lock-frontend >/dev/null 2>&1 \
   || fuser /var/cache/apt/archives/lock >/dev/null 2>&1; do
    sleep 2
done

echo "==> Updating package lists..."
apt-get update

echo "==> Installing prerequisites..."
DEBIAN_FRONTEND=noninteractive apt-get install -y \
    git \
    curl \
    sudo \
    ca-certificates

echo "==> Installing Docker..."
if ! command -v docker >/dev/null 2>&1; then
    curl -fsSL https://get.docker.com | sh
else
    echo "    Docker already installed."
fi

echo "==> Enabling Docker service..."
systemctl enable docker
systemctl start docker

echo "==> Creating deploy user..."
if ! id -u "$DEPLOY_USER" >/dev/null 2>&1; then
    adduser \
        --disabled-password \
        --gecos "" \
        "$DEPLOY_USER"
else
    echo "    User already exists."
fi

usermod -aG docker "$DEPLOY_USER"

echo "==> Preparing application directory..."
mkdir -p "$DEPLOY_PATH"
chown "$DEPLOY_USER:$DEPLOY_USER" "$DEPLOY_PATH"

echo "==> Cloning/updating repository..."
# NOTE: for a PRIVATE repo, add a read-only deploy key to this server first
# and set REPO_URL to the SSH clone URL (git@github.com:you/repo.git).
if [[ -d "$DEPLOY_PATH/.git" ]]; then
    echo "    Repository already exists."

    runuser -u "$DEPLOY_USER" -- \
        git -C "$DEPLOY_PATH" fetch --all --prune

    runuser -u "$DEPLOY_USER" -- \
        git -C "$DEPLOY_PATH" checkout "$DEPLOY_BRANCH"

    runuser -u "$DEPLOY_USER" -- \
        git -C "$DEPLOY_PATH" reset --hard "origin/$DEPLOY_BRANCH"
else
    runuser -u "$DEPLOY_USER" -- \
        git clone "$REPO_URL" "$DEPLOY_PATH"

    runuser -u "$DEPLOY_USER" -- \
        git -C "$DEPLOY_PATH" checkout "$DEPLOY_BRANCH"
fi

echo
echo "=========================================="
echo "Bootstrap complete!"
echo
echo "Repository:"
echo "  $DEPLOY_PATH"
echo
echo "Deploy user:"
echo "  $DEPLOY_USER"
echo
echo "Docker version:"
docker --version
echo
echo "Next steps:"
echo "  • Configure GitHub Actions secrets (see deploy/README.md)."
echo "  • Push to '$DEPLOY_BRANCH' to deploy."
echo
echo "Note: '$DEPLOY_USER' was added to the docker group. Reconnect its session"
echo "(or run 'newgrp docker') before running docker commands manually. This does"
echo "not affect the GitHub Actions deploy, which opens a fresh session each time."
echo "=========================================="
