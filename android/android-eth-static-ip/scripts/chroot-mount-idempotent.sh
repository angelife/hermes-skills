#!/system/bin/sh
# Idempotent chroot mount script
# Usage: place in /data/adb/post-fs-data.d/ for Magisk early mount
mount_once() {
  mountpoint -q "$2" 2>/dev/null && return 0
  mount ${3:+-t $3} "$1" "$2"
}

mount_once /data/local/tmp/debian/debian-rootfs /data/local/tmp/chroot/debian
mount_once proc /data/local/tmp/chroot/debian/proc proc
mount_once sysfs /data/local/tmp/chroot/debian/sys sysfs
mountpoint -q /data/local/tmp/chroot/debian/dev || mount --rbind /dev /data/local/tmp/chroot/debian/dev
