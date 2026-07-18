#!/system/bin/sh
set -e
MOUNT=/data/local/tmp/chroot3/debian
ROOTFS=/data/local/tmp/debian/debian-rootfs
mkdir -p "$MOUNT"
mount --bind "$ROOTFS" "$MOUNT"
mount -t proc proc "$MOUNT/proc"
mount -t sysfs sysfs "$MOUNT/sys"
mount --rbind /dev "$MOUNT/dev"
exec chroot "$MOUNT" /bin/bash
