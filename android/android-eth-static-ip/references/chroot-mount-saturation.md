# chroot Mount Saturation Notes

## Symptom
- `mount --rbind /dev /data/.../chroot/.../dev` returns `No space left on device`
- `df -h /data` shows free space
- `df -i /data` shows plenty of inodes
- `grep -c chroot/... /proc/mounts` shows tens of thousands of entries

## Root Cause
- `/proc/1/mountinfo` lines for the chroot tree show `shared:NN` propagation
- Peer mount namespaces recursively copy every mount
- One `mount --rbind /dev` alone can multiply into tens of recursive child mounts
- Repeated mount attempts from debugging or unguarded scripts quickly saturate kernel mount resources

## Verification
- `grep "shared:" /proc/1/mountinfo | sort -u | head` to spot shared domains
- `grep -c chroot/... /proc/mounts` before/after each mount action
- If count climbs without explicit new mounts, propagation is active

## Observed Evidence (Mi8 / dipper)
- `grep -c chroot/debian /proc/mounts` returned **34802**
- `/proc/self/mountinfo` lines for `/data/local/tmp/chroot/debian` show:
  - `shared:39` on the bind mount
  - `shared:56` on proc
  - `shared:57` on sysfs
  - `shared:2` on dev tmpfs
- After reboot, same paths reused **without** `shared:N` only when `make-rprivate` is applied in `post-fs-data.d`
- `/sys/bus/usb/devices` empty and `dmesg`/`logcat` show no usb/ethernet/adbd errors when USB-C Ethernet adapter is attached: on Mi8/MIUI this adapter is **not enumerated at all**, not just displacing ADB

## Pitfalls
- `mount --make-private` on Android may require an `/etc/fstab`; or fail with "bad /etc/fstab" and return success while doing nothing.
- `unshare --mount` is available on Mi8, but executing `chroot` inside `unshare` requires careful quoting; a helper init script pushed to device is more reliable than shell heredocs.
- `umount -R` does not clear mounts held by other mount namespaces during active propagation; repeated looping is misleading.
- Isolating to a new directory works only if the new mount point is not itself inside a replicated shared subtree.

## Recommended Mount Sequence After Reboot
```bash
MOUNT=/data/local/tmp/chroot2/debian
mount_once /data/local/tmp/debian/debian-rootfs "$MOUNT"
mount --make-rprivate "$MOUNT" 2>/dev/null || true
mount_once proc "$MOUNT/proc" proc
mount_once sysfs "$MOUNT/sys" sysfs
mountpoint -q "$MOUNT/dev" || mount --rbind /dev "$MOUNT/dev"
mount --make-rprivate "$MOUNT/dev" 2>/dev/null || true
```

## Alist Credentials Note
- Initial admin password is printed by `alist admin` / first-time `alist server --force-bin-dir` initialization
- Unless initialized, accessing the web UI returns 503 because the default config does not exist yet
- No retroactive password view after initialization

## chroot Profile Noise
- Debian `/etc/profile` may call `id -u` which is not available in minimal chroots
- This pollutes shell output with `/etc/profile: line 4: id: command not found` and `integer expression expected`
- Remove the bare `id` line from `/etc/profile` to restore clean shell behavior
