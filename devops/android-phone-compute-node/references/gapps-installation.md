# GApps (Google Apps) Installation on LineageOS

Session-logged learnings from installing MindTheGApps on Mi8 (dipper, LineageOS 22.2 / Android 15).

---

## Download MindTheGApps

The official GitHub repo has releases for each Android version:

- Android 15 (arm64): https://github.com/MindTheGapps/15.0.0-arm
- Android 15 (arm): https://github.com/MindTheGapps/15.0.0-arm

### Download via API

```bash
# Get latest release info
curl -sL "https://api.github.com/repos/MindTheGapps/15.0.0-arm/releases/latest" \
  | grep -E '"tag_name"|"browser_download_url"'

# Download zip (~268MB)
curl -L -o mindthegapps.zip \
  "https://github.com/MindTheGapps/15.0.0-arm/releases/download/<tag>/<filename>.zip"
```

---

## TWRP Compatibility Issue (Android 15 Dynamic Partitions)

**TWRP 3.7.0_9-0-dipper (2022) CANNOT install GApps on LineageOS 22 (Android 15) —** the installer script fails at:

```
mount: /dev/block/bootdevice/by-name/system: need -t
Could not mount /mnt/system! Aborting
```

**Root cause:** Android 15 uses dynamic (virtual) partitions via device-mapper (`dm-0`). The raw block device `/dev/block/sda21` (system) is **not** a directly mountable ext4 partition — it's part of a `super` logical volume. The running system mounts:

```
/dev/block/dm-0 on / type ext4 (ro,...)    ← system
/dev/block/dm-4 on /system_ext type ext4 (ro,...)
```

TWRP 3.7.0's kernel predates Android 15's partition scheme and can't resolve the dm targets.

**Workaround options (none fully tested):**
- Find a newer TWRP build (none official for dipper after 2022)
- Use a different Recovery (OrangeFox / PitchBlack) that supports dynamic partitions
- Install GApps from within the running system (see Magisk Module method below)

---

## Magisk Module Method (from Running System)

When TWRP can't mount /system, but the device is booted into LineageOS with Magisk root:

### 1. Push GApps zip to device
```bash
adb push /tmp/mindthegapps.zip /data/local/tmp/
```

### 2. Extract zip on device
```bash
adb shell su -c "
  cd /data/local/tmp
  unzip -o mindthegapps.zip -d /tmp/mtg-install/
"
```

### 3. Create Magisk module structure
```bash
adb shell su -c "
  mkdir -p /data/adb/modules/mtgapps/system/product/app
  mkdir -p /data/adb/modules/mtgapps/system/product/priv-app
  mkdir -p /data/adb/modules/mtgapps/system/product/etc
  mkdir -p /data/adb/modules/mtgapps/system/product/framework
  mkdir -p /data/adb/modules/mtgapps/system/product/lib
  mkdir -p /data/adb/modules/mtgapps/system/product/overlay
  mkdir -p /data/adb/modules/mtgapps/system/system_ext/etc/permissions
  mkdir -p /data/adb/modules/mtgapps/system/system_ext/priv-app
  mkdir -p /data/adb/modules/mtgapps/system/addon.d

  cat > /data/adb/modules/mtgapps/module.prop << EOF
id=mtgapps
name=MindTheGApps
version=v1.0
versionCode=1
author=TeamWin
description=MindTheGApps for Android 15
EOF
"
```

The system partition in Magisk's overlay appears writable (`mount -o rw,remount /` works through overlay), but direct writes to `/system/product/` hit the read-only partition underneath. The module directory is where Magisk expects overlays.

### 4. Copy GApps files into module
```bash
adb shell su -c "
  cd /tmp/mtg-install/system
  cp -r product/app/*    /data/adb/modules/mtgapps/system/product/app/
  cp -r product/priv-app/* /data/adb/modules/mtgapps/system/product/priv-app/
  cp -r product/etc/*    /data/adb/modules/mtgapps/system/product/etc/
  cp -r product/framework/* /data/adb/modules/mtgapps/system/product/framework/
  cp -r product/lib/*    /data/adb/modules/mtgapps/system/product/lib/
  cp -r product/overlay/* /data/adb/modules/mtgapps/system/product/overlay/
  cp -r system_ext/*     /data/adb/modules/mtgapps/system/system_ext/
  cp -r addon.d/*        /data/adb/modules/mtgapps/system/addon.d/
"
```

Result: ~38 files, ~607MB total (GmsCore alone is 154MB, Phonesky 76MB, Velvet 76MB).

### 5. Reboot to activate module
```bash
adb reboot
```

---

## Boot Failure Recovery (Magisk Module Bootloop)

**Warning:** A Magisk module with 600MB+ GApps overlay can cause boot failure (stuck at boot animation indefinitely, 5+ minutes no ADB).

On Android 15 with FBE (File-Based Encryption), TWRP cannot decrypt `/data/adb/` (credential-encrypted storage) without the lock screen password/pattern:

```bash
# In TWRP: check if /data is decrypted
ls /data/
# → Shows only "lost+found" and "media" = encrypted
# → Shows full directory tree = decrypted

# Try to decrypt with default_password (only works for DE, not CE)
twrp decrypt default_password
ls /data/adb/  # may still show "No such file or directory"
```

`twrp decrypt default_password` decrypts the **device-encrypted** (DE) storage, but `/data/adb/` is under **credential-encrypted** (CE) storage, protected by the user's lock screen credentials.

**Recovery options:**

1. **Enter lock screen password in TWRP** — TWRP prompts for decryption at boot. If the user enters their PIN/pattern, `/data/adb/` becomes accessible and the module can be removed:
   ```bash
   # In TWRP shell (after decryption)
   rm -rf /data/adb/modules/mtgapps
   # Or create a disable file
   touch /data/adb/modules/mtgapps/disable
   ```

2. **Format /data** — Wipes all user data (files, apps, settings) but also removes the module. The system boots cleanly after.

3. **Boot to safe mode** — On LineageOS: during boot animation, hold Volume Down until the system enters safe mode (disables all Magisk modules). Then delete the module:
   ```bash
   # In safe mode
   su -c 'rm -rf /data/adb/modules/mtgapps'
   reboot
   ```

---

## Pitfalls

- TWRP 3.7.0 (2022) on dipper does NOT support Android 15 dynamic partitions — don't rely on it for system operations
- MindTheGApps installer script expects `/mnt/system` to be mountable; TWRP mounts at `/system` directly
- Magisk module with 600MB overlay can cause boot failure
- FBE encryption makes TWRP recovery of modules nearly impossible without lock screen credentials
- `twrp decrypt default_password` does NOT decrypt CE storage
- Formatting /data is the nuclear option but guaranteed to fix bootloop
- NikGapps may work differently — untested with this approach
