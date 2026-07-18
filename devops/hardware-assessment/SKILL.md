---
name: hardware-assessment
description: Assess hardware specs and capability for self-hosted AI workloads — Mac, ARM Linux devices (N1, 玩客云), and Android phones connected via ADB. Maps specs to what workloads (LLM, Hindsight, Hugo, etc.) each device can realistically run.
tags: [hardware, mac, android, adb, arm, device-assessment, n1, xiaomi]
---

# Hardware Assessment for Self-Hosted AI

Check what hardware the user has available and assess its capability to run specific AI workloads (LLM inference, embedding services, Hindsight, build pipelines).

## When to Use
- User asks "can I run X on this device"
- User asks about their hardware specs
- User wants to know what their devices are capable of
- User connects a new device (Android phone via ADB, etc.)
- User asks about multi-device topology planning

## Workflow

### 1. Mac Hardware Assessment

Run these commands for a complete picture:

```bash
# CPU
sysctl -n machdep.cpu.brand_string
# RAM
sysctl -n hw.memsize | awk '{printf "%d GB\n", $1/1073741824}'
# Cores
sysctl -n hw.ncpu
# Disk
df -h / | tail -1 | awk '{print $3 " 已用 / " $4 " 空余 (共" $2 ")"}'
# OS version
sw_vers -productVersion
# GPU — ALWAYS check this; Macs often have dual GPUs
system_profiler SPDisplaysDataType | grep -E "Chipset|VRAM|Graphics|GPU|Metal"
# Model name
system_profiler SPHardwareDataType | grep "Model Name" | sed 's/.*: //'
```

**⚠️ CRITICAL: Always check `SPDisplaysDataType` for discrete GPUs.**
MacBook Pros (2013–2019 especially) have dual GPUs: integrated Intel + discrete AMD Radeon. The discrete GPU may be idle/hibernating and won't show in basic CPU/memory queries. Do NOT claim "no discrete GPU" without running this check first — the user will correct you.

### 2. ARM Linux Device Assessment (N1, 玩客云, etc.)

Run directly on the device or via SSH:

```bash
cat /proc/cpuinfo | grep -E "Processor|Hardware" | head -3
cat /proc/meminfo | grep MemTotal | awk '{printf "%d MB\n", $2/1024}'
df -h / | tail -1
uname -a
lscpu 2>/dev/null || echo "lscpu not available"
free -m
```

Reference specs:

| Device | SoC | CPU | RAM | GPU | GPU for LLM? |
|--------|-----|-----|-----|-----|-------------|
| **N1 box** | Amlogic S905 | 4×Cortex-A53 @ 1.5GHz | 2GB | Mali-450 | ❌ No acceleration |
| **玩客云 ws1608** | Amlogic S805 | 4×Cortex-A5 @ 1.5GHz | 1GB | Mali-400 | ❌ No acceleration |
| **Raspberry Pi 4** | BCM2711 | 4×Cortex-A72 @ 1.8GHz | 2-8GB | VideoCore VI | ❌ |

### 3. Android Device Assessment via ADB

When the user plugs in an Android phone:

```bash
# Check authorization status first
adb devices -l
# If "unauthorized", user needs to accept RSA key prompt on phone screen

# Basic info
adb shell getprop ro.build.version.release    # Android version
adb shell uname -a                             # Kernel + arch (important: armv7l vs aarch64)
adb shell free -m | head -3                    # RAM (total, used, free)
adb shell df -h /data | tail -1                # Storage
adb shell cat /proc/cpuinfo | grep Processor   # CPU info
adb shell top -b -n 1 -o PID,%CPU,%MEM,NAME 2>/dev/null | head -15

# ARCH CHECK — critical for determining package compatibility:
adb shell uname -m                              # armv7l = 32-bit ARM, aarch64 = 64-bit ARM
adb shell getprop ro.product.cpu.abi            # e.g. armeabi-v7a or arm64-v8a
# armv7l means: no GSI upgrades, Rust Python extensions broken on Bionic, <4GB RAM max

# Storage type detection (UFS vs eMMC)
adb shell cat /sys/block/sda/queue/rotational  # 0 = UFS/SSD, 1 = rotational
adb shell cat /sys/block/mmcblk0/device/type 2>/dev/null || echo "no mmcblk (UFS device)"

# Battery depth check
adb shell dumpsys battery | grep -E 'level|temperature|voltage|technology|counter|health'

# Sensor detection
adb shell dumpsys sensorservice | grep -E 'Sensor|accel|gyro|prox|light|compass' | head -12

# Root status
adb shell su -c "id" 2>/dev/null && echo "Rooted" || echo "Not rooted"

# Check for existing Linux environment
adb shell pm list packages | grep -iE "termux|linux|debian|ubuntu|proot|busybox|servd"

# Check /data/local/tmp
adb shell ls -la /data/local/tmp/
```

Arm architecture impact on workload feasibility:

| Arch | Example devices | GSI upgrade | Rust wheels | Hermes Agent | Best use |
|------|-----------------|-------------|-------------|--------------|----------|
| arm64 (aarch64) | Mi 8, Mi 6, Pixel | Available | Bionic vs glibc issue still applies | Same pydantic-core blocker | Edge node, LLM via llama.cpp |
| arm32 (armv7l) | Qin2, 玩客云 | None available | No armv7l cp313 wheels for many | Double blocked (arch+bionic) | SSH-accessible lightweight scripts |

### Spreadtrum/Unisoc ADB Detection Pattern

Some devices (Spreadtrum/Unisoc SoCs like 多亲2/Qin 2) appear in system_profiler as "Spreadtrum Phone" but NOT in adb devices by default. USB Debugging must be enabled on the phone first. On macOS system_profiler SPUSBDataType, the Product ID tells the mode:

- 0x4001 - Charging only, USB Debugging off - not in adb devices
- 0x4002 - ADB-capable - will appear in adb devices
- 0x4ee7 (Google VID 0x18d1) - Standard ADB+MTP mode

Workflow when user says "再试试" after you report no device:
1. Ask user to enable Developer Options + USB Debugging on the phone
2. After they retry, recheck with: adb kill-server; adb start-server; adb devices -l
3. Check system_profiler for Product ID change from 0x4001 to 0x4002 or 0x4ee7
4. If still not visible, device may need replug or RSA key accept on screen

Accessing Termux environment without root (tested on Android 9 Go - 多亲2):
  adb shell run-as com.termux ls -la /data/data/com.termux/files/
Works even when adb root is blocked. Note: run-as can list/edit files but cannot run dynamically-linked Termux binaries (bash, python, apt) due to linker namespace restrictions on Android 9+.

### 4. Capability Mapping

### 4. Capability Mapping

Map device specs to common workloads:

| Workload | Min RAM | Min Disk | GPU Needed? | Notes |
|----------|---------|----------|-------------|-------|
| Hugo build machine | 128MB | 1GB | No | Any device works |
| Health watchdog (ping+alert) | 64MB | 100MB | No | Any device works |
| AdGuard Home | 256MB | 1GB | No | Needs stable network |
| Hindsight (API embed, no rerank) | 500MB | 2GB | No | N1 ✅, 玩客云 ❌ |
| Hindsight (local ONNX embed) | 2.5GB | 4GB | No | N1 ❌ (2GB too tight after OS) |
| LLM 1.5B Q4 (e.g. Qwen2.5-1.5B) | 1.5GB | 1.5GB | No (CPU slow) | N1 ⚠️ ~1-3 tok/s |
| LLM 3B Q4 (e.g. Llama-3.2-3B) | 2.5GB | 2GB | Helpful | Mi 8 ✅ ~15 tok/s CPU |
| LLM 7B Q4 (e.g. Qwen2.5-7B) | 5GB | 4GB | Helpful | Mi 8 ⚠️ ~5 tok/s CPU; Mac ✅ |
| LLM 7B Q4 + GPU partial offload | 5GB | 4GB | 2GB+ VRAM | R9 M370X ✅ partial (~10-20 layers) |
| LLM 3B + full GPU offload | 3GB | 2GB | 2GB VRAM | R9 M370X ✅ fits fully |
| Hermes Agent (direct on Android) | 500MB | 200MB | No | ❌ BLOCKED — pydantic-core needs glibc, Android uses Bionic. Pure-Python scripts OK. |
| Hermes Agent (via SSH remote node) | 64MB | 10MB | No | ✅ Phone acts as lightweight edge node, Hermes runs on host |
| Simple Python API (stdlib http.server) | 64MB | 10MB | No | ✅ Works on any device with Python — zero pip deps |
| FastAPI/Uvicorn | 128MB | 50MB | No | ✅ On arm64 Android, but ❌ on arm32 (pydantic-core blocked) |

**Hermes-on-Android class structure:** A phone can participate in a Hermes ecosystem in two roles:
- **Edge node (SSH-accessible worker)** — Pure Python scripts, curl, cron. Hermes runs on the Mac/host. Works on ANY device with Termux+SSH.
- **Full Hermes agent** — Requires pydantic-core (Rust native). Works on arm64 with glibc (Linux/desktop) but NOT on Android Termux regardless of arch, because PyPI ships only glibc wheels. arm32 is additionally blocked by memory (can't compile Rust).

### 5. Multi-Device Topology Planning

When the user has multiple devices, consider:

```
Role assignment logic:
  - Always-on low-power tasks → 玩客云 or N1 (Hugo, watchdog, AdGuard)
  - RAM-hungry services → device with most free RAM
  - LLM inference → device with GPU or most CPU cores
  - Network-critical → device with reliable Ethernet/WiFi
```

### 6. Android Device Setup via ADB (Termux)

After assessment, set up the device as a usable edge server:

```bash
# 1. Download latest Termux APK
curl -sL "https://api.github.com/repos/termux/termux-app/releases/latest" \
  | grep "browser_download_url" | grep "universal" | head -1 \
  | cut -d '"' -f 4 | xargs curl -sL -o /tmp/termux.apk

# 2. Install via ADB
adb install /tmp/termux.apk

# 3. Launch Termux (triggers bootstrap extraction)
adb shell monkey -p com.termux 1
sleep 5  # Wait for process to start

# 4. Check if Termux is running
adb shell ps | grep termux

# 5. Check if bootstrap initialized (usr/bin should exist after ~10-30s)
adb shell ls /data/data/com.termux/files/usr/bin/ 2>/dev/null | head -5
```

#### Network for WiFi-Broken Devices

If the device has no WiFi (broken or unavailable), Termux's first-launch bootstrap download will fail:

```
connect: Network is unreachable  # from ping
/data/data/com.termux/files/usr/bin/: inaccessible or not found  # bootstrap missing
```

**Solution: USB Tethering** — enable on the phone side:
- Settings → Personal Hotspot / Tethering → **USB tethering** toggle ON
- This routes the phone's network through the Mac's internet connection
- Termux bootstrap will then download and extract normally

After bootstrap completes, verify:
```bash
adb shell "/data/data/com.termux/files/usr/bin/echo 'Termux ready'"
```

#### Termux Package Setup

Once bootstrapped, update and install core tools:
```bash
adb shell "/data/data/com.termux/files/usr/bin/pkg update -y"
adb shell "/data/data/com.termux/files/usr/bin/pkg install -y curl git wget"
```

For LLM inference:
```bash
# Install proot-distro for a full Linux environment
adb shell "/data/data/com.termux/files/usr/bin/pkg install -y proot-distro"
adb shell "/data/data/com.termux/files/usr/bin/proot-distro install ubuntu"

# Or compile llama.cpp directly in Termux
adb shell "/data/data/com.termux/files/usr/bin/pkg install -y cmake make ninja"
```

> **Note on root & GPU:** Without root, OpenCL is unavailable in Termux — LLM inference is pure CPU only. If the bootloader is unlocked (common on custom ROMs), consider installing Magisk/KernelSU for root access to enable GPU offload. See **Section 7** for the full Magisk root workflow.

### 7. Rooting Android Devices via Magisk

Magisk provides systemless root for Android — patches the boot image in-place without modifying system partitions. This enables `su`, GPU acceleration in Termux (OpenCL), and system apps that require root.

**Pre-requisites:**
- **Bootloader unlocked** — required for flashing the patched boot image. Check: `fastboot getvar unlocked`
- **ADB working** — device detected and authorized (`adb devices -l` shows "device" not "unauthorized")
- **Single boot partition (no A/B slots)** — simpler workflow. Check: `ls /dev/block/bootdevice/by-name/` — if you see `boot`, not `boot_a`/`boot_b`, it's single-slot
- **Userdebug ROM** (optional but helpful) — allows `adb root` for easy root shell access. On production ROMs, work within non-root shell limitations

**Workflow:**

```bash
# 0. Environment check
adb root
adb shell "getprop ro.build.version.release && uname -a && getprop ro.build.fingerprint"
adb shell "ls /dev/block/bootdevice/by-name/boot*"  # single slot? boot or boot_a+boot_b?

# 1. Download Magisk APK (latest stable from GitHub)
curl -sL "https://api.github.com/repos/topjohnwu/Magisk/releases/latest" \
  | grep "browser_download_url" | grep -E "Magisk-.*\.apk" | head -1 \
  | cut -d '"' -f 4 | xargs curl -sL -o /tmp/magisk.apk
unzip -l /tmp/magisk.apk | head -5  # verify it's a valid zip, not HTML

# 2. Install APK on device (registers package manager entry)
adb install /tmp/magisk.apk

# 3. Extract Magisk binaries from APK
mkdir -p /tmp/magisk_extract
cd /tmp/magisk_extract
unzip -o /tmp/magisk.apk \
  lib/armeabi-v7a/libmagisk.so \
  lib/armeabi-v7a/libmagiskboot.so \
  lib/armeabi-v7a/libmagiskinit.so \
  lib/armeabi-v7a/libmagiskpolicy.so \
  lib/armeabi-v7a/libbusybox.so \
  lib/armeabi-v7a/libinit-ld.so \
  assets/stub.apk \
  assets/boot_patch.sh \
  assets/util_functions.sh
# On 64-bit devices, also extract arm64-v8a variants
unzip -o /tmp/magisk.apk \
  lib/arm64-v8a/libmagisk.so \
  lib/arm64-v8a/libmagiskboot.so \
  lib/arm64-v8a/libmagiskinit.so \
  lib/arm64-v8a/libmagiskpolicy.so \
  lib/arm64-v8a/libbusybox.so \
  lib/arm64-v8a/libinit-ld.so

# Rename and organize
cd lib/armeabi-v7a
for f in lib*.so; do mv "$f" "$(echo $f | sed 's/^lib//; s/\.so$//')"; done
cd ../../

# 4. Push binaries to device
adb shell "mkdir -p /data/local/tmp/magisk"
adb push lib/armeabi-v7a/* /data/local/tmp/magisk/
adb push assets/boot_patch.sh /data/local/tmp/magisk/
adb push assets/util_functions.sh /data/local/tmp/magisk/
adb push lib/arm64-v8a/* /data/local/tmp/magisk/ 2>/dev/null || true
adb shell "chmod 755 /data/local/tmp/magisk/*"

# 5. Dump the boot partition
adb shell "dd if=/dev/block/bootdevice/by-name/boot of=/data/local/tmp/boot.img bs=1M"
adb shell "ls -lh /data/local/tmp/boot.img"  # ~64MB or ~96MB

# 6. Patch the boot image (Magisk does its work)
adb shell "KEEPVERITY=false KEEPFORCEENCRYPT=false sh /data/local/tmp/magisk/boot_patch.sh /data/local/tmp/boot.img"
# Output: /data/local/tmp/new-boot.img

# 7. Flash the patched image
adb shell "dd if=/data/local/tmp/new-boot.img of=/dev/block/bootdevice/by-name/boot"
adb shell "sync"

# 8. Reboot and verify
adb reboot
adb wait-for-device  # wait for device to come back
adb root
adb shell "ps -A | grep magiskd"  # should show magisk daemon running
adb shell "/debug_ramdisk/magisk -c"  # should return version, e.g. "30.7:MAGISK:R (30700)"
adb shell "PATH=/debug_ramdisk:\$PATH su -c 'id'"  # should show uid=0(root) context=u:r:magisk:s0
```

**Verification checklist:**
- ✅ `magiskd` process running (PID typically 800–1200)
- ✅ `magisk -c` returns version string
- ✅ `su -c 'id'` shows `uid=0(root)` with `context=u:r:magisk:s0`
- ✅ Phone boots normally (no bootloop, no dm-verity warning)

**Magisk Manager App (stub APK quirk):**
- The APK from GitHub releases is a **stub** (~11MB) — the full Magisk Manager is downloaded and expanded **after** root by the daemon
- `pm list packages` will show `com.topjohnwu.magisk` registered
- **ADB launch will fail**: `am start -n com.topjohnwu.magisk/.ui.MainActivity` → "Activity class does not exist"
- **Fix:** launch from phone screen (app drawer → Magisk icon). The stub expands on first user launch
- Root works **regardless** of whether the Manager app is opened — su, magiskd, and all system-level features are active immediately after flashing

**Userdebug vs Production ROMs:**

| Aspect | Userdebug ROM | Production ROM |
|--------|---------------|----------------|
| `adb root` | ✅ Works (adbd runs as root) | ❌ Blocked |
| Shell root access | `adb root` → root shell | Need `su -c` via adb |
| `/debug_ramdisk` | Accessible via root ADB shell | Harder to reach |
| Patching | All commands via `adb shell` | Some need workarounds |

**Pitfalls & Troubleshooting:**

1. **"dd: writing: No space left"** — /data/local/tmp is usually 16-64MB. Clear old files first: `adb shell rm -rf /data/local/tmp/magisk`
2. **TWRP download failure** — official TWRP site uses anti-hotlink protection. Not needed — Magisk boot-patch is cleaner.
3. **Bootloop after flash** — if phone doesn't boot: hold Power+VolDown to enter fastboot, then `fastboot flash boot original-boot.img`. Always keep a backup of the original boot image!
4. **`su` not in PATH for non-root shells** — `/debug_ramdisk/` is root-only accessible. Normal apps need PATH override or Magisk mount propagation (requires a full boot cycle).
5. **Magisk APK mismatch** — download from `topjohnwu/Magisk` releases only, not forks.

## Reference Files

- `references/android-devices-known.md` — specific device specs (Mi 8, Honor Play, 多亲2/Qin 2, ...), ADB kill-server TCP pitfall, USB tethering troubleshooting
- `references/magisk-root-workflow.md` — full session transcript with exact commands and error modes

## Pitfalls

1. **Don't assume integrated-only graphics on Macs** — Older MacBook Pros (2013–2019) often have dual GPUs (Intel + AMD Radeon). Run `SPDisplaysDataType` before making GPU claims.
2. **Android "8GB RAM" ≠ 8GB usable** — GPU, kernel, and hardware reservations eat 1.5–2.5GB. Check `free -m` on the device.
3. **Unrooted Android = no GPU acceleration** for LLM in Termux (OpenCL unavailable without root or specialized setup).
4. **ADB "unauthorized"** — user must accept RSA key prompt on phone screen. This is normal, not a driver problem.
5. **Broken WiFi phones still usable** — USB tethering from Mac, or USB-to-Ethernet adapter, works as network backhaul.
6. **Termux bootstrap needs internet on first launch** — if the device has no network, Termux won't initialize. Enable USB tethering on the phone side before launching.
7. **N1/玩客云 eMMC is slow (read ~50MB/s)** — don't expect fast model loading. Boot from USB3 for better I/O if possible.
8. **Dual GPU Macs switch dynamically** — the discrete GPU (Radeon) may be powered off when idle. Querying GPU info when it's asleep still shows it in `SPDisplaysDataType` but it won't accelerate until woken by a workload.
9. **`adb kill-server` drops TCP connections** — USB devices re-appear automatically, but TCP-connected devices (e.g. Mi6 at 192.168.1.15:5555) are lost and must be reconnected manually with `adb connect <IP>:5555`.
10. **Device shows up in USB but not in `adb devices`** — this means USB Debugging is not enabled. The user needs to: Settings → About Phone → tap Build Number 7× → Developer Options → USB Debugging ON. Do NOT report this as "device not detected" — report it as "USB visible but ADB not enabled" to be precise.