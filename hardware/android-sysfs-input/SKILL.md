---
name: android-sysfs-input
description: Manage Android input devices via sysfs — disable/enable touchscreens for headless/server use. Covers ADB device discovery, input device identification, sysfs irq_enable control, I2C driver unbinding, and staged rollout scripts.
---

# Android sysfs input device management

Use when making an Android phone headless/server-ready by disabling its touchscreen while keeping the display functional.

## Workflow

### 0. ADB Connection Troubleshooting

Before anything else, confirm ADB access:

```
adb devices -l
```

**"unauthorized" on USB** — the device received the public key but the user hasn't accepted the RSA fingerprint dialog on the phone screen.

Common cause: `adb kill-server` followed by `adb start-server` regenerated the ADB key pair. The device has the OLD public key authorized in `/data/misc/adb/adb_keys`, but the new server presents a DIFFERENT key.

Fix — restore the old key:
```bash
# Check if old keys were backed up
ls ~/.android_bak/adbkey.pub 2>/dev/null

# Restore them
cp ~/.android_bak/adbkey ~/.android/adbkey
cp ~/.android_bak/adbkey.pub ~/.android/adbkey.pub
adb kill-server
sleep 2
adb start-server
```

If no backup exists, try rapid reconnection cycles — random touches on a malfunctioning screen may accidentally hit "Allow" on the RSA dialog. If that fails, physical interaction (tap "Allow" manually) is the only path.

**"offline" on TCP** — the ADB daemon connection was established but the handshake failed. This often means the device's adbd is hung or unresponsive. Try rebooting the device or reconnecting via USB.

**Device in system_profiler/USB tree but NOT in adb devices** — the physical USB connection exists, but adbd on the device has crashed (common on Mi6 after failed su commands or cmd invocations). Standard adb kill-server + start-server may not help because the issue is on the device side.

Recovery — reset the Mac USB daemon to force the device to re-enumerate:
```bash
sudo killall -STOP -c usbd
sleep 2
sudo killall -CONT -c usbd
sleep 3
adb kill-server
sleep 1
adb start-server
# Device should now appear in adb devices
```

### 1. Find the touchscreen device

Connect via ADB (rooted device):

```
adb root
adb shell "su -c 'cat /proc/bus/input/devices | grep -i -A 5 touch'"
```

Look for "TouchScreen" or "touch_input" in the output. Note the event device (event0, event1, etc.) and the sysfs path.

For devices like Xiaomi Mi6 (synaptics_dsx), the touchscreen may show as:
```
N: Name="synaptics_dsx"
P: Phys=synaptics_dsx/touch_input
```

### 2. Try irq_enable control (method A — preferred)

```bash
adb shell "su -c 'ls -la /sys/bus/i2c/devices/*/input/input*/irq_enable'"
```

If `/sys/bus/i2c/devices/<addr>/input/input<N>/irq_enable` exists, the driver supports direct interrupt control via writing 0 (disable) or 1 (enable).

**Verified Mi6 (sagit, LineageOS 22.2):** `irq_enable` does NOT exist. Skip straight to method B.

### 2b. Verify via dumpsys input

The most reliable post-disable check is `dumpsys input`. After successful disable:

- `synaptics_dsx` device **disappears entirely** from the Event Hub State Devices list
- `getevent /dev/input/event<N>` returns `No such file or directory`
- `TouchStatesByDisplay` shows no active touch windows

```bash
adb shell su -c "dumpsys input" | grep -A8 synaptics
# Expected: no matches = disabled
```

If dumpsys still lists the touchscreen, the disable did not take effect.

### 3. I2C driver unbind (method B — fallback when no irq_enable)

When `irq_enable` does NOT exist, disable the touchscreen by unbinding its I2C driver. This removes the input device from the system entirely.

**Find the driver:**
```
adb shell su -c "
# Find the touch driver in sysfs
find /sys -name 'synaptics*' -type d 2>/dev/null | head -10
# Identify the I2C address
ls /sys/bus/i2c/devices/
# Read each device name to find the touch one
cat /sys/bus/i2c/devices/*/name 2>/dev/null
"
```

Look for the driver directory like `/sys/bus/i2c/drivers/synaptics_dsi_force` and the device address like `5-0020`.

**Unbind the driver:**
```
adb shell su -c "echo '5-0020' > /sys/bus/i2c/drivers/synaptics_dsi_force/unbind"
```

**Verify touch is disabled:**
```
adb shell su -c "
# synaptics_dsx should no longer appear in input list
cat /sys/class/input/input*/name
# No events on the device
timeout 3 getevent /dev/input/event<N> || echo 'disabled'
"
```

**Re-bind when needed:**
```
adb shell su -c "echo '5-0020' > /sys/bus/i2c/drivers/synaptics_dsi_force/bind"
```

### 4. Create management scripts (staged rollout — user preference)

Place scripts at `/data/local/tmp/`:

**disable-touch.sh:**
```bash
#!/system/bin/sh
# Try irq_enable first (method A)
IRQ_FILE=$(find /sys -name irq_enable 2>/dev/null | head -1)
if [ -n "$IRQ_FILE" ]; then
  echo 0 > "$IRQ_FILE" 2>/dev/null
  echo "Disabled via irq_enable: $IRQ_FILE"
  exit 0
fi

# Fallback: I2C driver unbind (method B)
TOUCH_ADDR=$(cat /sys/bus/i2c/devices/*/name 2>/dev/null | grep -l 'dsx\|touch\|synaptics' 2>/dev/null | head -1 | xargs dirname 2>/dev/null | xargs basename 2>/dev/null)
DRIVER_PATH=$(find /sys/bus/i2c/drivers -name '*synaptics*' -type d 2>/dev/null | head -1)
if [ -n "$TOUCH_ADDR" ] && [ -n "$DRIVER_PATH" ]; then
  echo "$TOUCH_ADDR" > "$DRIVER_PATH"/unbind 2>/dev/null
  echo "Disabled via driver unbind: $DRIVER_PATH/$TOUCH_ADDR"
  exit 0
fi

echo "ERROR: no touchscreen control method found"
exit 1
```

**enable-touch.sh:**
```
#!/system/bin/sh
IRQ_FILE=$(find /sys -name irq_enable 2>/dev/null | head -1)
if [ -n "$IRQ_FILE" ]; then
  echo 1 > "$IRQ_FILE" 2>/dev/null
  exit 0
fi
TOUCH_ADDR=$(cat /sys/bus/i2c/devices/*/name 2>/dev/null | grep -l 'dsx\|touch\|synaptics' 2>/dev/null | head -1 | xargs dirname 2>/dev/null | xargs basename 2>/dev/null)
DRIVER_PATH=$(find /sys/bus/i2c/drivers -name '*synaptics*' -type d 2>/dev/null | head -1)
if [ -n "$TOUCH_ADDR" ] && [ -n "$DRIVER_PATH" ]; then
  echo "$TOUCH_ADDR" > "$DRIVER_PATH"/bind 2>/dev/null
  exit 0
fi
echo "ERROR: no touchscreen control method found"
exit 1
```

Set permissions:
```bash
adb shell "su -c 'chmod 755 /data/local/tmp/*.sh'"
```

### 5. Staged rollout (DO NOT skip)

1. Manual test: `adb shell "su -c 'sh /data/local/tmp/disable-touch.sh'"` → verify no touch events with `getevent`
2. Observe 1-2 days without auto-boot
3. Only then add to boot-time execution (Magisk service.sh or init.d)

### 6. Verify touch is disabled

For method A (irq_enable):
```
adb shell "su -c 'echo 0 > /sys/bus/i2c/devices/<addr>/input/input<N>/irq_enable'"
adb shell "su -c 'timeout 3 getevent /dev/input/event<N>'"
adb shell "su -c 'echo 1 > /sys/bus/i2c/devices/<addr>/input/input<N>/irq_enable'"
```

For method B (I2C unbind):
```
adb shell su -c "echo '<i2c-addr>' > /sys/bus/i2c/drivers/<driver-name>/unbind"
# Verify: synaptics_dsx no longer in input list
```

If `getevent` shows no events after disable (compared to ghost touches before), the disable worked.

## Device-specific paths

See `references/mi6-synaptics-touch.md` for Xiaomi Mi6 (LineageOS 22/sagit) specific paths and driver details.

For other devices:
- Find the driver: `find /sys -name '*touch*' -o -name '*synaptics*' -o -name '*focal*' -o -name '*goodix*' 2>/dev/null`
- Find I2C touch device: `cat /sys/bus/i2c/devices/*/name 2>/dev/null | grep -i 'touch\|dsx\|synaptics\|focal\|goodix'`
- Find input event number: `cat /sys/class/input/input*/name | grep -n 'touch\|dsx'`

### Headless Hermes-on-Termux: post-install permission remediation

When Hermes (or any Python package) is installed in Termux via `adb -s <serial> shell su -c 'pip install ...'`, the resulting files end up owned by `root:root` with `700`/`755` permissions. After the install completes, **Termux (running as `u0_a188` / `u0_aXXX`) cannot execute or load them** — the dynamic linker fails with `CANNOT LINK EXECUTABLE`, `bad interpreter: Permission denied`, or `dlopen failed: library not found`.

Symptoms to recognize:
- `hermes --version` works from ADB (running as root) but `hermes` from inside Termux returns `Permission denied`
- After fixing the binary itself, `ImportError: dlopen failed: library "libssl.so.3" not found` follows
- `su -c 'su 10188 -c "hermes"'` reproduces it; without `su 10188` it works (proves it's the user context)

Standard remediation (run AFTER any `su -c pip install`):

```bash
# Termux prefix location
TP=/data/data/com.termux/files/usr
TERMUX_UID=10188  # verify with: dumpsys package com.termux | grep userId

# Recursively chown everything in Termux prefix to the Termux app user
adb -s <serial> shell su -c "
  chown -hR $TERMUX_UID:$TERMUX_UID $TP/bin
  chown -hR $TERMUX_UID:$TERMUX_UID $TP/lib
  chown -hR $TERMUX_UID:$TERMUX_UID $TP/include
  chown -hR $TERMUX_UID:$TERMUX_UID $TP/libexec
  chmod 755 $TP/bin/* $TP/lib/lib*.so* 2>/dev/null
"

# Then verify as the Termux user (NOT root):
adb -s <serial> shell su -c "su 10188 -c '/data/data/com.termux/files/usr/bin/hermes --version'"
```

Critical details:
- **`-hR` flag on the symlinks** — `chown -R` alone does NOT change the ownership of the symlink itself, only the target. Every `libssl.so -> libssl.so.3` symlink will still be `root:root` and dlopen will reject the path. Always pass `-h` (or `chown -h` for symlinks explicitly).
- **Hardcode the Termux UID in the call** rather than parsing `stat -c %u`, because Android's toybox `stat` does not support `-c %u` reliably; `stat: illegal option -- c` is the usual symptom.
- **Verify as the user, not root** — `hermes --version` from ADB succeeds even when broken, because it runs as root and bypasses the permission bits. Use `su 10188 -c "..."` to reproduce the Termux-user FailureMode.
- **Fix the run-mode env separately** — even with correct perms, `su 10188 /system/bin/sh` doesn't have Termux's PATH. Use:
  ```bash
  adb -s <serial> shell 'su 10188 -s /data/data/com.termux/files/usr/bin/bash -c "
    PATH=/data/data/com.termux/files/usr/bin:/data/data/com.termux/files/usr/bin/applets
    HOME=/data/data/com.termux/files/home
    LD_LIBRARY_PATH=/data/data/com.termux/files/usr/lib
    export PATH HOME LD_LIBRARY_PATH
    hermes --version
  "'
  ```
  Otherwise the error becomes `hermes: command not found` even after the permission fix.

This is a recurring class-of-bug — re-run the chown block any time you (or anyone) installs/upgrades a Termux package from a `su -c` context.

### Display diagnostics — is the screen actually showing content?

A common source of confusion: the OS reports `ScreenState=ON` and `Wakefulness=Awake`, but the physical display appears blank or black. Before debugging further, use the **screencap file-size heuristic**:

```bash
adb shell su -c 'screencap -p /data/local/tmp/screen_test.png'
adb pull /data/local/tmp/screen_test.png .
ls -la screen_test.png
```

| File size | Meaning |
|-----------|---------|
| ~12 KB | Screen is black/off — display panel may be powered down despite software reporting 'ON' |
| 100+ KB | Content is being rendered — use `vision_analyze` to confirm what's on screen |

If the file is ~12KB (screen appears off):
1. Send `input keyevent 26` to wake from Dozing state
2. Check brightness: `settings get system screen_brightness` — may be as low as 3/255
3. Set brightness to 120+: `settings put system screen_brightness 120`

If the file is 100KB+ but the user reports a blank screen:
- Run `vision_analyze` on the pulled screenshot to confirm what's displayed
- The phone may be showing something unexpected (lockscreen instead of app, AOD instead of full UI)

## Pitfalls

- Not all kernel/driver combos expose `irq_enable`. Synaptics `synaptics_dsi_force` driver on Mi6 does NOT have `irq_enable` — use I2C driver unbind instead.
- `chmod 000 /dev/input/event<N>` is NOT recommended — Android may reset permissions, and it breaks the input system differently.
- Termux does NOT have systemd — do NOT rely on `systemctl` or auto-restart for gateway processes.
- Do NOT create configuration profiles on Mac for Android devices. Configure each device directly.
- The user requires staged rollout: manual test first, observe 1-2 days, then consider automation.
- After I2C driver unbind, the device node `/dev/input/event<N>` still exists as a file but produces no events. This is normal.
- `adb kill-server` regenerates the ADB key pair. If the device was previously authorized with the OLD key, backup and restore `~/.android/adbkey*` before reconnecting to avoid "unauthorized" state.
- `adb shell su` heredocs can fail on some devices (Mi6/LineageOS) with exit 1/255, even when the same commands work as single `su -c 'command'` invocations. Use one-liner syntax instead.
- After I2C unbind, the input node still exists as a file but produces no events. This is normal.
- **`cmd locksettings` crashes adbd on LineageOS 22.2 (Mi6).** Running `adb shell "cmd locksettings"` returns `Can't find service: locksettings` and immediately causes the device to disappear from `adb devices`. In severe cases, the device also vanishes from the Mac USB hardware tree (`system_profiler SPUSBDataType`), requiring a Mac-side USB stack reset: `sudo killall -STOP -c usbd` + wait 2s + `sudo killall -CONT -c usbd` + `adb kill-server/start-server`. Use `adb shell locksettings` (without `cmd`) instead — it works directly without su on LineageOS.
- **Display-only mode: screen ON does not guarantee screen VISIBLE.** After `stay_on_while_plugged_in` is set, the screen may be physically OFF (Dozing state). You must explicitly wake it with `input keyevent 26` — setting `screen_brightness` has no effect when the display panel is powered off. Sequence matters: `input keyevent 26` (wake) -> `wm dismiss-keyguard` (bypass lock) -> adjust brightness if too dim.
- **`locksettings set-disabled true` does not immediately dismiss the lock screen.** On some LineageOS builds, the lockscreen is disabled at the security level (no PIN/pattern/swipe required) but the keyguard may still be visually present. Always run `wm dismiss-keyguard` after enabling this setting.
- **AMOLED panels (Mi6, Pixel, etc.) have a multi-node backlight — `lcd-backlight` alone is NOT enough.** Qualcomm AMOLED displays ignore the legacy `lcd-backlight` LED. Three nodes must all be set for the panel to emit light: `wled` (white LED driver), `lcd-backlight` (legacy sysfs), and `white` (some kernels expose this separately). If any one of these is 0, the panel appears off even when `screenState=ON`, `Wakefulness=Awake`, and `screencap` returns >100KB (the screenshot captures the framebuffer, not the actual LED state). Diagnostic:
  ```bash
  adb shell su -c 'cat /sys/class/leds/white/brightness /sys/class/leds/wled/brightness /sys/class/leds/lcd-backlight/brightness'
  # All three should be > 0 (typically wled/lcd-backlight to max_brightness ~4095, white to 255)
  ```
  Fix:
  ```bash
  adb shell su -c 'echo 4095 > /sys/class/leds/wled/brightness && echo 4095 > /sys/class/leds/lcd-backlight/brightness && echo 255 > /sys/class/leds/white/brightness'
  ```
- **Adaptive brightness (`screen_brightness_mode=1`) silently dims the display** even when `screen_brightness` is set high. On a transition Doze→Awake, the ambient light sensor can override the user-set brightness down to 3/255 within seconds, making the screen appear off. Always set `screen_brightness_mode=0` (manual) for kiosk/headless use:
  ```bash
  adb shell su -c 'settings put system screen_brightness_mode 0'
  ```
- **When the device vanishes from both `adb devices -l` AND `system_profiler SPUSBDataType`**, the USB enumeration itself has dropped. Mac-side recovery:
  ```bash
  sudo killall -STOP -c usbd; sleep 2; sudo killall -CONT -c usbd; sleep 3
  adb kill-server; sleep 1; adb start-server
  ```
  If the device still doesn't reappear, it has fully powered off — the user must physically reconnect it.

## Display-only mode (screen ON, touch OFF)

When you want the screen to stay visible but touch disabled (kiosk/dashboard mode):

### Keep screen awake

After unbinding the touch driver, the device eventually enters Dozing state (AOD) and the screen goes black. Since touch is disabled, there's no way to wake it back up except ADB.

```bash
# Keep screen on while USB/AC powered (bitmask: 1=AC, 2=USB, 3=both)
adb shell "su -c 'settings put global stay_on_while_plugged_in 3'"

# Wake screen — two keyevents may be needed from Doze state
# First press transitions Dozing→Awake; second actually powers the display ON
adb shell "su -c 'input keyevent 26'"
sleep 1
adb shell "su -c 'input keyevent 26'"

# Dismiss any lingering keyguard (lockscreen overlay from previous state)
adb shell "su -c 'wm dismiss-keyguard'"
```

Leave `stay_on_while_plugged_in=3` in effect so the screen stays on as long as the device is connected to USB (which powers it via the Mac).

### Check screen brightness

After setting `stay_on_while_plugged_in`, some devices reset brightness to a very low value (e.g. 3/255), making the screen appear off when it's actually on but nearly black. Always check and adjust:

```bash
# Check current brightness
adb shell "settings get system screen_brightness"

# If very low (e.g. 3), raise to a visible level
adb shell "settings put system screen_brightness 120"
```

### Remove lock screen

For headless/server use, disable the lock screen so the device boots directly without swipe/PIN/pattern:

```bash
adb shell locksettings set-disabled true
adb shell wm dismiss-keyguard
```

### Set foreground app

Bring a specific app (e.g. Termux) to the foreground:

```bash
adb shell am start -n com.termux/com.termux.app.TermuxActivity
```

### Disable vibration (when haptic feedback mimics ghost touches)

If the user hears vibration after touch is disabled, the source may NOT be the touchscreen. Common false positives:

- **USB Charging started loop** — The phone detects and re-detects USB charging, each time triggering a HARDWARE_FEEDBACK "Charging started" vibration (~670ms stepped ramp). This happens when the USB voltage fluctuates or the cable is loose. Log entry: `reason: Charging started` with `usage: HARDWARE_FEEDBACK` in `dumpsys vibrator`.
- **System haptic feedback** — If `haptic_feedback_enabled=1`, the system may still vibrate for reasons other than touch.

To verify the actual vibration source:
```bash
adb shell "su -c 'dumpsys vibrator'"
```
Look at the `Recent vibrations:` section — the `usage:` and `reason:` fields identify the trigger.

To disable vibration entirely at the kernel level:
```bash
# Find vibrator sysfs
adb shell "su -c 'find /sys -name \"*vibrat*\" -type d'"
# Typically at /sys/class/leds/vibrator/
# Set max voltage to 0 (disables motor at hardware level)
adb shell "su -c 'echo 0 > /sys/class/leds/vibrator/vmax_mv'"
```

Restore: `echo <original_value> > /sys/class/leds/vibrator/vmax_mv` (typically 2830mV for Mi6).

Also disable system-level haptic feedback:
```bash
adb shell "su -c 'settings put system haptic_feedback_enabled 0'"
adb shell "su -c 'settings put system vibration_on_touch_enabled 0'"
adb shell "su -c 'settings put global charging_sounds_enabled 0'"
```

## References

See `references/mi6-synaptics-touch.md` for Xiaomi Mi6 (sagit) device-specific paths and driver details.
See `references/synaptics-touchscreen.md` for generic Synaptics touchscreen paths (note: irq_enable availability varies by ROM).
