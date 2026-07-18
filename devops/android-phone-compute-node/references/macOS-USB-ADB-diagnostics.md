# macOS USB Diagnostics for Android ADB Connectivity

## Scenario: Phone Physically Connected, ADB Can't Find It

When a phone is plugged into the Mac via USB but `adb devices` returns nothing:

1. Check the USB tree to see if macOS recognizes the device at all:
   ```bash
   system_profiler SPUSBDataType 2>&1 | grep -A 10 "Xiaomi\|Android\|Mi \|Product ID:"
   ```

2. Look at the Product ID for the phone's entry (vendor 0x18d1 = Google Inc., which is the standard Android composite vendor):

   | Product ID | Mode | adbd Running | Can ADB Reach It? | Recovery Path |
   |------------|------|-------------|-------------------|---------------|
   | 0x4ee1 | Charging only | No | No | Change USB mode on phone (MTP/ADB). Dead-screen: fastboot+twrp to push adb_keys or use hardware buttons |
   | 0x4e41 | MTP + ADB | Yes | Should be visible | Check `adb devices` output — may show "unauthorized" if RSA key not accepted |
   | 0x4e42 | PTP + ADB | Yes | Should be visible | Same as above |
   | 0x4ee7 | ADB (dedicated) | Yes | Should be visible | Pure ADB mode, no file transfer |
   | 0x4ee8 | DM + ADB (diag) | Yes | Should be visible | Diagnostics mode with ADB |

3. If the Product ID is 0x4ee1:
   - The phone's USB controller is operating in charging-only mode
   - The Android ADB daemon (adbd) is NOT running because the USB gadget is not configured as an ADB composite
   - This is different from "unauthorized" — the device won't even appear in `adb devices`
   - Fix: On a working-screen phone, tap the USB charging notification and select "File transfer / Android Debug" or "MTP"
   - **Dead-screen tip**: If `svc usb setFunctions mtp,adb` was previously configured (or the phone always defaults to MTP+ADB), adbd may still start. But if the phone defaults to charging-only mode and you can't change it via settings, the only recovery is physical:

   ```bash
   # Enter fastboot via hardware buttons (Vol Down + Power on Xiaomi)
   # Boot TWRP (or any recovery with ADB)
   fastboot boot /path/to/twrp.img
   
   # In TWRP, ADB works without authorization:
   adb push ~/.android/adbkey.pub /data/misc/adb/adb_keys
   adb reboot
   ```
   
   After reboot, the phone remembers the public key and ADB authorization works even if the screen is still dead. See the main skill's Pitfall #22 for details.

## Multi-Device Verification

When multiple Android devices are connected (e.g., Mi6 via TCP + Mi8 via USB), always verify which device a command runs on:

```bash
# List all devices
adb devices -l

# Before running device-specific commands, confirm the serial
adb -s <serial> shell getprop ro.product.model
adb -s <serial> shell uname -a
adb -s <serial> shell getprop ro.build.version.sdk

# Common trap: checking kernel version on the wrong device
# and drawing incorrect conclusions about driver support
```

## macOS ADB Server Reset

If the ADB server on macOS gets confused after re-cabling multiple devices:

```bash
adb kill-server
sleep 2
adb start-server  # re-enumerates all USB transports
adb devices -l
```

This does NOT clear authorization — the RSA keys in `~/.android/adbkey.pub` persist.
