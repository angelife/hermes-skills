---
name: android-magisk-root-activation
title: Android Magisk Root Activation After Factory Reset / Relock
description: >
  Covers the recurring class of "Mi8 / dipper-class device has been factory reset,
  Magisk APK installed, but root is not active" — including exact recovery/boot
  flashing paths, post-flash ROOT verification sequence, GUI-less Magisk activation,
  and how to use locally cached artifacts instead of redownloading.
tags: [android, magisk, root, fastboot, twrp, dipper, mi8]
---

## Trigger

- Device just factory-resetted and you need Magisk root again
- Magisk APK installs, reboot succeeds, but `su` / `/magisk` are still missing
- You have local `recovery_*.img`, `patched_boot.img`, `boot.img`, `Magisk.apk`
- User explicitly says "解锁机器 / 随便刷 / 已重启"

## Premise Lock

- Mi8 / dipper: BL is unlocked and fastboot is allowed
- One USB-C cable to Mac + ADB is enough
- `ro.secure=1` and absent `/magisk` after reboot = root not active, not hardware failure

## Golden Rule

**Use local artifacts first.** Do not redownload TWRP/Magisk if the file is already present on the Mac.

Before any step, prefer these local paths:

- Mi8 recovery: `/Users/macos/Downloads/recovery_dipper.img`
- Mi8 boot image: `/Users/macos/Downloads/patched_boot.img`
- Mi8 stock boot image: `/Users/macos/Downloads/boot.img`
- Magisk APK: `/Users/macos/Downloads/Magisk-v30.7.apk` (fallback `/Users/macos/Downloads/Magisk.apk`)

## Workflow

### 1. Get to fastboot and verify device

```bash
adb -s a6520fa3 reboot bootloader
sleep 8
fastboot devices
```

### 2. Flash recovery from fastboot

```bash
fastboot flash recovery /Users/macos/Downloads/recovery_dipper.img
```

### 3. Boot recovery, install Magisk APK

```bash
fastboot reboot recovery
sleep 8
adb wait-for-device
adb devices -l
adb -s a6520fa3 install -r /Users/macos/Downloads/Magisk-v30.7.apk
```

### 4. Magisk GUI boot-patch (user-side)

On the device:
1. Open Magisk
2. Install -> Select and patch a file -> `/sdcard/Download/boot.img`
3. Wait for `magisk_patched-*.img`

On Mac:
```bash
adb -s a6520fa3 ls /sdcard/Download/ | grep -i 'Magisk_patched\|patched'
# expected: magisk_patched-30700_*.img
```

### 5. Pull and flash patched boot

```bash
adb -s a6520fa3 pull /sdcard/Download/magisk_patched-30700_PQriw.img /Users/macos/Downloads/magisk_patched-30700_PQriw.img
adb -s a6520fa3 reboot bootloader
sleep 8
fastboot devices
fastboot flash boot /Users/macos/Downloads/magisk_patched-30700_PQriw.img
fastboot reboot
sleep 12
adb wait-for-device
adb devices -l
```

## Post-Flash Root Verification Sequence

Run in this order; each step proves the next state:

```bash
# 1. ADB shell reachable
adb devices -l

# 2. Android debug state
adb shell getprop ro.secure   # expect 0 after Magisk root
adb shell getprop ro.debuggable # expect 1

# 3. su path
adb shell 'which su 2>/dev/null; ls -l /system/bin/su 2>/dev/null; ls -l /system/xbin/su 2>/dev/null; ls -l /sbin/su 2>/dev/null; ls /magisk/.core/bin/ 2>/dev/null; ls /product/bin/su 2>/dev/null'

# 4. Magisk daemon
adb shell 'ps -A | grep -i magisk || true'

# 5. Actual root
adb shell su -c 'id' 2>&1 || true
# expect: uid=0(root)
```

Expected success state:
- `ro.secure=0`
- `which su` returns `/product/bin/su` or `/system/bin/su`
- `/magisk/.core/bin/` exists
- `ps` shows `magiskd`
- `su -c 'id'` returns `uid=0(root)`

## GUI-Less Magisk Rescue

If Magisk app won't launch from launcher:

```bash
# Enable the package (it can be disabled by system after factory reset)
adb shell pm enable com.topjohnwu.magisk

# Try launcher intent
adb shell monkey -p com.topjohnwu.magisk -c android.intent.category.LAUNCHER 1
```

If still no activity resolves, fall back to patching boot from Mac using the stock `/Users/macos/Downloads/boot.img` and the Magisk app on-device. Do not loop ADB activity discovery.

## Known Pitfalls

### Reboot timing
After `fastboot reboot`, always `sleep 12` before `adb wait-for-device`. Android 15 on Mi8 can take 10-15s to settle ADB after Magisk boot.

### Magisk APK reinstall wipe
`adb install -r` on an already working Termux/data-heavy app is a known data wipe pattern on Android 15. For Magisk, the wipe risk is lower, but only reinstall when `which su` is already missing.

### Boot-image mismatch
If `su -c 'id'` still returns permission denied after patched boot:
1. Verify the patched file was generated from the **currently running** boot.img
2. If you used `recovery_dipper.img` only to push files, ensure `boot.img` was actually replaced, not just recovery

### Bootloop fallback
If device bootloops after flashing patched boot, restore stock boot from local `/Users/macos/Downloads/boot.img`:

```bash
adb -s a6520fa3 reboot bootloader
fastboot flash boot /Users/macos/Downloads/boot.img
fastboot reboot
```

### Loopbreaker rule
After every state-changing flash/reboot, run exactly one new verification command set. Do not chain 3+ actions without reading the device state.

## Next Stage

After root is confirmed:
1. Install Termux locally if missing: `/Users/macos/Downloads/termux-arm64-v0.118.3.apk` or `termux-universal-v0.118.3.apk`
2. In Termux: `pkg update && pkg install proot-distro -y`
3. Install Ubuntu: `proot-distro install ubuntu`

Termux-side details are in the existing `android-termux-deploy` skill.
