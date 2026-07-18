# Android 设备异常重启诊断指南

## Quick Diagnostic Flow

When user reports "手机异常重启" (phone randomly rebooting):

### Step 1: Check Uptime & Boot Reason
```bash
# Uptime — seconds since boot
cat /proc/uptime

# Human-readable
uptime

# Boot reason (via logcat events)
adb shell "logcat -b events -d | grep system_boot_reason"
```
Boot reason values:
- 0 = unknown
- 1 = kernel panic
- 2 = power key (long press)
- 3 = soft reboot (adb reboot)
- **4 = watchdog reset** (OS crash / power threshold exceeded → most common for abnormal reboots)
- 5 = cold boot

### Step 2: Check Battery Status
```bash
adb shell "dumpsys battery"
```
Key fields:
- `level: N` — current charge level (critical if < 10%)
- `voltage: NNNN` — in mV (Li-poly: 3.6-4.2V normal; < 3.4V = critical)
- `temperature: NNN` — in tenths of °C (290 = 29°C; > 450 = overheating)
- `Max charging current: NNNNNN` — in µA (500000 = 500mA USB slow charge; need 2000000+ for meaningful charge)
- `status: N` — 1=unknown, 2=charging, 3=discharging, 4=not charging, 5=full
- `technology: Li-poly` — battery type

**Critical indicators**:
- `level: 2` + charging at 500mA = battery won't keep up with usage
- `status: 2` but level dropping = slow charging (common via Mac USB port)

### Step 3: Check Kernel Logs
```bash
# Current kernel log
adb shell "dmesg | tail -50"

# Last kernel crash (if available)
adb shell "cat /proc/last_kmsg 2>/dev/null || cat /sys/fs/pstore/console-ramoops 2>/dev/null || echo 'no pstore/ramoops'"
```
Watch for:
- `watchdog` — hardware watchdog triggered reboot
- `panic` / `Oops` / `kernel BUG` — kernel crash
- `healthd: battery l=N` — battery health daemon readings
- `thermal_zone*/temp` — overheating

### Step 4: Check ANR / Crash Logs
```bash
# ANR logs (app not responding — can cause system to reboot)
adb shell "ls -la /data/anr/"

# Tombstones (native crashes)
adb shell "ls -la /data/tombstones/ 2>/dev/null"

# Crash logs
adb shell "logcat -b crash -d | tail -20"
```

### Step 5: Discharge History
```bash
adb shell "dumpsys batterystats | grep -A5 'Discharge step'"
```
Look for deep discharges (below 10-20%) — indicates battery degradation.

### Step 6: Charging Capability
```bash
adb shell "cat /sys/class/power_supply/usb/type 2>/dev/null"
adb shell "cat /sys/class/power_supply/usb/current_max 2>/dev/null"
```

## Common Root Causes

### 1. Battery Degradation (Most Common)
- **Symptoms**: Random reboots at 20-50% battery, sudden shutdowns, voltage drops
- **Signs**: Deep discharges in history, capacity < 80% of rated, voltage < 3.5V
- **Fix**: Replace battery. If temporarily stuck, charge with wall charger (not USB port).

### 2. Slow Charging (Common Tie-In)
- **Symptoms**: Phone plugged in but battery slowly dropping
- **Signs**: `Max charging current: 500000` (USB 2.0 limit), battery level decreasing while "charging"
- **Fix**: Use 5V/2A+ wall charger. Mac/PC USB ports only deliver 500-900mA.

### 3. Kernel Panic / Watchdog
- **Symptoms**: Random reboot, no warning, often during heavy I/O
- **Signs**: Boot reason = 4 (watchdog), panic traces in dmesg
- **Fix**: Check for bad app, overheating, or corrupted firmware. Try safe mode.

### 4. Power Button Hardware Fault
- **Symptoms**: Phone reboots when pressing certain areas, or from vibration
- **Signs**: No consistent pattern, triggered by physical handling
- **Fix**: Disable power button wake in settings, or hardware repair.

### 5. Overheating
- **Symptoms**: Reboots during gaming, video, or charging
- **Signs**: `temperature > 500` (50°C+), thermal zone throttling in dmesg
- **Fix**: Clean cooling, reduce load, avoid charging while using heavily.

## Nut3 / DT1902A (坚果3) Specific Notes

- Chipset: Snapdragon 625 (SD625)
- Android: 10 (SDK 29), Smartisan ROM
- Battery type: Li-poly, ~4000mAh rated
- Charging: USB-C, supports QC3.0
- Known issues: Battery degradation is common after 3+ years; Smartisan ROM has heavy background services
- Boot reason 4 observed → watchdog triggered by low voltage threshold

## Quick Recovery (Temporary)
If phone keeps rebooting and you need it stable immediately:
1. **Plug into wall charger** (not USB port) — need 2A+ to actually charge
2. Let it charge to 100% undisturbed (2-3 hours)
3. Disable unnecessary background services
4. If still rebooting after full charge → likely hardware (battery)