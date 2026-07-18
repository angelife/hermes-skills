# Known Android Devices — Specs & ADB Workflow Reference

## Xiaomi Mi 8 (codename: dipper)

| Property | Value |
|----------|-------|
| SoC | Snapdragon 845 (Kryo 385: 4x A75 + 4x A55) |
| RAM (rated) | 8 GB |
| RAM (usable, free -m) | ~5.6 GB (GPU/kernel/hw reservations ~2.4 GB) |
| Storage | 128/256 GB eMMC |
| GPU | Adreno 630 (OpenCL 2.0, Vulkan 1.1, no CUDA) |
| ADB vendor ID | 0x18d1 (Google Inc.) |
| ADB transport | USB 2.0 480 Mbps |
| USB tethering | Supported, works as network backhaul when WiFi is broken |

Typical custom ROM setup: Android 14/15, kernel 4.9.337-perf.

Key commands:
  adb shell getprop ro.build.version.release
  adb shell uname -a
  adb shell free -m | head -3
  adb shell df -h /data | tail -1
  adb shell cat /proc/cpuinfo | grep Processor | head -1
  adb shell su -c "id" 2>/dev/null && echo "Rooted" || echo "Not rooted"
  adb shell pm list packages | grep -iE "termux|linux|debian|ubuntu"

LLM capability (CPU-only, no root):
- Qwen2.5-1.5B Q4_K_M ~1GB ~20+ tok/s - Easy
- Llama-3.2-3B Q4_K_M ~1.8GB ~15 tok/s - Good
- Qwen2.5-7B Q4_K_M ~4GB ~5 tok/s - Usable
- Phi-3-mini-4k (3.8B) Q4_K_M ~2.2GB ~10 tok/s - Good

## Honor Play

| Property | Value |
|----------|-------|
| SoC | Kirin 970 (4x A73 2.4GHz + 4x A53 1.8GHz) |
| RAM | 4 GB (this unit: 2 GB variant) |
| Storage | 64 GB |
| GPU | Mali-G72 MP12 (no LLM acceleration) |
| Screen | Broken - ADB-only interaction |
| NPU | HiSilicon NPU (not usable for LLM) |

Status: ADB operation only. 2GB RAM limits to sub-1B models. Better as lightweight sensor/task runner.

## 多亲2 / Qin 2 (standard edition)

| Property | Value |
|----------|-------|
| SoC | Unisoc SC9832E (4x Cortex-A53 @ 1.4GHz, 28nm) |
| RAM (rated) | 1 GB |
| RAM (usable, /proc/meminfo) | ~878 MB (899220 kB MemTotal) |
| Storage | 32 GB (26 GB /data, only 3.1 GB used when clean) |
| GPU | Mali-T820 MP1 (no LLM acceleration) |
| System | Android 9 Pie Go Edition (SDK 28, ro.config.low_ram=true) |
| Architecture | armeabi-v7a (32-bit ARM) |
| ADB vendor ID | 0x1782 (Spreadtrum/Unisoc) |
| Product ID (charging) | 0x4001 |
| Product ID (ADB mode) | 0x4002 |
| Product ID (Google ADB) | 0x4ee7 (when ADB is active, vendor shown as 0x18d1 Google Inc.) |
| Bootloader | Locked (ro.boot.flash.locked=1, verifiedbootstate=green) |
| Treble | Supported (ro.treble.enabled=true) |
| Root | Magisk 20.4 installed (detected via /sbin/.magisk/block/ in mount table) |
| Model name | Qin 2 (ro.product.model), manufacturer DuoQin |
| Serial prefix | Qin2SM... |
| Cable type | Data-capable USB cable required - some charging-only cables don't expose USB interface |

Hardware variants:
- Standard (our unit): SC9832E, 1GB, Android 9 Go Edition
- Pro: SC9863A (8-core), 2GB, Android 9 full - more capable, active community

### ADB Access

To connect: USB Debugging must be enabled on the phone first.
  Settings > About Phone > tap Build Number 7x > Developer Options > USB Debugging ON

On macOS, system_profiler SPUSBDataType shows:
- Before enabling: "Spreadtrum Phone" with PID 0x4001 - adb devices shows nothing
- After enabling: PID changes to 0x4002 or 0x4ee7 - adb devices shows the device

Device appears in adb as:
  Qin2SM1908012103 device usb:20-2 product:sp9832e_1h10_gofu model:Qin_2 device:sp9832e_1h10_go

### Debloat (safe to disable)

Tested and working - these system apps can be disabled without core functionality loss:

  adb shell pm disable-user --user 0 com.microsoft.launcher     # Heavy launcher - replace with KISS
  adb shell pm disable-user --user 0 com.android.music          # Music player
  adb shell pm disable-user --user 0 com.android.calendar       # Calendar app
  adb shell pm disable-user --user 0 com.android.providers.calendar
  adb shell pm disable-user --user 0 com.android.mmsfolderview  # SMS folder view
  adb shell pm disable-user --user 0 com.duoqin.systemupdate    # System update (no updates available)
  adb shell pm disable-user --user 0 addon.sprd.browser.plugindrm

Protected (cannot disable from shell):
  com.sprd.powersavemodelauncher - SecurityException, privileged system app

### Launcher Replacement

The default Microsoft Launcher is heavy for 1GB RAM (~38MB PSS). Two options:

**Option A: Murine Launcher** (recommended for most users) — A lightweight
Launcher3 fork, looks and behaves exactly like standard Android home screen
with app grid + drawer. No confusing minimalism:

  # Install Murine Launcher (7MB APK from F-Droid)
  adb install /tmp/murine.apk
  # Set as default home
  adb shell am start -a android.intent.action.MAIN -c android.intent.category.HOME \
    -n app.murinelauncher/com.android.launcher3.Launcher
  # Disable Microsoft Launcher
  adb shell pm disable-user --user 0 com.microsoft.launcher

**Option B: KISS Launcher** (only for power users who like search-only) —
Text-only search bar, no app grid, no home screen icons. Most users find it
confusing ("简洁过头了不知道怎么用"). Use Murine unless the user explicitly
asks for a minimal interface.

  # Install KISS Launcher (2MB APK from F-Droid)
  adb install /tmp/kiss.apk
  # Set as default home
  adb shell am start -a android.intent.action.MAIN -c android.intent.category.HOME \
    -n fr.neamar.kiss/.MainActivity

### Upgrade Feasibility

BL unlock: Possible but high-risk. Requires modified fastboot binary from 4PDA
(Russian phone forum) with factory private key. Unlock corrupts boot partition -
ResearchDownload (Windows-only Spreadtrum flashing tool) required to revive.
No Mac alternative exists.

Custom ROM: BL unlocked + GSI flash theoretically works (Treble is enabled), but:
- 1GB RAM severely limits which GSIs can run
- arm32 GSI development is nearly dead (all modern GSIs target arm64)
- Android Go is already the lightest Android configuration
- Practical gain is marginal

Best path: ADB debloat + KISS Launcher + use as-is.

### Termux Setup

Termux 0.119.0-beta.3 installed via ADB (debug universal APK from GitHub releases).
The app needs first-launch bootstrap to download and extract base system files.
After bootstrap, access via:

  adb shell run-as com.termux ls -la /data/data/com.termux/files/

This works even without root but cannot run dynamically-linked binaries (bash,
python, apt) due to linker namespace restrictions.

## ADB kill-server Pitfall (TCP connections)

Running adb kill-server drops ALL TCP-connected devices.
  adb devices shows nothing after kill-server.
  Fix: adb connect <IP>:5555 to reconnect TCP devices.

USB devices re-appear automatically, TCP devices don't.

## ADB Network Troubleshooting

Symptom: Device detected but no internet
  adb shell ping -c 1 8.8.8.8
  connect: Network is unreachable

Causes:
- WiFi broken/unavailable on device
- USB data connected but no IP routing via host

Fix: USB Tethering (enable on phone)
1. Unlock phone screen
2. Settings > Hotspot & Tethering > USB tethering ON
3. Verify: adb shell ping -c 1 8.8.8.8 should succeed
