# Magisk Root Workflow — Session Reproduction

Rooted a Xiaomi Mi 8 (dipper, LineageOS 14 userdebug, Android 14) via Magisk v30.7 boot-patch method. No TWRP required.

## Environment

| Item | Value |
|------|-------|
| Host | MacBook Pro 2015 (macOS 15.7) |
| Device | Mi 8, codename `dipper`, USB path 20-2, transport_id 4 |
| Android | 14 (UQ1A.240205.004), LineageOS userdebug |
| Kernel | 4.9.337-perf, aarch64 |
| ADB serial | `a6520fa3` |
| Bootloader | Unlocked (`fastboot getvar unlocked → yes`) |
| Boot partition | `/dev/block/bootdevice/by-name/boot` — single slot (no A/B) |
| Boot image size | 64MB, Android boot image v1 |
| Magisk | v30.7 (30700) from `topjohnwu/Magisk` GitHub |

## Key Findings

### 1. Magisk Boot-Patch Works Without Recovery

The entire root process was done via ADB from a computer — no TWRP, no physical phone interaction until the very end (verification). Steps:
1. Download Magisk APK → extract binaries with `unzip`
2. Push to `/data/local/tmp/magisk/`
3. `dd` the boot partition
4. Run `boot_patch.sh` with `KEEPVERITY=false KEEPFORCEENCRYPT=false`
5. `dd` the patched image back
6. Reboot

### 2. ADB root on Userdebug ROM Simplifies Everything

Because the ROM is a `userdebug` build (LineageOS), `adb root` grants a root shell directly. All commands run without needing `su` — you can read `/debug_ramdisk/`, write to protected paths, and run `dd` directly.

**On production ROMs** you'd need alternative approaches:
- Patch via TWRP (if available)
- Or root via other methods first, then install Magisk
- Or use `adb shell → su -c` if a temporary root method exists

### 3. Magisk Stub APK Quirk

The Magisk APK from GitHub releases is a **stub** — it's ~11MB and contains only the bootstrapper. The actual Magisk Manager UI gets downloaded by the Magisk daemon after root is established.

This means:
- `adb install magisk.apk` succeeds
- `pm list packages` shows `com.topjohnwu.magisk`
- **But** launching via ADB fails: `am start -n com.topjohnwu.magisk/.ui.MainActivity` → `Error: Activity class does not exist`
- **Fix:** User must launch from phone screen (app drawer → tap Magisk icon). The stub expands on first user launch.

Root functionality works immediately regardless of whether the Manager app has been opened.

### 4. Verification Commands

```bash
# Check Magisk daemon
adb root
adb shell "ps -A | grep magiskd"

# Check Magisk version
adb shell "/debug_ramdisk/magisk -c"

# Test su
adb shell "PATH=/debug_ramdisk:\$PATH su -c 'id'"
# Expected: uid=0(root) gid=0(root) groups=... context=u:r:magisk:s0

# Check magisk binary location
adb shell "ls -la /debug_ramdisk/magisk"
```

### 5. Boot Image Details

- **Size:** 64MB (65536 blocks × 1024 bytes)
- **Format:** Android boot image v1
- **Partition device:** `/dev/block/bootdevice/by-name/boot`
- **No A/B slots:** Only one `boot` partition (no `boot_a`/`boot_b`)

Typical boot_patch.sh output:
```
Backup stock boot image -> /data/local/tmp/boot.img
Reading stock boot image: /data/local/tmp/boot.img
MagiskBoot v30.7 - Boot Image Manipulation Tool
- Unpacking boot image
KEEPVERITY=false → skipping dm-verity removal
KEEPFORCEENCRYPT=false → skipping forced encryption removal
- Checking ramdisk status
- Device is system-as-root
- Stock boot image detected
- Patching ramdisk
- Repacking boot image
New boot image ready: /data/local/tmp/new-boot.img
```

### 6. Bootloop Recovery

Always keep a backup of the original boot image (`boot.img.backup` or similar). If the patched image causes bootloop:

1. Hold **Power + VolDown** to enter fastboot
2. `fastboot devices` — verify device detected
3. `fastboot flash boot original-boot.img`
4. `fastboot reboot`

## Error Modes Encountered

### TWRP Download: Anti-hotlink

```
curl -sL -o /tmp/twrp.img "https://dl.twrp.me/dipper/twrp-3.7.0_12-0-dipper.img"
# Result: 6.7KB HTML page, not an image
# "file tmp/twrp.img" → "HTML document, ASCII text"
```

Root cause: TWRP's CDN (dl.twrp.me) blocks curl with no `Referer` header. Setting `Referer: https://dl.twrp.me/dipper/` still returned HTML — the site uses anti-hotlink/Cloudflare protection.

**Workaround:** Use Magisk boot-patch instead. No TWRP needed. ✅

### Magisk Manager Launch via ADB: Activity Not Found

```
adb shell am start -n com.topjohnwu.magisk/.ui.MainActivity
# Error: Activity class {com.topjohnwu.magisk/com.topjohnwu.magisk.ui.MainActivity}
# does not exist.
```

Root cause: Stub APK hasn't expanded yet. The `base.apk` in `/data/app/~~/com.topjohnwu.magisk/` is the stub, not the full app.

**Workaround:** Launch from phone screen. Or pre-extract the full app (not tested — the daemon handles this automatically after first launch).

### su Unreachable from Non-Root Shell

When `adb unroot` (non-root adbd):
```
$ adb shell "PATH=/debug_ramdisk:\$PATH su -c 'id'"
# Permission denied
```

Root cause: `/debug_ramdisk/` permissions (0700, root-only). Non-root shell can't traverse into it.

**Fix:** Use `adb root` first (userdebug ROM privilege). On production ROMs, this is a real limitation — need to rely on Magisk's mount namespace propagation, which typically requires one full boot cycle after root to take effect.

## Resource Requirements

- **Disk on host:** ~11MB for Magisk APK download, ~70MB for extraction/boot images
- **Disk on device:** ~130MB for boot.img + new-boot.img + magisk tools (64MB + 64MB + ~4MB)
- **Time:** ~5 minutes from start to reboot (download speed dependent)
- **Flashing speed** (dd): ~64MB at 168MB/s = <1 second
