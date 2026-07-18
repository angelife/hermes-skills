# Dynamic Partition Diagnosis

Android 14+ (LineageOS 22+) on older devices often uses **dynamic partitions** managed by `lpdump`, even when the kernel is still 4.9. The "system" partition symlink points to a raw block device, but the actual filesystem lives on a device-mapper target (`/dev/block/dm-*`).

## Symptoms of TWRP / recovery partition mismatch

In TWRP recovery shell:

```
$ mount -t ext4 /dev/block/sda21 /mnt/system
mount: '/dev/block/sda21'->'/mnt/system': Invalid argument

$ blkid /dev/block/sda21
(no output — filesystem not recognized)
```

In the running Android system:

```
$ mount | grep " / "
/dev/block/dm-0 on / type ext4 (ro,seclabel,relatime,discard)
/dev/block/dm-4 on /system_ext type ext4 (ro,seclabel,relatime,discard)
```

No `/dev/block/sda21` appears in `mount` — that raw partition is a container (super partition), not a mountable filesystem.

## MindTheGapps installer error output

```
umount: /system: Invalid argument
umount: /mnt/system: No such file or directory
mount: /dev/block/bootdevice/by-name/system: need -t
Could not mount /mnt/system! Aborting
Updater process ended with ERROR: 1
```

## Root cause: `get_block_for_mount_point()` in update-binary

MindTheGapps installer script (`META-INF/com/google/android/update-binary`) contains a function that tries to find the system block device by looking for `/system` in fstab entries. On legacy layouts, this resolves to `/dev/block/bootdevice/by-name/system`. On dynamic partition layouts (Android 15), this symlink exists but the actual filesystem is on a device-mapper target (`dm-*`), so `mount` fails with `need -t` or `Invalid argument`.

## Fix: Patch the installer script

### Step 1: Extract the zip

```bash
mkdir -p /tmp/gapps-fix/extracted
cd /tmp/gapps-fix
unzip /tmp/mindthegapps.zip -d extracted/
```

### Step 2: Locate the `get_block_for_mount_point()` function

```bash
cd extracted
# Find the function in update-binary (it's a shell script)
grep -n "get_block_for_mount_point" META-INF/com/google/android/update-binary
```

### Step 3: Replace the function body

Edit `META-INF/com/google/android/update-binary`. Find the function definition:

```bash
get_block_for_mount_point() {
    # legacy approach that fails on dynamic partitions
    ...
}
```

Replace the entire function body with:

```bash
get_block_for_mount_point() {
    # Read the recovery's actual fstab to find the correct block device
    cat /etc/recovery.fstab | cut -d '#' -f 1 | grep /system | grep -o '/dev/[^ ]*' | head -1
}
```

This reads `/etc/recovery.fstab` from **the running recovery environment** (not the device's system fstab), which knows the correct dm-* device for the current dynamic partition layout.

### Step 4: Re-zip with store mode

```bash
cd /tmp/gapps-fix/extracted
# -0 = store (no compression). Android recovery needs this for update-binary
zip -r -0 /tmp/mindthegapps-fixed.zip .
```

### Step 5: Sideload the fixed zip

```bash
adb sideload /tmp/mindthegapps-fixed.zip
```

## Alternative: Pre-modded packages

The GitHub repo `samsungexynos7420/MindTheGapps_Legacy` provides pre-modded MindTheGapps packages with this fix applied for Android 14+. However:
- Only available up to Android 14 (not 15 as of mid-2026)
- ARM64 only
- Primarily tested on Exynos devices

## What works

| Method | Works on dynamic partitions? | Notes |
|--------|------------------------------|-------|
| Flashable zip via stock LineageOS recovery | ✅ (if signature bypassed) | LineageOS recovery knows dm-* targets — **preferred method** |
| Flashable zip via TWRP | ❌ | Old TWRP doesn't know dynamic layout |
| ADB sideload via TWRP | ❌ | The installer script fails, not the sideload protocol |
| Magisk module | ✅ | Overlay works regardless of partition layout |
| Manual `adb push` to system | ❌ | /system is ro even with root; overlay may help |

## Device-specific

### Mi8 (dipper) — LineageOS 22 (A15), kernel 4.9
- `system` block-by-name → `/dev/block/sda21`
- Actual mount → `/dev/block/dm-0` (ext4)
- `system_ext` → `/dev/block/dm-4` (ext4)
- TWRP 3.7.0_9-0 (2022): does NOT mount dynamic partitions
- No super partition by-name; dynamic layout managed in lpmake metadata
- /data is ext4 on sda22; encrypted with FBE (file-based encryption)

### Quick check: Is your TWRP new enough?

```bash
# In TWRP shell — if erofs is missing, TWRP predates Android 14
adb shell "cat /proc/filesystems | grep erofs"

# Check available dynamic-partition tools
adb shell "which lpdump lpflash 2>/dev/null || echo 'no lpdump'"
```
