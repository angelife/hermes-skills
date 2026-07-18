# Xiaomi Mi 6 (sagit) — Android Compute Node Notes

## Device Identity

This device was originally on LineageOS 15.1 (Android 8.1), but as of Jun 22 2026 after a clean flash, it now runs LineageOS 22.2 (Android 15, build lineage_sagit-userdebug 15 BP1A.250505.005). The user also owns the device and provided hardware access in a Jun 22 session that confirmed Android 15.

## Hardware Profile (as of Jun 22 2026)

| Check | Result | Verdict |
|-------|--------|---------|
| **CPU** | Snapdragon 835 (MSM8998), 8× Kryo 280: 4×1900MHz + 4×300MHz | ✅ Ok — big cluster runs at 1.9GHz (not 2.45GHz stock) |
| **RAM** | 5,861 MB (6 GB), ~1.9 GB free, 3.76 GB available | ✅ Ample for headless compute |
| **Storage** | UFS 2.1 (NOT eMMC) — `/dev/block/sda` is non-rotational; 112 GB total; /data 108 GB, 818 MB used (99% free) | ✅ Very fast, nearly empty |
| **Partitions** | 77 partitions; `/dev/block/sd*` (UFS) used; no `/dev/block/mmcblk*` entries | ✅ UFS layout |
| **Sensors** | Accel+gyro: ICM20690 (InvenSense); Proximity: TMD2620 (ams AG) | ✅ All detected |
| **Battery** | Li-poly, 96% @ 4352mV, 35°C, ~2947 mAh remaining, health=2 (GOOD) | ✅ Healthy |
| **WiFi** | 2.4G connected: RSSI -52 dBm (excellent), 72 Mbps link speed, 2432 MHz | ✅ Strong signal |
| **Touch** | Synaptics DSX RMI4 — `spontaneous reset detected` (4 occurrences in dmesg) | ⚠️ Minor — restarts don't affect headless use |
| **Audio** | MI2S TLMM pinctrl fails (`msm_mi2s_snd_startup: MI2S TLMM pinctrl set failed with -22`) | ⚠️ Known LOS 15.1 issue, non-critical |
| **Modules** | USB Ethernet drivers NOT built-in after LOS 22.2 flash (`CONFIG_USB_RTL8152` absent in kernel 4.4.302-perf+). CONFIG count: 2463 vs 4009 on stock LOS. USB WiFi drivers **not** compiled. | ⚠️ Wired USB Ethernet needs module compilation; cannot load due to MODVERSIONS |

### Hardware Verdict

The device is in **good physical condition** for a compute node. 6 GB RAM + UFS storage is well above the minimum for Python/Hindsight workloads. The only hardware-level concerns are:

- **Synaptics spontaneous reset** — touch controller hiccups while the phone is Dozing. Not a blocker for headless operation but worth monitoring if the phone runs unattended for weeks.
- **MI2S audio errors** — cosmetic. The audio subsystem isn't used on a headless compute node.
- **No USB WiFi driver** — USB WiFi adapters (RTL8188, MT7601, etc.) will NOT work with this kernel. Stick to wired USB Ethernet via RTL8152/RTL8153 adapters.

### Session 2026-06-22: WiFi Resolution

The user initially reported WiFi as "受限连接" (captive portal / no internet). Root cause: both 2.4G and 5G bands serve DHCP from the same pool (192.168.1.x), but the 2.4G band does NOT assign a default gateway. Fix:

1. Connected to 2.4G with correct password: `cmd wifi connect-network 'PHICOMM_2.4G_C97BD8' wpa2 'q1w2e3r4'`
2. Manually added default route: `ip route add default via 192.168.1.1 dev wlan0`
3. DNS set via root: `setprop net.dns1 8.8.8.8`

After fix, phone can reach Mac (192.168.1.8) and Hindsight health endpoint.

Key lesson: **Never use placeholder `[PASSWORD]` in WiFi commands** — the phone stores it as the literal passphrase.

## Device Specs (Snapshot)

| Attribute | Value |
|-----------|-------|
| SoC | Snapdragon 835 (MSM8998) -- 4x Kryo 280 Gold @ 2.45GHz + 4x Kryo 280 Silver @ 1.9GHz |
| RAM | 5,861 MB (6 GB) |
| Storage | UFS 2.1 112 GB (108 GB usable, 99% free) |
| OS | LineageOS 22.2 (Android 15, build lineage_sagit-userdebug 15 BP1A.250505.005) |
| Kernel | 4.4.302-perf+ (Clang 19.0.1, June 2026); MODVERSIONS=y |
| WiFi | ✅ Working — 2.4G (PHICOMM_2.4G_C97BD8) and 5G (PHICOMM_5G_C97BE0) saved. 2.4G signal: RSSI -52dBm, 72Mbps link. DHCP on 2.4G does NOT assign default gateway — manual `ip route add default via 192.168.1.1` required per session |
| IP | 192.168.1.15/24 (both bands served from same DHCP pool) |
| ADB TCP | ✅ Port 5555 — root via wireless (`adb connect 192.168.1.15:5555` gives uid=0) |
| Bootloader | Unlocked (`ro.boot.verifiedbootstate=orange`) |
| Root | ✅ Magisk — `magisk su -c` functional; ADB TCP gives root natively |
| Termux | ✅ Installed (UID 10188) — Python 3.13.13 + pip 26.1.2 + requests 2.34.2 |
| Termux user DNS | ❌ Broken in `su 10188 -c` context — use root shell for network ops |
| SELinux | Enforcing |
| Hindsight reachable | ✅ `curl http://192.168.1.8:8888/health` → `{"status":"healthy","database":"connected"}` |

## Network Setup

### WiFi Credential Location

On Android 8.1 (LOS 15.1):
```bash
# No wpa_supplicant.conf on newer Android — credentials in XML
adb shell cat /data/misc/apexdata/com.android.wifi/WifiConfigStore.xml
# Look for: <string name="PreSharedKey">"REAL_PASSWORD"</string>
```

### Post-Switch DHCP Gateway Loss

When switching between saved 5G → 2.4G networks with `cmd wifi connect-network`, the phone may authenticate at WPA level but fail to receive DHCP options, leaving **no default gateway**:

```bash
# Symptom: ip route shows only local subnet, no default via
$ ip route
192.168.1.0/24 dev wlan0 proto kernel scope link src 192.168.1.15
#                                                         ^--- no default gateway

# Fix: manually add gateway
adb shell "/data/local/tmp/magisk/magisk su -c 'ip route add default via 192.168.1.1 dev wlan0'"
```

This is a temporary workaround. For permanent fix, forget the network and reconnect fresh, or toggle WiFi off/on to trigger a fresh DHCP transaction.

### Cross-Subnet Correction

**Never assume the Mac host IP from memory.** The Mac was noted as `192.168.2.106` in earlier notes, but the actual IP was `192.168.1.8` (same subnet as phone). Verify at setup time:

```bash
# On phone
adb shell ip addr show wlan0 | grep inet
# On Mac (run locally)
ifconfig | grep "inet " | grep -v 127.0.0.1
```

## Primary Stability Issues (Stock OS)

### 1. data partition mounted with `errors=panic`

```
/dev/block/sda17 on /data type ext4 (...,errors=panic,...)
```

Any filesystem error triggers immediate kernel panic + reboot. **Fix**: Clean flash — `errors=panic` is a stock-LOS-15.1 mount-option issue, not hardware.

### 2. Charger daemon triggered reboot (confirmed in pstore)

```
[   11.158280] charger: [11157] rebooting
```

Charger daemon restarts the system ~11s into boot. Mi 6 known issue.

### 3. Synaptics touchscreen spontaneous reset / WLED OVP / MI2S audio

All peripheral-level issues that don't affect headless compute-node use (audio, display, touch unused).

## Verdict for Compute Node Use

**Do NOT try to fix individual issues on stock OS.** Clean flash to latest LineageOS 22.2 — one-shot fix for ALL kernel/driver stability issues. However, the device is usable as-is for light compute workloads (Python scripts, hindsight-client, cron-like background tasks). The stability issues only manifest under heavy I/O or charger-attached scenarios.

## Running Services (as of Jun 2026)

Two Python services run as root, started via Magisk boot script (`/data/adb/service.d/hindsight_proxy.sh`):

| Service | Port | Purpose |
|---------|------|---------|
| `hindsight_proxy.py` | 8090 | Proxies HTTP requests to Mac's Hindsight server (192.168.1.8:8888). Zero dependency — uses Python stdlib `http.server` + `urllib.request`. |
| `api_server.py` | 5000 | Simple status API. Returns JSON with device info, time, uptime. Zero dependency — Python stdlib only. |

These are lightweight (15-20MB each) and survive across reboots via Magisk service.d.

## Current State (Jun 2026)

- LineageOS 22.2 nightly (2026-06-19) — up to date
- Storage: 108GB total, only 989MB used — essentially bare
- Installed: Termux + Magisk only (no GApps, no extra tools)
- Termux: Python 3.13 + pip + `hermes-venv` virtualenv. No SSH server installed, no cron.
- Leftover build artifacts in `/data/local/tmp/`: multiple RTL8153 kernel modules, module build scripts, hindsight installation packages. These can be cleaned up to reclaim ~400MB.
- Screen: Garbled/unreadable (花屏) — UI not usable but ADB/SSH work fine.
- WiFi: Working (2.4G connected). 5G also configured.

## Stability Status

This device had a clean flash from stock LOS 15.1 to LOS 22.2 on Jun 22 2026. The clean flash resolved all previous systemic issues (errors=panic, charger reboot, etc.). Currently stable with no crash history (pstore empty).

After compute node setup, verify the phone can reach the Hindsight memory server:

```bash
# From the phone (via root shell — Termux user DNS may fail)
adb shell "curl -s --connect-timeout 3 http://192.168.1.8:8888/health"
# Expected: {"status":"healthy","database":"connected"}
```

If this returns `healthy`, the phone can send/receive memories via the Hindsight API client.

## Flashing: LineageOS Clean Install (sagit)

### Step-by-step (verified Jun 22 2026)

```bash
# 1. Find latest build via LineageOS API
curl -sL https://download.lineageos.org/api/v2/devices/sagit/builds | python3 -m json.tool

# 2. Download ROM (~992MB) and recovery (~27MB) via mirror links from API
#    Use background mode — download can take 15-25 minutes at ~800KB/s
curl -L -o /tmp/lineage-sagit.zip "https://mirrorbits.lineageos.org/full/sagit/YYYYMMDD/lineage-XX.X-YYYYMMDD-nightly-sagit-signed.zip"
curl -L -o /tmp/recovery-sagit.img "https://mirrorbits.lineageos.org/full/sagit/YYYYMMDD/recovery.img"

# 3. SHA256 verify both
echo "<sha256_rom> */tmp/lineage-sagit.zip" | shasum -a256 -c
echo "<sha256_recovery> */tmp/recovery-sagit.img" | shasum -a256 -c

# 4. Flash recovery via fastboot
adb reboot bootloader
fastboot flash recovery /tmp/recovery-sagit.img

# 5. Boot into recovery
# ⚠️ `fastboot oem reboot-recovery` → returns OKAY but boots OLD OS
# ⚠️ `fastboot reboot recovery` → same issue
# ⚠️ `fastboot boot /tmp/recovery-sagit.img` → may also fail on Mi 6
# ✅ CRITICAL: Must use physical Volume UP + Power from fastboot menu
#    (fastboot shows bootloader menu — volume keys to "Recovery mode")

# 6. Recovery menu navigation (done on phone)
#    Volume keys: navigate   Power: select
#    Navigate to: "Apply update" → "Apply from ADB"
#    Screen shows "Waiting for ADB sideload connection..."

# 7. Sideload ROM
#    Device shows as "sideload" in `adb devices`
#    Use background mode (ROM is ~1GB, may exceed 600s foreground limit):
adb kill-server
sleep 2
adb devices -l  # confirm "sideload" mode
adb sideload /tmp/lineage-sagit.zip   # in background + notify_on_complete

# 8. After sideload (Total xfer: 1.00x), recovery auto-installs ROM
#    Main menu → "Reboot system now"
#    First boot: 3-5 min optimization

# 9. Post-flash: Enable Developer options + USB debugging
```

### Post-Flash: init_user0_failed — Android 8.1→15 Data Incompatibility

After sideload completes (Total xfer: 1.00x), the recovery auto-installs the ROM. When you select "Reboot system now", the phone attempts to boot the new system but may show:

```
Can't load Android system. Your data may be corrupt.
Reason: init_user0_failed
```

With two options: **Try again** (highlighted) / **Factory data reset**.

**Root cause**: The old Android 8.1 data partition format is incompatible with Android 15's user management (`init_user0_failed`). The old app data, system settings, and user profiles cannot be migrated across such a large version gap. This is NOT a failed flash — the ROM installed correctly.

**Fix**:
1. Press Power to **Try again** first — may work if it was a transient init issue
2. If it returns to the same screen, select **Factory data reset** → this wipes user data but leaves the ROM intact
3. After reset, the phone boots cleanly into LineageOS 22.2
4. Skip all setup wizards (no GApps = no Google restore), go straight to **Settings → About → tap Build Number 7×** to enable Developer Options, then enable USB debugging

**Prevention**: On the next device, wipe data (`/data`) from recovery before sideloading — saves the extra reboot. But post-flash factory reset works fine.

### Critical Pitfalls

**1. `adb keygen ~/.android/adbkey` destroys authorization** — silently overwrites the existing private key. The phone has the old public key stored. Mismatch = device shows "unauthorized".

**Recovery (no physical access needed):** If the old private key was backed up (e.g. `~/.android_bak/`), restore it:
```bash
cp ~/.android_bak/adbkey ~/.android/adbkey
cp ~/.android_bak/adbkey.pub ~/.android/adbkey.pub
adb kill-server && adb start-server && adb devices
```
The device re-authorizes immediately — the public key on the phone still matches the restored private key.

**Prevention:** Before any `adb kill-server` or `adb keygen`, back up existing keys:
```bash
cp -a ~/.android ~/.android_bak_$(date +%Y%m%d)
```
NEVER run `adb keygen` on an existing, working ADB setup without a backup.

**2. `fastboot oem reboot-recovery` is a trap on Mi 6** — returns "OKAY" but boots the OLD system (SDK 27). Always verify: `getprop ro.build.version.sdk` or `adb get-state`.

**3. Physical button combo (Volume Up + Power) is unavoidable** — No fastboot command reliably boots recovery on Mi 6. Accept it early.

**4. From ADB "unauthorized": ALL adb commands blocked** — including `adb reboot bootloader`. No software workaround.

**5. Recovery shows "unauthorized" until "Apply from ADB" is selected** — This is NORMAL. Navigate the menu, then `adb devices` shows "sideload".

**6. `adb sideload` for 1GB ROM needs background mode** — foreground timeout limit (600s) is too tight. Use `terminal(background=true, notify_on_complete=true)` with `timeout=900`.

## Touchscreen: Disable / Re-enable

When the Mi 6 screen exhibits ghost-touching (乱触) — the touch controller (`synaptics_dsx`) can be unbounded from the I2C bus via root ADB, completely disabling touch input. Physical buttons (power, volume) are unaffected.

### Disable touchscreen

```bash
adb -s <serial> shell su -c 'echo "5-0020" > /sys/bus/i2c/drivers/synaptics_dsi_force/unbind'
```

Verify: `getevent /dev/input/event2` returns no events (device still exists but driver is detached).

### Re-enable touchscreen

```bash
adb -s <serial> shell su -c 'echo "5-0020" > /sys/bus/i2c/drivers/synaptics_dsi_force/bind'
```

### Device identifiers

| Item | Value |
|------|-------|
| Touch driver | `synaptics_dsi_force` |
| I2C address | `5-0020` (bus 5, addr 0x20) |
| Input event device | `/dev/input/event2` |
| Input device name | `synaptics_dsx` |
| Sysfs path | `/sys/devices/soc/c179000.i2c/i2c-5/5-0020/synaptics_force.0` |

### Notes

- The unbind is not persistent — survives ADB restart but reset when the device reboots
- If the kernel driver supports it, also try: `echo 0 > /sys/devices/virtual/input/input2/enabled` (this file may not exist on sagit kernel 4.4)
- The event device `/dev/input/event2` persists after unbind (character device stays) but no longer reports events
