# Realtek USB WiFi Driver on macOS

**Source:** chris1111/Wireless-USB-Big-Sur-Adapter (GitHub)
**Latest release:** V18 (2026-07-11)
**macOS support:** Tahoe 26, Sequoia 15, Sonoma 14, Ventura 13, Monterey 12, Big Sur 11
**Chipset support:** RTL8192CU, RTL8188CU, RTL8188EU, RTL8811CU, RTL8821CU and likely other Realtek 802.11n/ac chips.

## Quick Install

```bash
# 1. Download V18 zip from GitHub
curl -L -o /tmp/usbwifi.zip \
  "https://github.com/chris1111/Wireless-USB-Big-Sur-Adapter/releases/download/V18/Wireless.USB.Big.Sur.Adapter-V18.zip"

# 2. Unzip
cd /tmp && unzip -o usbwifi.zip -d usbwifi

# 3. Install .pkg (needs admin)
sudo installer -pkg \
  "/tmp/usbwifi/Wireless USB Big Sur Adapter-V18/Wireless USB Big Sur Adapter.app/Contents/Resources/.Files/Wireless USB Big Sur Adapter.pkg" \
  -target /
# Or use GUI: osascript -e 'do shell script "installer -pkg \"...\" -target /" with administrator privileges'

# 4. Reboot to load kexts
```

## Kext Approval (macOS 15+)

After reboot, macOS blocks the Realtek kexts by default:
```
kmutil load -p /Library/Extensions/RtWlanU.kext
→ "Extension not approved to load. Please approve using System Settings."
```

**Fix:** System Settings → Privacy & Security → scroll down → click "Allow" next
to the Realtek driver entry. (May need to click the info ⓘ button first, then
find the "Allow" button at the bottom of the Security section.)

After approving, either reboot or load manually:
```bash
osascript -e 'do shell script "kmutil load -p /Library/Extensions/RtWlanU.kext" with administrator privileges'
```

## Verification

```bash
# Check if kext is loaded
kextstat | grep -i rtWlanU

# Check for new network interface
networksetup -listallhardwareports | grep -A 3 -i wifi

# Scan for networks
/System/Library/PrivateFrameworks/Apple80211.framework/Versions/Current/Resources/airport -s
```

## Known Issues

- **macOS kills Wi-Fi when USB inserted:** Built-in Broadcom Wi-Fi may disconnect.
  Re-enable via menu bar or `networksetup -setairportpower en0 on`.
- **Only one Wi-Fi active at a time:** macOS typically uses only one Wi-Fi interface.
  The USB adapter replaces built-in Wi-Fi, not adds a second connection.
- **5GHz support:** Depends on chipset. RTL8811CU supports 5GHz; RTL8188EU/CU is 2.4GHz only.
  Check `airport -s` output for channel info.
- **Built-in Wi-Fi (Broadcom) may be more reliable** than the USB Realtek adapter.
  The USB adapter is useful as a backup when built-in fails, or for testing.
