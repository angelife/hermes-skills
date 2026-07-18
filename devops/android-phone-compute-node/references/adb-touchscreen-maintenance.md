# ADB Authorization & Touchscreen Maintenance

## ADB Authorization Recovery

**Problem:** Device shows "unauthorized" or "offline" after ADB server restart, key regeneration, or host key mismatch.

**Root cause:** The ADB private key on the host (`~/.android/adbkey`) no longer matches the public key authorized on the device (`/data/misc/adb/adb_keys`).

**Recovery (software-only, no physical access):**

1. Check for a backup of the original key:
   ```
   ls -la ~/.android_bak*/adbkey
   ```

2. If backup exists, restore and restart ADB:
   ```
   cp ~/.android_bak*/adbkey ~/.android/adbkey
   cp ~/.android_bak*/adbkey.pub ~/.android/adbkey.pub
   adb kill-server && adb start-server
   ```

3. Device re-authorizes automatically — the public key on the phone still matches the restored private key.

**If no backup exists** — requires physical device access to re-accept the RSA fingerprint dialog, or push the new key via recovery-mode ADB (which skips authorization).

**Command that triggers this problem:** `adb keygen ~/.android/adbkey` silently overwrites the private key. The device shows "unauthorized" immediately.

**Prevention (run before risky ADB operations):**
```
cp -a ~/.android ~/.android_bak_$(date +%Y%m%d)
```

---

## Disable Touchscreen on Rooted Android

### Use case

Random ghost touches (乱触) rendering the phone unusable. The touch driver can be unloaded at the bus level while the phone stays running. All physical buttons (power, volume, headset) continue to work.

### Procedure

**1. Identify touch device**
```
adb shell getevent -p | grep -B 5 -i touch
adb shell cat /proc/bus/input/devices | grep -A 5 -i touch
```

**2. Locate the I2C driver path**
```
adb shell find /sys -name "*touch*" -o -name "*synaptics*" -o -name "*ft5x*" -o -name "*goodix*" 2>/dev/null
adb shell ls /sys/bus/i2c/drivers/
```

**3. Unbind the driver**
```
adb shell su -c 'echo "<i2c-addr>" > /sys/bus/i2c/drivers/<driver-name>/unbind'
```

The address is typically formatted as `<bus>-<addr>` (e.g. `5-0020` for I2C bus 5, address 0x20).

**4. Verify**
```
adb shell getevent /dev/input/event<N>   # Returns nothing or timeouts — driver detached
```

The event device file persists after unbind but stops reporting events.

### Re-enable
```
adb shell su -c 'echo "<i2c-addr>" > /sys/bus/i2c/drivers/<driver-name>/bind'
```

### Persistence

Unbind is not persistent across device reboot. For permanent disable on every boot, add the unbind command to a Magisk boot script at `/data/adb/service.d/`.

### Known device-specific identifiers

| Device | Driver | I2C addr | Input event | Notes |
|--------|--------|----------|-------------|-------|
| Xiaomi Mi 6 (sagit) | `synaptics_dsi_force` | `5-0020` | `event2` | Kernel 4.4, no `enabled` sysfs file — unbind only method |
| Xiaomi Mi 8 (dipper) | Unknown — check proc/bus/input/devices | | | |

---

## Common ADB states

| State | Meaning | Fix |
|-------|---------|-----|
| `device` | Working. Authorized and ready. | None needed |
| `unauthorized` | Device connected via USB, RSA dialog pending on screen. | Restore old key, or accept dialog on device |
| `offline` | TCP transport established but adbd not responding to handshake. | Try `adb reconnect`, `adb kill-server`, or device-side adbd restart |
| `sideload` | Device in recovery mode waiting for `adb sideload`. | Send ROM via `adb sideload <file>` |
| empty/no device | Not connected. USB unplugged or ADB daemon not running. | Check cable, `adb kill-server && adb start-server` |
