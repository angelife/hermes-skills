# Xiaomi Mi6 (sagit) Touchscreen — Device Paths

## Device Info

- Device: Xiaomi Mi 6 (sagit)
- ROM: LineageOS 22.2 (Android 15)
- Touch controller: Synaptics DSX (synaptics_dsx)
- I2C address: 5-0020 (bus 5, address 0x20)
- Driver path: `/sys/devices/soc/c179000.i2c/i2c-5/5-0020/driver/` (device-level `driver/` dir, not `/sys/bus/i2c/drivers/synaptics_dsi_force/` on this ROM)
- Input device name: synaptics_dsx
- Event node: `/dev/input/event1` on this ROM (was event2 in older notes)
- `dumpsys input` device id: `Device 3` (`deviceId=3`, `EventHub Devices: [5]`)
- Sysfs of the IC: `/sys/devices/soc/c179000.i2c/i2c-5/5-0020/`

## ADB Connection

- USB serial: ca00a222
- TCP: 192.168.1.15:5555 (WiFi ADB)
- Root: available via Magisk (`su` / `su 0 -c`)

## irq_enable

**NOT available** on this device. No `irq_enable` exists under `/sys/bus/i2c/devices/5-0020/input/` or `/sys/devices/soc/c179000.i2c/i2c-5/5-0020/`. Use I2C driver unbind instead.

## Unbind command (verified 2026-07-07)

```bash
adb shell "su -c 'echo 5-0020 > /sys/devices/soc/c179000.i2c/i2c-5/5-0020/driver/unbind'"
```

This is the working path on LineageOS 22.2 (sagit). The `driver/unbind` node lives under the I2C device directory itself.

## Re-bind command

```bash
adb shell "su -c 'echo 5-0020 > /sys/devices/soc/c179000.i2c/i2c-5/5-0020/driver/bind'"
```

## Verification (verified)

```bash
# Successful unbind result:
# - dumpsys input Event Hub list: synaptics_dsx is GONE
# - getevent: No such file or directory
# - TouchStatesByDisplay shows no active touch windows
adb shell "su -c 'cat /sys/class/input/input*/name'"
# → no synaptics_dsx output

adb shell "su -c 'timeout 3 getevent /dev/input/event1'"
# → disabled / No such file or directory
```

`dumpsys input` is the authoritative post-disable check. If `synaptics_dsx` still appears under Event Hub Devices with `Enabled: true`, the unbind did not take effect.

## ADB Connection

- USB serial: ca00a222
- TCP: 192.168.1.15:5555 (WiFi ADB)
- Root: availble via Magisk (su -)

## Key files

| Path | Purpose |
|------|---------|
| `/sys/bus/i2c/drivers/synaptics_dsi_force/unbind` | Write `5-0020` to disable touch |
| `/sys/bus/i2c/drivers/synaptics_dsi_force/bind` | Write `5-0020` to re-enable touch |
| `/sys/bus/i2c/devices/5-0020/name` | Reads `dsx-i2c-force` |
| `/dev/input/event2` | Touch event node (still exists after unbind, no events) |
| `/sys/class/input/input2/name` | Reads `synaptics_dsx` (disappears after unbind) |

## irq_enable

**NOT available** on this device. `/sys/bus/i2c/devices/5-0020/input/input2/` does NOT have an `irq_enable` file. Use I2C driver unbind instead.

## Unbind command

```bash
adb shell "su -c 'echo 5-0020 > /sys/bus/i2c/drivers/synaptics_dsi_force/unbind'"
```

## Re-bind command

```bash
adb shell "su -c 'echo 5-0020 > /sys/bus/i2c/drivers/synaptics_dsi_force/bind'"
```

## Verification

```bash
# Before unbind:
adb shell "su -c 'cat /sys/class/input/input*/name'" | grep synaptics
# → synaptics_dsx

# After unbind:
adb shell "su -c 'cat /sys/class/input/input*/name'" | grep synaptics
# → (no output — device removed)

# Events test:
adb shell "su -c 'timeout 3 getevent /dev/input/event2'"
# → no output (disabled)
```

## ADB Key Recovery

If the Mi6 shows "unauthorized" after `adb kill-server`, the ADB key pair may have been regenerated. Restore the old key:

```bash
cp ~/.android_bak/adbkey ~/.android/adbkey
cp ~/.android_bak/adbkey.pub ~/.android/adbkey.pub
adb kill-server
sleep 2
adb start-server
# Verify: adb devices should show "device" instead of "unauthorized"
```

## Screen stay-on (display-only mode)

When touch is disabled, prevent the screen from going to sleep:

```bash
adb shell "su -c 'settings put global stay_on_while_plugged_in 3'"
adb shell "su -c 'input keyevent 26'"
sleep 1
adb shell "su -c 'input keyevent 26'"
adb shell "su -c 'wm dismiss-keyguard'"
```

Bitmask: 1=AC, 2=USB, 3=both. As long as the Mi6 is connected to the Mac via USB, the screen stays on.

**Brightness may be very low** (e.g. 3/255) after setting stay_on, making the screen appear off. Fix:
```bash
adb shell "su -c 'settings put system screen_brightness 120'"
```

Restore normal timeout: `settings put global stay_on_while_plugged_in 0`

## Vibrator control

### Locate vibrator sysfs

```
/sys/class/leds/vibrator/
```

Key control files:
| Path | Purpose | Typical value |
|------|---------|---------------|
| `/sys/class/leds/vibrator/vmax_mv` | Max motor voltage | 2830 (Mi6) |
| `/sys/class/leds/vibrator/brightness` | Current intensity | 0 (idle) |
| `/sys/class/leds/vibrator/state` | Current state | 0 (idle) |
| `/sys/class/leds/vibrator/duration` | Vibration duration ms | varies |

### Disable vibrator entirely

```bash
adb shell "su -c 'echo 0 > /sys/class/leds/vibrator/vmax_mv'"
```

The motor receives 0V — no software trigger can make it vibrate. Not persistent across reboots.

### Restore

```bash
adb shell "su -c 'echo 2830 > /sys/class/leds/vibrator/vmax_mv'"
```

### The "Charging started" vibration quirk

A known false positive on Mi6: when connected to USB, fluctuations in USB voltage can trigger repeated HARDWARE_FEEDBACK vibrations with `reason: Charging started`. Each vibration is a ~670ms amplitude ramp. The user hears this and may attribute it to ghost touches.

Detection — check `dumpsys vibrator` Recent vibrations for entries with `usage: HARDWARE_FEEDBACK` and `reason: Charging started`.

Fix — either stabilize the USB connection (better cable, reseat plug) or disable the vibrator via `vmax_mv=0`.

## ADB instability

The Mi6 `adbd` is fragile. Running certain commands (e.g. `cmd locksettings`, `su` heredocs) can crash `adbd`, causing the device to disappear from `adb devices` while still visible in `system_profiler SPUSBDataType`.

Recovery:
```bash
adb kill-server
sleep 2
adb start-server
# Mi6 should reappear as "device" (not "unauthorized" if ADB keys are stable)
```

**If adb kill-server alone doesn't work** — reset the Mac USB daemon to force re-enumeration:
```bash
sudo killall -STOP -c usbd
sleep 2
sudo killall -CONT -c usbd
sleep 3
adb kill-server
sleep 1
adb start-server
```

If the device shows as "unauthorized" after recovery, restore the backed-up ADB key pair:
```bash
cp ~/.android_bak/adbkey ~/.android/adbkey
cp ~/.android_bak/adbkey.pub ~/.android/adbkey.pub
adb kill-server && adb start-server
```

## Lockscreen removal

To remove the lock screen for headless/server use:
```bash
adb shell "su -c 'locksettings set-disabled true'"
adb shell "su -c 'wm dismiss-keyguard'"
```

Note: On this LineageOS build, `locksettings get-password`, `get-pattern`, `get-pin` subcommands are NOT supported.

**IMPORTANT**: Use `adb shell locksettings` (without `cmd` prefix). Running `adb shell "cmd locksettings"` crashes the Mi6's adbd daemon, causing the device to disappear from `adb devices`. Recovery requires USB transport reset (`sudo killall -STOP -c usbd` + `CONT` + `adb kill-server/start-server`).

## Other input devices

After unbinding synaptics_dsx, remaining input devices:
- qpnp_pon (power button) — event0
- gpio-keys (volume) — event3
- uinput-goodix (fingerprint) — not via event node
- Headset Jack / Button Jack — audio jack
