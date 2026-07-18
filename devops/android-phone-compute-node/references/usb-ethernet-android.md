# USB Ethernet Adapter on Android — Troubleshooting

## Context
AX88772D (ASIX AX88772A chipset, USB 2.0 10/100) on Mi8 (dipper/LOS 22.2/Android 15) for wired internet. No powered Hub available, physical USB-C port conflict (Mac ADB vs OTG ethernet).

## Key Findings

### Hardware Verification First
Always verify adapter on Mac before blaming phone:
```bash
system_profiler SPUSBDataType | grep -i "ax88\|asix\|ethernet"
# If nothing → cable dead or adapter dead
ifconfig | grep "^en"  # new enX should appear with MAC address
```

### Driver Support on Android (Mi8/LOS 22.2)
Kernel 4.9.337 has built-in support:
- `/sys/bus/usb/drivers/asix` ✅
- `/sys/bus/usb/drivers/ax88179_178a` ✅ (also covers AX88772D variant)
- `/sys/bus/usb/drivers/cdc_ether` ✅

### USB OTG Host vs Device Mode Conflict
**Critical physical constraint**: Mi8 has ONE USB-C port. If connected to Mac for ADB (device mode), it cannot simultaneously be USB host for OTG ethernet. Physical conflict — no software workaround.

**Solutions**:
1. USB-C Hub (one port → Mac + ethernet adapter)
2. WiFi instead (WiFi hardware on Mi8 — check if it's working)
3. USB network sharing from Mac (Internet Sharing) — requires Mac OS-level NAT

### Termux Input Issue
Fcitx5 (Chinese input framework) conflicts with Termux terminal input.
```bash
ime set com.android.inputmethod.latin/.LatinIME
settings put secure default_input_method com.android.inputmethod.latin/.LatinIME
```
After Termux reinstall: always set this before first use.

### Mi8-specific Route
- No built-in `en8/en9` naming — USB ethernet shows as `eth0` in `/sys/class/net/`
- If `/sys/class/net/` shows only rmnet_data* and virtual interfaces → USB device not detected
- `dmesg | grep -iE 'usb.*device\|asix\|eth' | tail -20` for detection logs
- `cat /proc/kmsg` for kernel-level USB events

### If Adapter Not Detected
1. Bad USB cable (charge-only cables have no data pins)
2. Adapter draws > 500mA → try powered USB Hub
3. USB-C OTG cable needed (USB-C female to USB-A female adapter)
4. Try different USB port on phone