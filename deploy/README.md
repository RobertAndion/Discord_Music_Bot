# Automated Deployment: GitHub Actions → your server

This guide sets up continuous deployment for your **own fork** of the bot. Every
push to `master` (or a manual run from the **Actions** tab) SSHes into your
server, syncs the code, rebuilds the Docker image, and restarts the bot. Secrets
(`DISCORD_TOKEN`, Lavalink password) live in **GitHub Actions secrets** and are
written to `.env` on the server at deploy time — they are never committed.

It works on **any SSH-accessible Linux server** — a DigitalOcean droplet (used as
the example below), any VPS, or a home server. All you need is Docker and SSH.

```
push to master ──► GitHub Actions ──ssh──► server
                                            ├─ git reset --hard origin/master
                                            ├─ deploy/deploy.sh
                                            │   ├─ write .env from secrets
                                            │   ├─ docker build -f Docker/Dockerfile
                                            │   └─ run.sh (stop old → start new)
```

`Lavalink.jar` is **downloaded during the Docker build** (see `Docker/Dockerfile`,
`ARG LAVALINK_VERSION`), so it does not need to exist on the droplet or in git.

---

## 1. One-time droplet setup

Create an Ubuntu 22.04/24.04 droplet, then SSH in as root and run:

```bash
# --- Install Docker ---
curl -fsSL https://get.docker.com | sh

# --- Create an unprivileged deploy user with Docker access ---
adduser --disabled-password --gecos "" deploy
usermod -aG docker deploy

# --- Prepare the app directory ---
mkdir -p /opt/musicbot
chown deploy:deploy /opt/musicbot
```

Clone the repo as the `deploy` user (public repo shown; for a **private** repo,
add a read-only [deploy key](https://docs.github.com/en/authentication/connecting-to-github-with-ssh/managing-deploy-keys)
to the droplet first and use the SSH clone URL):

```bash
su - deploy
git clone https://github.com/<you>/Discord_Music_Bot.git /opt/musicbot
cd /opt/musicbot && git checkout master
```

## 2. SSH key for GitHub Actions

Generate a dedicated keypair (run locally or on the droplet). **Do not** reuse a
personal key.

```bash
ssh-keygen -t ed25519 -C "github-actions-musicbot" -f gha_deploy -N ""
```

- Append `gha_deploy.pub` to the droplet's `deploy` user:
  ```bash
  # as deploy on the droplet
  mkdir -p ~/.ssh && chmod 700 ~/.ssh
  echo "<contents of gha_deploy.pub>" >> ~/.ssh/authorized_keys
  chmod 600 ~/.ssh/authorized_keys
  ```
- The **private** key `gha_deploy` becomes the `SSH_PRIVATE_KEY` secret below.

## 3. GitHub Actions secrets

Repo → **Settings → Secrets and variables → Actions → New repository secret**:

| Secret | Required | Example / notes |
| --- | --- | --- |
| `DROPLET_HOST` | ✅ | Droplet public IP, e.g. `203.0.113.10` |
| `DROPLET_USER` | ✅ | `deploy` |
| `SSH_PRIVATE_KEY` | ✅ | Full contents of the `gha_deploy` private key |
| `DISCORD_TOKEN` | ✅ | Your Discord bot token |
| `LAVALINK_PASSWORD` | ⬜ | Any string; defaults to `changeme123` if omitted |
| `DEPLOY_PATH` | ⬜ | Defaults to `/opt/musicbot` |
| `DROPLET_SSH_PORT` | ⬜ | Defaults to `22` |

## 4. Deploy

- **Automatic:** merge/push to `master`.
- **Manual:** Actions tab → *Deploy to DigitalOcean* → **Run workflow**.

Watch the run's logs in the Actions tab; the final step prints the container
status. On the droplet you can check with:

```bash
docker ps --filter name=musicbot
docker logs -f musicbot
```

---

## Notes & troubleshooting

- **First deploy is slow** — the image build compiles deps and Lavalink downloads
  its YouTube plugin on first boot (`startup.sh` waits up to 90s for it).
- **Rotating a secret** — update it in GitHub, then re-run the workflow; `.env` is
  rewritten every deploy.
- **Bumping Lavalink** — change `ARG LAVALINK_VERSION` in `Docker/Dockerfile`.
- **Deploying a different branch** — edit `DEPLOY_BRANCH` and the `on.push.branches`
  list in `.github/workflows/deploy.yml`.
- The workflow's `git reset --hard` discards any uncommitted changes on the droplet
  (except `.env`, preserved via `git clean -e`). Treat the droplet checkout as
  disposable — the git repo is the source of truth.
