# Automated Deployment: GitHub Actions → your server

Continuous deployment for your **own fork** of the bot. Every push to `master`
(or a manual run from the **Actions** tab) SSHes into your server, syncs the
code, rebuilds the Docker image, and restarts the bot. Secrets (`DISCORD_TOKEN`,
Lavalink password) live in **GitHub Actions secrets** and are written to `.env`
on the server at deploy time — they are never committed.

It works on **any SSH-accessible Linux server** — a DigitalOcean droplet (used
as the example throughout), any VPS, or a home server. All you need is Docker
and SSH.

```
push to master ──► GitHub Actions ──native ssh (live logs)──► server
                                                               ├─ git reset --hard origin/master
                                                               └─ deploy/deploy.sh
                                                                   ├─ write .env from secrets
                                                                   ├─ docker build  (discord-music-bot:<sha> + :latest)
                                                                   ├─ run.sh        (stop old → start new)
                                                                   └─ prune old images
```

`Lavalink.jar` is **downloaded during the Docker build** (`Docker/Dockerfile`,
`ARG LAVALINK_VERSION`), so it never has to exist on the server or in git.

## Contents

1. [Prerequisites](#prerequisites)
2. [Step 1 — Provision & bootstrap the server](#step-1--provision--bootstrap-the-server)
3. [Step 2 — SSH key for GitHub Actions](#step-2--ssh-key-for-github-actions)
4. [Step 3 — GitHub Actions secrets](#step-3--github-actions-secrets)
5. [Step 4 — Deploy](#step-4--deploy)
6. [Persistent playlists with Block Storage](#persistent-playlists-with-block-storage)
7. [Day-to-day operations](#day-to-day-operations)
8. [Troubleshooting](#troubleshooting)
9. [Files in this folder](#files-in-this-folder)

---

## Prerequisites

- A server you can SSH into as `root` (e.g. an Ubuntu 22.04/24.04 DigitalOcean droplet).
  A 1 GB droplet works; the bootstrap adds swap so the build won't get OOM-killed.
- A Discord bot token — [Discord Developer Portal](https://discord.com/developers/applications).
- A GitHub repo (your fork) where the Actions workflow and secrets live.

---

## Step 1 — Provision & bootstrap the server

`deploy/setup-droplet.sh` does the entire one-time setup and is **safe to re-run**
(every step is idempotent). It:

- waits for cloud-init/apt to settle, then installs `git`, `curl`, Docker;
- **creates a 2 GB swapfile** (persisted in `/etc/fstab`) so memory-hungry builds
  aren't OOM-killed on small droplets;
- creates an unprivileged **`deploy`** user in the `docker` group;
- installs an SSH key for `deploy` (see [Step 2](#step-2--ssh-key-for-github-actions));
- clones the repo to `/opt/musicbot`.

On a **fresh droplet**, download and run it as root:

```bash
curl -fsSL https://raw.githubusercontent.com/RobertAndion/Discord_Music_Bot/master/deploy/setup-droplet.sh -o setup-droplet.sh
sudo bash setup-droplet.sh
```

Configurable via env vars (all optional):

| Var | Default | Purpose |
| --- | --- | --- |
| `REPO_URL` | this repo | Point at your fork (use the SSH URL for a private repo) |
| `DEPLOY_USER` | `deploy` | Service account name |
| `DEPLOY_PATH` | `/opt/musicbot` | Where the repo is cloned |
| `AUTHORIZED_KEY` | — | Public key to grant the `deploy` user (see Step 2) |
| `COPY_ROOT_KEYS` | `true` | If no `AUTHORIZED_KEY`, reuse root's `authorized_keys` |
| `SWAP_SIZE` | `2G` | Swapfile size; `0` to skip |

Example for a private fork with a dedicated CI key:

```bash
REPO_URL=git@github.com:you/Discord_Music_Bot.git \
AUTHORIZED_KEY="$(cat gha_deploy.pub)" \
sudo -E bash setup-droplet.sh
```

> **Private repo?** The `deploy` user needs read access. Add a read-only
> [deploy key](https://docs.github.com/en/authentication/connecting-to-github-with-ssh/managing-deploy-keys)
> to the droplet and set `REPO_URL` to the `git@github.com:...` SSH URL.

---

## Step 2 — SSH key for GitHub Actions

GitHub Actions logs into the server **as the `deploy` user**, so the public key
matching your `SSH_PRIVATE_KEY` secret must be in `deploy`'s `authorized_keys`.

Generate a **dedicated** keypair (never reuse a personal key):

```bash
ssh-keygen -t ed25519 -C "github-actions-musicbot" -f gha_deploy -N ""
```

- **Public** half (`gha_deploy.pub`) → give it to the `deploy` user. Easiest is to
  pass it to the bootstrap: `AUTHORIZED_KEY="$(cat gha_deploy.pub)"`. Or append by hand:
  ```bash
  # as deploy on the server
  install -d -m 700 ~/.ssh
  echo "ssh-ed25519 AAAA... github-actions-musicbot" >> ~/.ssh/authorized_keys
  chmod 600 ~/.ssh/authorized_keys
  ```
- **Private** half (`gha_deploy`) → the `SSH_PRIVATE_KEY` secret in [Step 3](#step-3--github-actions-secrets).

Test it: `ssh -i gha_deploy deploy@<server-ip>` should log in without a password.

> The bootstrap also copies **root's** existing `authorized_keys` to `deploy`
> (unless you pass `AUTHORIZED_KEY`), so you can log in as `deploy` with the same
> key you already use for root. That's for *your* convenience — GitHub Actions
> still needs its own dedicated key as above.

---

## Step 3 — GitHub Actions secrets

Repo → **Settings → Secrets and variables → Actions → New repository secret**:

| Secret | Required | Example / notes |
| --- | --- | --- |
| `DROPLET_HOST` | ✅ | Server public IP, e.g. `203.0.113.10` |
| `DROPLET_USER` | ✅ | `deploy` |
| `SSH_PRIVATE_KEY` | ✅ | Full contents of the `gha_deploy` private key |
| `DISCORD_TOKEN` | ✅ | Your Discord bot token |
| `LAVALINK_PASSWORD` | ⬜ | Any string; defaults to `changeme123` if omitted |
| `DEPLOY_PATH` | ⬜ | Defaults to `/opt/musicbot` |
| `DROPLET_SSH_PORT` | ⬜ | Defaults to `22` |
| `MUSICBOT_DATA_DIR` | ⬜ | Mount point of a block-storage volume for playlists (see below). Empty = Docker named volumes. |

---

## Step 4 — Deploy

- **Automatic:** merge/push to `master`.
- **Manual:** Actions tab → *Deploy to DigitalOcean* → **Run workflow**.

The deploy step uses **native `ssh`**, so the remote output — `git` sync,
`docker build` (with `--progress=plain`), container restart — **streams live**
into the Actions log as it happens. On the server you can also watch:

```bash
docker ps --filter name=musicbot
docker logs -f musicbot
```

Each build is tagged `discord-music-bot:<git-sha>` and `:latest`; after a
successful deploy, older image tags are pruned automatically so the disk stays clean.

---

## Persistent playlists with Block Storage

By default, playlists / song-logs / Lavalink plugins live in **Docker named
volumes**. They survive deploys, but they sit on the droplet's **boot disk** — so
they're lost if the droplet is destroyed or rebuilt. A **DigitalOcean Block
Storage volume** puts this data on a separate, durable disk you can snapshot,
resize, and re-attach to a new droplet.

This is **opt-in**: nothing changes until you set `MUSICBOT_DATA_DIR`.

### 1. Create & attach the volume

In the DO control panel: **Volumes → Create**, attach it to your droplet.
Playlists are tiny — 1 GB is plenty.

### 2. Prepare it (once, as root)

Find the device, then run the helper. It formats a **blank** volume only (never
one that already has a filesystem), mounts it at `/mnt/musicbot-data` via
`/etc/fstab`, and creates the data dirs owned by the container user (**uid 999**):

```bash
ls -l /dev/disk/by-id/ | grep -i DO_Volume
#   -> scsi-0DO_Volume_<name> -> ../../sda

DEVICE=/dev/disk/by-id/scsi-0DO_Volume_<name> bash /opt/musicbot/deploy/setup-volume.sh
```

Prefer a different mount path? Pass `MOUNT_POINT=/mnt/yourname` — just make sure
the `MUSICBOT_DATA_DIR` secret matches whatever you use.

### 3. Confirm it's mounted and will stay mounted

The `/etc/fstab` entry (added by the helper) is what remounts the volume on every
boot. Verify **without rebooting** — this exercises fstab exactly like boot does:

```bash
umount /mnt/musicbot-data && mount -a      # no error = fstab is valid
findmnt /mnt/musicbot-data                 # shows the volume on /dev/sdX
ls -ln /mnt/musicbot-data                  # Playlist/SongLog/plugins owned by 999 999
```

The entry uses `UUID=` (survives device-name changes) and `nofail` (a detached
volume won't block boot).

### 4. Migrate existing playlists (only if you already had some)

If the bot already ran with named volumes, copy that data onto the volume
**before** switching:

```bash
docker run --rm -v musicbot-playlists:/src -v /mnt/musicbot-data/Playlist:/dst \
  alpine sh -c 'cp -a /src/. /dst/ && chown -R 999:999 /dst'
```

### 5. Switch deploys onto the volume

Set the secret `MUSICBOT_DATA_DIR = /mnt/musicbot-data`, then redeploy. `run.sh`
now bind-mounts `<dir>/{Playlist,SongLog,plugins}` instead of the named volumes.
Confirm the running container is using it:

```bash
docker inspect musicbot --format '{{range .Mounts}}{{.Source}} -> {{.Destination}}{{"\n"}}{{end}}'
# expect: /mnt/musicbot-data/Playlist -> /MusicBot/Playlist  (+ SongLog, plugins)
```

To roll back, remove the `MUSICBOT_DATA_DIR` secret and redeploy.

> ⚠️ **Mount-before-Docker matters.** The bot bind-mounts `/mnt/musicbot-data`. If
> that path is ever *not* mounted (volume detached, bad fstab), Docker silently
> bind-mounts the empty directory on the boot disk instead — the container starts
> fine but writes to the wrong place, so playlists look "gone." `UUID` + `nofail`
> + the `mount -a` check in step 3 are what prevent this.

---

## Day-to-day operations

```bash
# Logs / status
docker logs -f musicbot
docker ps --filter name=musicbot

# Restart / stop / start
docker restart musicbot
docker stop musicbot && docker start musicbot
```

- **Rotate a secret** — update it in GitHub, then re-run the workflow; `.env` is
  rewritten from secrets on every deploy.
- **Bump Lavalink** — change `ARG LAVALINK_VERSION` in `Docker/Dockerfile` and push.
- **Change the Lavalink password** — set `LAVALINK_PASSWORD` (both the server via
  `application.yml` and the bot via `Cogs/music.py` read it from that variable).
- **Deploy a different branch** — edit `DEPLOY_BRANCH` and the `on.push.branches`
  list in `.github/workflows/deploy.yml`.
- **Back up playlists from Discord** — `.backupPlaylists` DMs the owner a zip.

The workflow's `git reset --hard` discards any uncommitted changes on the server
(except `.env`, preserved via `git clean -e`). Treat the server checkout as
disposable — **git is the source of truth**, playlists live in the volume.

---

## Troubleshooting

**Deploy step ends with `Process exited with status 255` mid-`docker build`.**
The SSH session was killed, not a build error — almost always the **OOM killer**
on a swap-less droplet during the parallel build. Fix: ensure swap exists
(`free -h`, `swapon --show`). Re-run `setup-droplet.sh` (it adds 2 GB), or:
```bash
sudo fallocate -l 2G /swapfile && sudo chmod 600 /swapfile
sudo mkswap /swapfile && sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

**Build fails: `openjdk-21-jre-headless has no installation candidate`.**
The base image must be Debian 13 (`python:3.13-slim-trixie`) — Debian 12
(bookworm) doesn't package OpenJDK 21. This repo already uses trixie; if you
changed it, change it back.

**Build fails: `no space left on device`.**
Failed builds leave image/layer cruft (cleanup only runs after a *successful*
build). Check `df -h /` and clear it: `docker system prune -af`.

**Logs only appear at the end, not live.**
You're on a `master` whose workflow still uses `appleboy/ssh-action` (it buffers
output). The current workflow uses native `ssh` and streams; make sure `master`
has it.

**Can't `ssh deploy@server` ("Permission denied (publickey)").**
The `deploy` user is `--disabled-password`, so it needs a key in
`~deploy/.ssh/authorized_keys`. See [Step 2](#step-2--ssh-key-for-github-actions).
Perms must be `700` on `~/.ssh` and `600` on `authorized_keys`.

**Playlists "disappear" after enabling block storage.**
The volume probably isn't mounted at deploy time — Docker bind-mounted the empty
boot-disk dir. Verify `findmnt /mnt/musicbot-data`, that `MUSICBOT_DATA_DIR`
matches the mount point, and that `docker inspect` shows the volume path (see
the block-storage section).

**First deploy is slow.** Normal — the image build compiles deps, and Lavalink
downloads its YouTube plugin on first boot (`startup.sh` waits up to 90s for it).

---

## Files in this folder

| File | Runs where | Purpose |
| --- | --- | --- |
| `setup-droplet.sh` | server, once, as root | Bootstrap: Docker, swap, `deploy` user, SSH key, clone |
| `setup-volume.sh` | server, once, as root | Prepare a block-storage volume for persistent playlists |
| `deploy.sh` | server, every deploy | Write `.env`, build image, restart container, prune old images |
| `README.md` | — | This guide |

Related: `.github/workflows/deploy.yml` (the workflow), `Docker/Dockerfile` (image
build + Lavalink download), `run.sh` (the `docker run` invocation + volume wiring).
