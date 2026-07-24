#!/usr/bin/env bash
#
# DigitalOcean Droplet Bootstrap
#
# - Installs Git, Curl, Docker
# - Creates an unprivileged deploy user
# - Adds deploy user to the docker group
# - Installs an SSH key so you (and GitHub Actions) can log in as deploy
# - Clones (or updates) the Discord Music Bot repository
#
# Safe to run multiple times.
#
# Run as root:   bash setup-droplet.sh
# Custom fork:   REPO_URL=git@github.com:you/Discord_Music_Bot.git bash setup-droplet.sh
# Specific key:  AUTHORIZED_KEY="ssh-ed25519 AAAA... you@host" bash setup-droplet.sh
#

set -euo pipefail

# ---------- Configuration ----------
REPO_URL="${REPO_URL:-https://github.com/RobertAndion/Discord_Music_Bot.git}"
DEPLOY_USER="${DEPLOY_USER:-deploy}"
DEPLOY_PATH="${DEPLOY_PATH:-/opt/musicbot}"
DEPLOY_BRANCH="${DEPLOY_BRANCH:-master}"
# Public key to grant SSH access to the deploy user. If empty, we fall back to
# copying root's authorized_keys (COPY_ROOT_KEYS) so you can log in as deploy
# with the same key you already use for root.
AUTHORIZED_KEY="${AUTHORIZED_KEY:-}"
COPY_ROOT_KEYS="${COPY_ROOT_KEYS:-true}"

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

echo "==> Configuring SSH access for '$DEPLOY_USER'..."
# The deploy user is created with --disabled-password, so it has NO way to log
# in until a public key is installed here. This is the same key GitHub Actions
# uses (its public half must live in this authorized_keys file).
DEPLOY_HOME="$(getent passwd "$DEPLOY_USER" | cut -d: -f6)"
SSH_DIR="$DEPLOY_HOME/.ssh"
AUTH_KEYS="$SSH_DIR/authorized_keys"
install -d -m 700 -o "$DEPLOY_USER" -g "$DEPLOY_USER" "$SSH_DIR"
touch "$AUTH_KEYS"

add_key() {
    local key="$1"
    # Skip blanks/comments; append only if not already present (idempotent).
    if [[ -n "$key" && "$key" != \#* ]] && ! grep -qxF "$key" "$AUTH_KEYS" 2>/dev/null; then
        echo "$key" >> "$AUTH_KEYS"
    fi
}

if [[ -n "$AUTHORIZED_KEY" ]]; then
    add_key "$AUTHORIZED_KEY"
    echo "    Installed the provided AUTHORIZED_KEY."
elif [[ "$COPY_ROOT_KEYS" == "true" && -s /root/.ssh/authorized_keys ]]; then
    while IFS= read -r line; do
        add_key "$line"
    done < /root/.ssh/authorized_keys
    echo "    Copied root's authorized_keys — log in with: ssh $DEPLOY_USER@<droplet-ip>"
else
    echo "    WARNING: no SSH key installed for '$DEPLOY_USER' (login will fail)."
    echo "    Add one, e.g.:  echo 'ssh-ed25519 AAAA...' >> $AUTH_KEYS"
fi

chown -R "$DEPLOY_USER:$DEPLOY_USER" "$SSH_DIR"
chmod 700 "$SSH_DIR"
chmod 600 "$AUTH_KEYS"

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
echo "  • Verify login:  ssh $DEPLOY_USER@<droplet-ip>"
echo "  • Add GitHub Actions secrets (DROPLET_HOST, DROPLET_USER, SSH_PRIVATE_KEY,"
echo "    DISCORD_TOKEN, ...) — see deploy/README.md. The SSH_PRIVATE_KEY must match"
echo "    a public key in $AUTH_KEYS."
echo "  • Trigger a test run from the Actions tab, then push to '$DEPLOY_BRANCH'."
echo
echo "Note: '$DEPLOY_USER' was added to the docker group. Reconnect its session"
echo "(or run 'newgrp docker') before running docker commands manually. This does"
echo "not affect the GitHub Actions deploy, which opens a fresh session each time."
echo "=========================================="
