---
name: android-gapps
description: Install Google Apps (MindTheGapps / NikGapps) on LineageOS or other custom-ROM Android devices via ADB, recovery sideload, TWRP, or Magisk module fallback
---

# android-gapps

Install Google Apps (GApps) on a custom-ROM Android device. Covers the full pipeline: download, flash via recovery (LineageOS / TWRP), and the Magisk module fallback when TWRP cannot mount the system partition.

## Triggers

- User wants Google Play Services / Play Store on a custom ROM
- "装Gapp" / "install gapps" / "no google services"
- Recovery signature-verification failure during sideload
- TWRP partition mount failure during GApps install
- Mi8 / dipper or similar older Xioami device on Android 14/15

## Prerequisites

- ADB + fastboot available on host
- Device bootloader **unlocked**
- USB debugging enabled
- Device model codename known (`adb shell getprop ro.product.board` or `ro.build.product`)

## Step 0: Download the LineageOS build (if reinstalling)

For a full reinstall (system won't boot, fresh start), get the official LineageOS build.

### Download URL pitfall: SPA-based download page

The official download page at `https://download.lineageos.org/<codename>` is a **JavaScript SPA** that builds download links dynamically. Plain `curl` returns only the JS loader HTML, not the actual download URL.

**Use a direct mirror instead.** The Princeton mirror works reliably:

```bash
# Pattern: https://mirror.math.princeton.edu/pub/lineageos/full/<codename>/<YYYYMMDD>/lineage-<VERSION>-<YYYYMMDD>-nightly-<codename>-signed.zip

# Example for Mi8 (dipper), build 2026-06-20:
curl -L "https://mirror.math.princeton.edu/pub/lineageos/full/dipper/20260620/lineage-22.2-20260620-nightly-dipper-signed.zip" \
  -o lineage22.zip --progress-bar

# Verify SHA256 (hash listed on https://download.lineageos.org/<codename>)
sha256sum lineage22.zip

# Also download the recovery.img from the same directory:
curl -L "https://mirror.math.princeton.edu/pub/lineageos/full/dipper/20260620/recovery.img" \
  -o los_recovery.img --progress-bar
```

### Build list on the SPA page

To find the SHA256 hashes without JS, extract from the JSON data embedded in the SPA:

```bash
curl -s "https://download.lineageos.org/<codename>" | grep -oE '"sha256":"[a-f0-9]+"' | head -5
# Or use the web-based tool to list builds and copy the mirror URL manually.
```

### Full reinstall sequence (device stuck in fastboot)

If the device **only boots to fastboot** after formatting /data:

1. `fastboot flash recovery los_recovery.img` — flash LineageOS recovery
2. `fastboot reboot recovery` — try this first, BUT on Mi8/dipper this command **sends the device back to fastboot** instead of recovery (known quirk). Fallback: user holds **Volume Up + Power** during boot until the LineageOS logo appears.
3. In recovery: **Factory Reset → Format data / factory reset** (already done)
4. **Apply update → Apply from ADB** → `adb sideload lineage22.zip` (~1.1 GiB)
5. Without rebooting: **Apply update → Apply from ADB** → `adb sideload mindthegapps.zip`
6. If signature verification fails: tap **"Yes" / "Install anyway"** on device screen
7. **Reboot system now** — first boot takes 5–15 minutes

### Hardware key combos (be precise — do not use ambiguous phrasing)

Always state the EXACT buttons, not approximate descriptions:

**Mi8 (dipper) — entering Fastboot:** Power off → hold **Volume Down** + **Power** simultaneously until "FASTBOOT" appears on screen.

**Mi8 (dipper) — entering Recovery:** Power off → hold **Volume Up** + **Power** simultaneously until the LineageOS logo appears.

**Mi6 (sagit):** Same pattern (Volume Up/Down + Power).

**⚠️ Common error:** `fastboot reboot recovery` on Mi8/dipper sends the device BACK to fastboot (not recovery) — a known ROM/fastboot quirk. Always use the hardware key combo to enter recovery, never rely on `fastboot reboot recovery` for Xiaomi devices.

### ADB push/install path pitfall

When pushing APKs to a running Android system for `pm install`, use `/data/local/tmp/` NOT `/sdcard/`:

```bash
# ❌ /sdcard/ — fails with SELinux error:
#   "System server has no access to read file context u:object_r:fuse:s0"
adb push app.apk /sdcard/Download/
adb shell pm install /sdcard/Download/app.apk  # FAILS

# ✅ /data/local/tmp/ — works reliably
adb push app.apk /data/local/tmp/
adb shell pm install /data/local/tmp/app.apk
```

When Magisk file picker can't see `/data/local/tmp/` (it only shows `/sdcard/`), push to `/sdcard/Download/` first, then use Magisk's file picker to select from `/sdcard/Download/`.

On Xiaomi Mi8 (dipper) and possibly other older Xiaomi devices, `fastboot reboot recovery` does not boot to recovery — it boots back to **fastboot** (the bootloader). This is a ROM/fastboot quirk, not a flash failure.

Symptoms:
```
$ fastboot reboot recovery
Rebooting into recovery                            OKAY [  0.000s]
Finished. Total time: 0.001s
# Device boots to fastboot again
$ fastboot devices
a6520fa3    fastboot
```

**Fix:** Always tell the user to manually enter recovery via hardware keys (Volume Up + Power on Mi8) after flashing recovery via fastboot. Do not rely on `fastboot reboot recovery` for Xiaomi devices.

### Preferred installation path: LineageOS stock recovery

The [official LineageOS wiki](https://wiki.lineageos.org/devices/<codename>/install/) recommends using **LineageOS Recovery** (NOT TWRP) for installation. TWRP is a fallback for devices whose stock recovery can't handle GApps signature verification.

```bash
# 1. Flash LineageOS recovery via fastboot
fastboot flash recovery los_recovery.img

# 2. Reboot to recovery (hardware key combo or fastboot reboot recovery)
fastboot reboot recovery
# If that fails: manually hold Volume Up + Power during boot

# 3. In recovery: Factory Reset → Format data / factory reset
#    (wipes encryption keys, required before first install)

# 4. Select: Apply update → Apply from ADB

# 5. Sideload the ROM ~1.1 GiB
adb sideload lineage22.zip
# (47% or "adb: failed to read command: Success" is normal)

# 6. WITHOUT rebooting, go back → Apply update → Apply from ADB again
#    Then sideload GApps
adb sideload mindthegapps.zip

# 7. If signature verification fails: tap "Yes" / "Install anyway"
#    (expected for MindTheGapps — it's test-signed)

# 8. Reboot system now
```

**Important:** Do GApps BEFORE first boot. Once the system boots without Google services, you'd need to factory reset to add them.

### When to use TWRP instead of stock recovery

TWRP is useful when:
- Stock LineageOS recovery signature-verification bypass doesn't work
- You need file manager / ADB push to /sdcard (device already has working ROM)
- You're troubleshooting a boot-loop and need to disable Magisk modules
- The device is known to have TWRP with kernel support matching the Android version

**Check whether TWRP supports your Android version first:**
```bash
# Boot into TWRP, then check:
adb shell "cat /proc/filesystems | grep -E 'erofs|ext4|f2fs'"
# Missing erofs = TWRP too old for Android 14+
```

## Step 1: Download the right GApps

### Android 15+ (LineageOS 22.x): NikGapps is the recommended choice

MindTheGapps **fails on Android 15** due to its installer script (`get_block_for_mount_point()`) not handling dynamic partitions. **Use NikGapps instead.**

**NikGapps** — recommended for LineageOS 22 (Android 15+). Get from SourceForge Config-Releases (latest daily builds):

```bash
# Config-Releases channel — LineageOS 22 specific builds, updated daily
# Browse: https://sourceforge.net/projects/nikgapps/files/Config-Releases/Android-15/

# Example: 2026-06-20 build (essential varant, 276 MB)
curl -L "https://sourceforge.net/projects/nikgapps/files/Config-Releases/Android-15/20-Jun-2026/NikGapps-a15-essential-arm64-15-20260620-unofficial.zip/download" \
  -o nikgapps.zip --progress-bar
```

Variant guide (ARM64 for most modern phones):
- **essential** (~276 MB): Play Store, Play Services, SetupWizard — sufficient for most users
- **core** (~126 MB): Minimal — Play Services only, no Play Store
- **basic** (~244 MB): core + a few extras (Calculator, Calendar)
- **stock** (~923 MB): Near-stock Google experience
- **full** (~1.1 GB): Everything including Google Assistant

**Important:** Always use the **Config-Releases** channel for LineageOS 22 — these are tested against LineageOS specifically. The "Releases" channel also has stable Android 15 builds but they may be weeks old.

**MindTheGApps** — **NOT recommended for Android 15+**. Only use for Android 14 and below:

```bash
# Only for Android 14 and below
curl -sL "https://api.github.com/repos/MindTheGapps/14.0.0-arm64/releases/latest" | grep browser_download_url
```

**TWRP** download from `https://twrp.me` — requires browser-like User-Agent:

```bash
curl -L -A "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) ..." --referer "https://dl.twrp.me/<codename>/" \
  "https://dl.twrp.me/<codename>/<filename>.img" -o twrp.img
```

## Step 2: Flash via LineageOS stock recovery

1. Reboot to recovery:
   ```
   adb reboot recovery
   ```
2. Authorize ADB in recovery screen
3. Enter **Apply update → Apply from ADB** (use volume keys + power)
4. Sideload:
   ```
   adb sideload mindthegapps.zip
   ```
5. If **signature verification fails**: select "Install anyway" on device screen, then re-sideload

### Pitfall: ADB authorization in recovery

Recovery mode resets USB debugging authorization. After `adb reboot recovery`, the device will show "unauthorized" until the user taps "Allow USB debugging" on the screen. Wait for `adb devices` to show `device` or `sideload` before proceeding.

### Pitfall: MindTheGapps fails after tapping "Yes" on signature

This is a **different failure** from the signature-verification prompt. Sequence:

1. `adb sideload mindthegapps.zip` → transfers to 47% (normal)
2. Phone shows **"Signature verification failed"**
3. User taps **"Yes" / "Install anyway"**
4. Installation continues briefly, then shows **"Installation aborted"** / **"Updater process ended with ERROR: 1"**

**Root cause:** MindTheGapps installer script (`META-INF/com/google/android/update-binary`) contains a `get_block_for_mount_point()` function that cannot find the `/system` block device on Android 15 **dynamic partition** layouts. The script tries `mount /dev/block/bootdevice/by-name/system /mnt/system` which fails because on Android 15 the system partition lives under `/dev/block/dm-*` (device-mapper), not at the legacy by-name symlink.

**This is NOT a signature problem** — tapping "Yes" is correct, but bypassing the signature check doesn't fix the mount detection code.

**Fixes (in priority order):**

**Fix A — Try NikGapps instead (recommended):**
See `references/nikgapps-reference.md` for download links. NikGapps has better Android 15 dynamic partition support and doesn't trigger this mount-point failure.

**Fix B — Modify MindTheGapps installer script:**
```bash
# 1. Extract the zip
mkdir /tmp/gapps-fix && cd /tmp/gapps-fix
unzip /tmp/mindthegapps.zip -d /tmp/gapps-fix/extracted

# 2. Edit the update-binary script
# Find the get_block_for_mount_point() function and replace its body with:
#   cat /etc/recovery.fstab | cut -d '#' -f 1 | grep /system | grep -o '/dev/[^ ]*' | head -1
# This reads the recovery's fstab directly instead of guessing the block device.

# 3. Re-zip without compression (Android recovery expects store mode for update-binary)
cd /tmp/gapps-fix/extracted
zip -r -0 /tmp/mindthegapps-fixed.zip .

# 4. Try sideloading the fixed zip
adb sideload /tmp/mindthegapps-fixed.zip
```
See `references/dynamic-partitions-diagnosis.md` for the exact code snippet and diff.

**Fix C — Manual GApps install via ADB root (when recovery methods all fail):**
Boot the system (GApps-free), enable root, and use `adb shell su -c` to push Google services manually. See Step 5 (Magisk module) below.

**Fix D — Factory reset + reinstall:**
If the device booted into the system before GApps were installed, the wiki says: *"If you reboot into LineageOS before installing Google Apps, you must factory reset and then install them, otherwise expect crashes."* Go back to recovery, format data, re-sideload ROM + GApps without booting between them.

## Step 3: Replace stock recovery with TWRP (if needed)

If stock recovery cannot flash GApps (signature issues, partition errors):

```bash
# Reboot to bootloader (fastboot mode)
adb reboot bootloader

# Flash TWRP
fastboot flash recovery twrp-<version>-<codename>.img
fastboot reboot

# Immediately hold the key combo to boot into TWRP
# Mi8/dipper: Volume Up + Power after screen goes dark
# Most Xioami: Volume Up + Power
```

Once TWRP boots, it patches the stock ROM to prevent overwriting TWRP on next normal boot.

## Step 4: Flash GApps via TWRP

### Option A — ADB Sideload (recommended)
1. In TWRP: **Advanced → ADB Sideload** → swipe to enable
2. From host:
   ```bash
   adb sideload mindthegapps.zip
   ```
3. TWRP does NOT enforce signature verification, so "Install anyway" is unnecessary

### Option B — Push to device + twrp install
Only works if data partition is **not encrypted**:
```bash
adb push mindthegapps.zip /sdcard/
adb shell twrp install /sdcard/mindthegapps.zip
```

Encrypted /data produces errors like `Required key not available`. Use sideload instead.

### Pitfall: TWRP too old for Android 14/15 dynamic partitions

TWRP builds for older devices (e.g. TWRP 3.7.0_9-0 for Mi8 dipper, 2022) may lack:
- **EROFS** filesystem support
- **dm-verity / device mapper** support for dynamic partitions
- Recognition of `super` partition layout

Symptoms:
```
mount: /dev/block/bootdevice/by-name/system: need -t
Could not mount /mnt/system! Aborting
```

**Root cause:** system partition lives under `/dev/block/dm-0` (managed by `lpdump` / `super`), not directly at the `system` by-name symlink. Old TWRP can't handle it.

**Fix:** Fall back to Magisk module method (Step 5 below).

## Step 5: Magisk module fallback (when recovery/TWRP can't mount system)

If TWRP can't mount the system partition, install GApps as a Magisk module from the running system:

```bash
# 1. Push GApps zip to device
adb push mindthegapps.zip /data/local/tmp/

# 2. Extract on device (via root shell)
adb shell su -c "
  cd /data/local/tmp
  unzip -o mindthegapps.zip -d /tmp/gapps-extract/
"

# 3. Create Magisk module structure
adb shell su -c "
  mkdir -p /data/adb/modules/gapps/system/product/{app,priv-app,etc,framework,lib,overlay}
  mkdir -p /data/adb/modules/gapps/system/system_ext/{etc/permissions,priv-app}
  mkdir -p /data/adb/modules/gapps/system/addon.d

  # Create module.prop
  cat > /data/adb/modules/gapps/module.prop << 'EOF'
id=gapps
name=MindTheGApps
version=v1.0
versionCode=1
author=Custom
description=Google Apps installed via Magisk module
EOF
"

# 4. Copy all files from the extracted zip
adb shell su -c "
  cd /tmp/gapps-extract/system
  cp -r product/* /data/adb/modules/gapps/system/product/
  cp -r system_ext/* /data/adb/modules/gapps/system/system_ext/
  cp -r addon.d/* /data/adb/modules/gapps/system/addon.d/
"

# 5. Reboot
adb reboot
```

Magisk loads overlay files from `/data/adb/modules/<name>/system/` onto the real system at boot time. The files persist through OTA updates as long as Magisk is installed.

### Pitfall: Termux and Termux:API require same signature

Termux and Termux:API use a **shared user ID** (`com.termux`). Installing them from different sources (F-Droid + GitHub, or different GitHub commits) gives them different signatures → `INSTALL_FAILED_SHARED_USER_INCOMPATIBLE`.

**Always get both from the same release:**
```bash
# Both from GitHub termux releases (recommended — same signature)
curl -sL "https://api.github.com/repos/termux/termux-app/releases/latest" | grep browser_download_url
curl -sL "https://api.github.com/repos/termux/termux-api/releases/latest" | grep browser_download_url

# Both from F-Droid (also same signature)
# Only if you can get the actual APK, not an HTML redirect
```

### Pitfall: ADB pm install fails with FUSE / sdcard permission on Android 15+

Android 15+ restricts `pm install` from `/sdcard/` (FUSE layer). Error:
```
avc: denied { read } for scontext=u:r:system_server:s0 tcontext=u:object_r:fuse:s0
Error: Unable to open file: /sdcard/xxx.apk
```

**Always push to /data/local/tmp/ instead:**
```bash
adb push app.apk /data/local/tmp/
adb shell pm install /data/local/tmp/app.apk
```

### Pitfall: F-Droid direct APK URLs return HTML

F-Droid's repo URLs do server-side checks (User-Agent, HTTP vs HTTPS, referer). Plain `curl -L` on the page URL returns HTML, not the APK.

**Fixes:**
```bash
# Option A: Use GitHub releases (preferred for Termux — same signature as termux-api)
curl -sL "https://api.github.com/repos/termux/termux-app/releases/latest" | grep browser_download_url

# Option B: Use a browser-like curl with proper headers + ?fingerprint
curl -L -A "Mozilla/5.0 (Linux; Android 15)" \
     --referer "https://f-droid.org/" \
     "https://f-droid.org/repo/com.termux_1000.apk"
```

### Magisk rooting via boot.img patch (no TWRP needed)

When the device has no root, install Magisk by patching the boot.img from the ROM zip:

**Step A: Prepare files on Mac**

```bash
# 1. Extract boot.img from the ROM zip
cd /tmp && unzip -o lineage22.zip boot.img

# 2. Download Magisk Manager APK (latest v30.7)
curl -L "https://github.com/topjohnwu/Magisk/releases/download/v30.7/Magisk-v30.7.apk" \
  -o /tmp/magisk.apk

# 3. Push both to device (use /data/local/tmp/, NOT /sdcard/ — Android 15 pm install fails on /sdcard/)
adb push /tmp/magisk.apk /tmp/boot.img /data/local/tmp/

# 4. Install Magisk Manager APK
adb shell pm install /data/local/tmp/magisk.apk
```

**Step B: On the phone — patch boot.img in Magisk app**

1. Open **Magisk** app → follow first-run setup
2. Tap **Install** → select **"Select and Patch a File"**
3. Navigate to `/data/local/tmp/boot.img` → select it
4. Wait for patch to complete (progress bar in app)

**Step C: Pull patched image and flash via fastboot**

```bash
# 5. Pull patched image back to Mac
adb pull /data/local/tmp/magisk_patched.img /tmp/magisk_boot.img

# 6. Reboot to fastboot and flash
adb reboot bootloader
fastboot flash boot /tmp/magisk_boot.img
fastboot reboot
```

**Step D: Verify root**

```bash
adb shell su -c "id"
# Should return: uid=0(root) gid=0(root)
```

### Key pitfalls in this flow

- **`pm install` on /sdcard/ fails on Android 15** — Error `avc: denied { read }`. Use `/data/local/tmp/` instead.
- **Magisk Manager and boot.img must match the installed ROM** — boot.img from a different ROM variant will cause boot failure.
- **Magisk Manager ≠ Magisk zip** — The APK (Manager) is a shell that downloads and installs the actual Magisk binary. For patch-based rooting, use the APK only.
- **Termux and Termux:API must share the same signature** — Installing Termux from one source (old APK) and Termux:API from another (F-Droid/GitHub) causes `INSTALL_FAILED_SHARED_USER_INCOMPATIBLE`. Always reinstall both from the same source (e.g., both from `github.com/termux/termux-app/releases` + `github.com/termux/termux-api/releases`). Uninstall old version first: `adb shell pm uninstall com.termux`

## Verification

After reboot:
- Check Google Play Services is running:
  ```bash
  adb shell dumpsys package | grep google
  ```
- Open Play Store app on device
- Check Settings → Apps → Google Play Services is present

## Device Reference

| Device | Codename | Recovery key combo | Notes |
|--------|----------|-------------------|-------|
| Mi8 | dipper | Vol Up + Power | TWRP 3.7.0 too old for A15 |
| Mi6 | sagit | Vol Up + Power | — |
| Pixel | various | Vol Down + Power (fastboot) | EROFS support in modern TWRP |

## Pitfalls

- **TWRP version must match Android major version.** A TWRP built for Android 9-12 kernel (`_9-0` suffix) won't mount Android 14+ dynamic partitions.
- **Signature verification in stock recovery:** MindTheGapps uses test keys. Stock LineageOS recovery warns but lets you force-install via "Install anyway". TWRP never blocks test-signed zips.
- **Sideload re-auth loop:** After selecting "Install anyway" in stock recovery, ADB drops to "unauthorized". The user must tap "Allow USB debugging" on the device screen again before the next sideload attempt. Each re-auth resets pairing, so expect this cycle for every retry.
- **Encrypted data in TWRP:** If /data is encrypted with a lock-screen PIN, TWRP cannot mount `/sdcard`. Use `adb sideload` in TWRP instead of `adb push`.
- **Magisk module survives OTA:** Files under `/data/adb/modules/` persist across LineageOS updates. If a GApps APK is updated via Play Store, the module overlay is automatically bypassed for the updated version.
- **LineageOS recovery is preferred over TWRP** for GApps installation. The [official LineageOS wiki](https://wiki.lineageos.org/devices/<codename>/install/) says stock recovery works with MindTheGapps — click "Yes" when signature verification fails. TWRP is a fallback for recovery-flash method fails.
- **`twrp decrypt` may fail from ADB shell but work from TWRP's built-in terminal.** If `adb shell twrp decrypt <password>` returns "Failed to decrypt data" silently, try entering the command directly in TWRP's **Advanced → Terminal** screen instead. TWRP may not forward the authentication prompt to the ADB shell session.
- **608 MB module size may cause boot failure:** GApps (especially Velvet/Google Search and GmsCore) are large files. A Magisk module with 600MB+ overlay can cause:
  - First boot to take 5+ minutes (device appears stuck at boot animation)
  - Complete boot failure in some cases (Magisk times out processing overlay)
  - Recovery requires entering lock-screen password in TWRP (if /data encrypted) then deleting / renaming the module directory at `/data/adb/modules/gapps/`
- **Recovering from GApps-module boot failure with encrypted /data:**
  1. Boot to TWRP (hardware key combo)
  2. TWRP will show a **"Decrypt data"** prompt — enter the device's lock-screen password/pattern
  3. Once decrypted, /data becomes accessible:
     ```bash
     # Remove or disable the module
     adb shell "rm -rf /data/adb/modules/gapps"
     # Or create a 'disable' file
     adb shell "touch /data/adb/modules/gapps/disable"
     ```
  4. If TWRP doesn't show the decrypt prompt, navigate to **Advanced → Terminal** and try:
     ```bash
     twrp decrypt <your-password>
     ```
  5. Reboot to system — should boot normally again
- **TWRP `twrp decrypt` CLI:** From TWRP's terminal, `twrp decrypt <password>` attempts to decrypt the data partition. Entering a wrong password or too few characters silently returns "Failed to decrypt data" with no error detail. On some builds, the command only works from TWRP's built-in terminal (not via `adb shell`).
