---
name: kindle-jailbreak-maintenance
description: Diagnose and repair jailbroken Kindle e-ink devices — x509 certificate issues, hotfix reinstallation, browser failure, network diagnostics, and plugin installation (webbrowser.koplugin). Verified on Kindle Paperwhite 5 (firmware 5.16.2.1.1, LanguageBreak jailbreak).
---

# Kindle Jailbreak Maintenance

Diagnose and repair jailbroken Kindle devices. Covers the most common failure mode: **browser spinning but not loading pages, despite WiFi and network working**.

## Trigger

Use this skill when:
- Kindle browser opens but spins/never loads any URL
- WiFi is connected and appears to work (icon shows connected)
- Device was jailbroken with LanguageBreak, WinterBreak, or similar
- KOReader is installed but browser doesn't work
- After a hotfix update, device behaves differently
- Network diagnostics needed (ping works but browser doesn't)

## Quick Diagnosis (USB-connected to Mac)

### 1. Check Network via Diagnostic Script

Create a script on the Kindle's documents folder, have the user tap it from Library:

```bash
cat > /Volumes/Kindle/documents/net_diag.sh << 'SCRIPT'
#!/bin/sh
LOG=/mnt/us/documents/net_report.txt
echo "=== Kindle 网络诊断 ===" > $LOG
date >> $LOG
echo "" >> $LOG

echo "--- WiFi 状态 ---" >> $LOG
lipc-get-prop -s com.lab126.wifid cmState 2>/dev/null >> $LOG
echo "" >> $LOG

echo "--- IP 地址 ---" >> $LOG
ifconfig wlan0 2>/dev/null >> $LOG
echo "" >> $LOG

echo "--- 路由表 ---" >> $LOG
route -n 2>/dev/null >> $LOG
echo "" >> $LOG

echo "--- DNS ---" >> $LOG
cat /etc/resolv.conf 2>/dev/null >> $LOG
echo "" >> $LOG

echo "--- Ping 8.8.8.8 ---" >> $LOG
ping -c 2 -W 3 8.8.8.8 2>/dev/null >> $LOG
echo "" >> $LOG

echo "--- DNS 解析测试 ---" >> $LOG
nslookup example.com 2>/dev/null | grep -E "Name|Address" >> $LOG
echo "" >> $LOG

echo "--- HTTP 测试 (80端口) ---" >> $LOG
curl -s --max-time 10 http://example.com 2>/dev/null | head -3 >> $LOG
echo "" >> $LOG

echo "--- HTTPS 测试 (443端口) ---" >> $LOG
curl -s --max-time 10 https://example.com 2>/dev/null | head -3 >> $LOG
echo "" >> $LOG

echo "--- 代理设置 ---" >> $LOG
echo "http_proxy=$http_proxy" >> $LOG
echo "=== 完成 ===" >> $LOG
date >> $LOG
SCRIPT
chmod +x /Volumes/Kindle/documents/net_diag.sh
```

### 2. Read System Logs

```bash
# Find latest log backup
ls -lt /Volumes/Kindle/system/logbackup/ | head -3

# Check for x509/certificate/auth errors
gunzip -c /Volumes/Kindle/system/logbackup/*.txt.gz 2>/dev/null | \
  grep -iE "x509|certificate|JwtSigner|Request Signing|browser.*error" | tail -10
```

## Browser Not Loading — Root Cause Decision Tree

```
Kindle browser spins but doesn't load
  │
  ├─ WiFi not connected? → Connect to WiFi
  │
  ├─ Network layer (use net_diag.sh)
  │   ├─ DNS fails? → Check router DNS / captive portal
  │   ├─ Ping 8.8.8.8 fails? → Router/gateway issue
  │   └─ HTTP/HTTPS works (curl)? → Browser application issue ↓
  │
  └─ Browser application issue (network OK, browser fails)
      │
      ├─ Fresh install / never worked? → Experimental Browser is extremely
      │   limited, consider webbrowser.koplugin (see below)
      │
      └─ Used to work, now broken?
          ├─ x509/JwtSigner errors in log → Jailbreak certificate issue
          │   → Apply KindleModding Universal Hotfix 2.5.0
          │     (https://github.com/KindleModding/Hotfix/releases)
          │
          └─ No certificate errors → Browser cache/corruption
              → Settings → Browser → Clear cache/cookies
              → Restart Kindle (hold power 40s)
```

## Hotfix Reinstallation

When the device has x509 certificate issues (`JwtSigner: x509 certificate couldn't be obtained`, `Request Signing Failure`):

1. Download the universal hotfix from GitHub:
   ```bash
   curl -sL "https://github.com/KindleModding/Hotfix/releases/download/2.5.0/Update_hotfix_universal.bin" -o /tmp/Update_hotfix_universal.bin
   ```
2. Copy to Kindle root: `cp /tmp/Update_hotfix_universal.bin /Volumes/Kindle/`
3. Tell user to eject, then on Kindle:
   - Search bar → `;dsts`
   - Find "Update your Kindle" → confirm
   - Wait for progress bar (100%) → auto reboot

The universal hotfix exits demo mode and restores the Java keystore. LanguageBreak-specific hotfix is an alternative but the universal one is more reliable.

## Installing webbrowser.koplugin (KOReader Text Browser)

This is a text-based web browser plugin for KOReader that supports DuckDuckGo/Brave search, Markdown rendering, and offline saving. Far more usable than the Kindle Experimental Browser.

```bash
# Download latest release
cd /tmp
curl -sL "https://github.com/omer-faruq/webbrowser.koplugin/archive/refs/tags/v0.7.0.tar.gz" -o webbrowser.tar.gz
tar xzf webbrowser.tar.gz

# Install to Kindle
mkdir -p /Volumes/Kindle/koreader/plugins/webbrowser.koplugin/
cp -r /tmp/webbrowser.koplugin-0.7.0/* /Volumes/Kindle/koreader/plugins/webbrowser.koplugin/

# Clean up
rm -rf /tmp/webbrowser.koplugin-0.7.0/ /tmp/webbrowser.tar.gz
```

Usage: Open KOReader → Tools → Web Browser → Search or enter URL.

**If plugin doesn't appear in KOReader menu:**

1. Plugin registers via `addToMainMenu()` with `text = "Web Browser"` and `sorting_hint = "search"` — should appear in the main menu under search-related items
2. KOReader must be **fully restarted** (exit to Kindle home, then relaunch KOReader) — standby/resume does not reload plugins
3. Verify files are present with correct names:
   - `ls /Volumes/Kindle/koreader/plugins/webbrowser.koplugin/_meta.lua` — should show `fullname = "Web Browser"`
   - `ls /Volumes/Kindle/koreader/plugins/webbrowser.koplugin/main.lua` — entry point
4. Check permissions match other plugins: `ls -la /Volumes/Kindle/koreader/plugins/ | head -5`
5. The plugin loads config from `webbrowser_configuration.lua` (NOT `.sample.lua`). If only `webbrowser_configuration.sample.lua` exists, `CONFIG_MISSING=true` and plugin uses defaults — this does NOT prevent menu registration
6. On-device: fully exit KOReader, start it again, look in the top menu (gear icon) or Tools section

## KOReader SSH File Transfer

Transfer files to Kindle while KOReader is running, without exiting to USB mass storage mode. Uses KOReader's built-in SSH plugin (`SSH.koplugin`).

### One-Time Setup

```bash
# 1. Plug Kindle via USB (mass storage mode mounts at /Volumes/Kindle/)

# 2. Create authorized_keys with Mac's public key
mkdir -p /Volumes/Kindle/koreader/settings/SSH/
cat ~/.ssh/id_rsa.pub >> /Volumes/Kindle/koreader/settings/SSH/authorized_keys

# 3. Eject safely
diskutil eject /Volumes/Kindle
```

### On Kindle (KOReader)

1. Eject from Mac (USB mass storage disconnects but USBNet stays up)
2. In KOReader: **Menu → Tools → SSH → Stop** (restart the server to load new authorized_keys)
3. Then **Menu → Tools → SSH → Start**

The SSH plugin listens on port **2222** by default (configurable). Key-only auth can be enabled via the plugin settings.

### Everyday File Transfer (while KOReader is running)

Once set up, just SCP files directly to the Kindle without touching USB:

```bash
# Copy a file to Kindle documents
scp -P 2222 /path/to/book.pdf root@192.168.15.244:/mnt/us/documents/

# Copy the AI Agent book (example from this session)
scp -P 2222 /tmp/ai-agent-book.pdf root@192.168.15.244:/mnt/us/documents/深入理解AI\ Agent-李博杰.pdf
```

### Network Details

- Kindle USBNet IP: `192.168.15.244` (stable)
- Mac side: `192.168.15.1`
- SSH port: `2222` (KOReader SSH plugin default)
- Requires Kindle plugged into Mac via USB (USBNet uses USB networking)
- Ping test: `ping 192.168.15.244` (should be <1ms)

### SSH Plugin Details

- Plugin path: `koreader/plugins/SSH.koplugin/`
- Authorized keys: `koreader/settings/SSH/authorized_keys` (relative to KOReader data dir)
- Dropbear binary: `koreader/dropbear`
- The SSH server must be **restarted** after adding/updating authorized_keys (use KOReader menu: Stop → Start)
- Default port is 2222; other open ports (22, 222, 8022) are different SSH instances

## Pitfalls

- **Do NOT assume captive portal** when the user says "home WiFi, used to work". The x509 certificate issue is the primary suspect for jailbroken devices.
- **The Kindle Experimental Browser is nearly unusable for modern websites** — it's a very old WebKit. Don't waste time debugging it; offer alternatives immediately.
- **KindleModding Universal Hotfix 2.5.0** is the most reliable fix for x509 cert issues. LanguageBreak-specific hotfix may fail at 1% progress.
- **USB mount shows limited filesystem** — network config, WiFi passwords, and many system files are NOT accessible from `/Volumes/Kindle/`.
- **SCP file transfer via KOReader SSH plugin (no USBNet needed)** — KOReader has a built-in SSH plugin (`SSH.koplugin`) that runs a patched dropbear. You don't need USBNetwork installed. Set it up once, then SCP files directly without exiting KOReader. See the "KOReader SSH File Transfer" section below.
- **The net_diag.sh script** outputs to `documents/net_report.txt` that can be read when the user plugs the Kindle back in.
- **x509 certificate errors in logs do NOT mean the browser can't work** — they've been happening since the initial jailbreak. The browser may have worked despite them.
