#!/usr/bin/env bash
#
# Prepare an attached DigitalOcean Block Storage volume to hold the bot's
# persistent data (playlists, song logs, Lavalink plugins), so it survives
# deploys AND droplet rebuilds, and can be snapshotted / moved.
#
# Run ONCE as root, AFTER attaching the volume in the DO control panel:
#   DEVICE=/dev/disk/by-id/scsi-0DO_Volume_<name> bash setup-volume.sh
#
# Find the device path with:  ls -l /dev/disk/by-id/ | grep -i DO_Volume
#
# Safe to re-run: it never formats a device that already has a filesystem.
#
set -euo pipefail

DEVICE="${DEVICE:-}"
MOUNT_POINT="${MOUNT_POINT:-/mnt/musicbot-data}"
CONTAINER_UID="${CONTAINER_UID:-999}"   # matches the Dockerfile's basicuser
CONTAINER_GID="${CONTAINER_GID:-999}"

if [[ "$EUID" -ne 0 ]]; then
    echo "ERROR: run as root." >&2
    exit 1
fi
if [[ -z "$DEVICE" ]]; then
    echo "ERROR: set DEVICE=... (find it: ls -l /dev/disk/by-id/ | grep -i DO_Volume)" >&2
    exit 1
fi
if [[ ! -b "$DEVICE" ]]; then
    echo "ERROR: $DEVICE is not a block device. Is the volume attached?" >&2
    exit 1
fi

# Only format a blank device — never wipe an existing filesystem.
FS_TYPE="$(blkid -o value -s TYPE "$DEVICE" 2>/dev/null || true)"
if [[ -z "$FS_TYPE" ]]; then
    echo "==> $DEVICE has no filesystem; creating ext4."
    mkfs.ext4 -F "$DEVICE"
else
    echo "==> $DEVICE already has a '$FS_TYPE' filesystem; keeping it (no format)."
fi

echo "==> Mounting at $MOUNT_POINT"
mkdir -p "$MOUNT_POINT"
# Persist by UUID (survives device-name changes); nofail so a detached volume
# can't block boot; discard enables TRIM on the SSD-backed volume.
UUID="$(blkid -o value -s UUID "$DEVICE")"
if ! grep -q "$UUID" /etc/fstab; then
    echo "UUID=$UUID $MOUNT_POINT ext4 defaults,nofail,discard 0 2" >> /etc/fstab
fi
mountpoint -q "$MOUNT_POINT" || mount "$MOUNT_POINT"

echo "==> Creating data directories owned by the container user ($CONTAINER_UID:$CONTAINER_GID)"
mkdir -p "$MOUNT_POINT/Playlist" "$MOUNT_POINT/SongLog" "$MOUNT_POINT/plugins"
chown -R "$CONTAINER_UID:$CONTAINER_GID" "$MOUNT_POINT"

echo
echo "=========================================="
echo "Volume ready at: $MOUNT_POINT"
echo
echo "To migrate playlists already stored in a Docker named volume:"
echo "  docker run --rm -v musicbot-playlists:/src -v $MOUNT_POINT/Playlist:/dst \\"
echo "    alpine sh -c 'cp -a /src/. /dst/ && chown -R $CONTAINER_UID:$CONTAINER_GID /dst'"
echo
echo "Then tell deploys to use it by setting the GitHub Actions secret:"
echo "  MUSICBOT_DATA_DIR = $MOUNT_POINT"
echo "(or 'export MUSICBOT_DATA_DIR=$MOUNT_POINT' before running ./run.sh manually)"
echo "=========================================="
