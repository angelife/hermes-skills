# Android Network Diagnosis via ADB

## When a device has no internet

### Check 1: Is there any interface with a default route?
```bash
adb shell "ip route show | grep default"
```
Expected output: `default via 192.168.x.x dev wlan0` or `default via x.x.x.x dev rmnet_data0`

If output is empty → NO default route anywhere.

### Check 2: What does the default route point to?
Common traps:
- `default dev dummy0` — dummy0 has no carrier, this is a dead end
- `default dev wlan0` — WiFi is associated but gateway unreachable (DNS broken, no signal)
- No default at all — need to configure one

### Check 3: Interface states
```bash
adb shell "ip link show | grep -E '(UP|<UP|NO-CARRIER|rndis|wlan|rmnet)'"
```
- `rndis0 NO-CARRIER` → USB tethering not enabled on phone (need user to toggle it in Settings)
- `wlan0 UP` but no default → WiFi connected but no internet
- `rmnet_data0 UP,LOWER_UP` but no default → cellular data blocked or needs USB tethering config

### Check 4: DNS
```bash
adb shell "cat /system/etc/resolv.conf"
```
If empty or missing nameserver → DNS won't work even if network is fine.

### Solutions

**USB tethering (most reliable for bridging phone↔Mac):**
1. User enables USB tethering in phone Settings (Settings → Network → USB tethering)
2. On Linux host: `rndis0` interface appears, `ip link set rndis0 up`
3. Host shares internet via `rndis0` to phone's IP range

**Cellular data (unreliable, depends on carrier/APN):**
- May need APN configuration
- May be blocked by carrier plan
- `rmnet_data*` interfaces may exist but have no default route

**WiFi:**
- Use `nmcli` or `wpa_cli` if available
- Android 15+ may block WiFi scanning via ADB shell
- Often broken by hardware issues (user stated WiFi is broken on Mi8)
