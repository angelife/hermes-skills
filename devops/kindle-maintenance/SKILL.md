---
name: kindle-maintenance
description: >-
  Diagnose and fix Kindle (jailbroken) device issues via USB mass storage.
  Covers firmware version check, log analysis, hotfix install, network diagnostics,
  KOReader plugin management, and text-based web browser setup.
category: devops
---

# Kindle Maintenance (Jailbroken)

Diagnose, repair, and configure a jailbroken Kindle Paperwhite (or other Kindle)
via its USB mass-storage mount (`/Volumes/Kindle`). Covers the most common
post-jailbreak issues: browser not working, certificate/x509 errors, network
diagnostics, hotfix (re)installation, and KOReader plugin management.

## Trigger

Use this skill when the user reports:
- Kindle browser (Experimental Browser) won't load websites
- Kindle was jailbroken and something stopped working
- Need to install/mange KOReader or plugins
- Kindle shows certificate/SSL errors
- Need to diagnose Kindle network connectivity
- **Need to transfer books wirelessly while in KOReader** (without exiting to USB mass storage)

## Prerequisites

- Kindle connected via USB to the host machine (mounts at `/Volumes/Kindle`)
- Kindle must be jailbroken (LanguageBreak or similar) for the hotfix/plugin steps
- The host machine has `curl`, `python3`, standard macOS/Linux tools

## Step 1: Filesystem State Check

When the Kindle is plugged in, it appears as `/Volumes/Kindle/`. First get a
baseline of the system state:

```bash
# Firmware version & device info
cat /Volumes/Kindle/system/version.txt

# Jailbreak state
ls /Volumes/Kindle/jb 2>/dev/null && echo "JB file present" || echo "No jb file"
ls /Volumes/Kindle/.demo/ 2>/dev/null && echo "Demo mode ON" || echo "No demo mode"
cat /Volumes/Kindle/DONT_CHECK_BATTERY 2>/dev/null || echo "No DONT_CHECK_BATTERY"
cat /Volumes/Kindle/documents/Run\ Hotfix.run_hotfix 2>/dev/null || echo "No hotfix tracking file"

# Installed extensions / tools
ls /Volumes/Kindle/extensions/ 2>/dev/null
ls /Volumes/Kindle/koreader/ 2>/dev/null | head -10
ls /Volumes/Kindle/usr/local/bin/ 2>/dev/null | head -10  # USBNetwork check
```

## Step 2: Log Analysis

Kindle stores system logs as compressed backups:

```bash
ls -lt /Volumes/Kindle/system/logbackup/ | head -5

# Check for key errors
gunzip -c /Volumes/Kindle/system/logbackup/*.txt.gz 2>/dev/null | \
  grep -iE "x509|certificate|JwtSigner|Unable to read device|Request Signing|browser.*error" | tail -15
```

**Key error signatures:**

| Error | Meaning |
|-------|---------|
| `x509 certificate couldn't be obtained` | Java keystore / device registration broken — needs hotfix |
| `Unable to read device identifiers` | Browser NetworkManager can't initialize — linked to cert issue |
| `Request Signing Failure` | Amazon Device Messaging can't sign requests |
| `Unable to retrieve x509 certificates` | Device can't get credentials from Amazon |
| `getNewDeviceCredentials` returns HTTP 500 | Amazon's credential server error (may be transient) |

## Step 3: Network Diagnostics

Create a diagnostic script on the Kindle's documents folder via the hotfix bridge,
then have the user run it from the Kindle's Library:

```bash
# Write diagnostic script to Kindle documents
cat > /Volumes/Kindle/documents/net_diag.sh << 'SCRIPT'
#!/bin/sh
LOG=/mnt/us/documents/net_report.txt
echo "=== Kindle Network Diagnostic ===" > $LOG
date >> $LOG
echo "WiFi state:" >> $LOG
lipc-get-prop -s com.lab126.wifid cmState 2>/dev/null >> $LOG
echo "IP:" >> $LOG
ifconfig wlan0 2>/dev/null | grep "inet addr" >> $LOG
echo "Gateway:" >> $LOG
route -n 2>/dev/null | grep ^0.0.0.0 >> $LOG
echo "DNS:" >> $LOG
cat /etc/resolv.conf 2>/dev/null >> $LOG
echo "Ping 8.8.8.8:" >> $LOG
ping -c 2 -W 3 8.8.8.8 2>/dev/null >> $LOG
echo "HTTP test:" >> $LOG
curl -s --max-time 10 http://example.com 2>/dev/null | head -3 >> $LOG
echo "HTTPS test:" >> $LOG
curl -s --max-time 10 https://example.com 2>/dev/null | head -3 >> $LOG
echo "Done" >> $LOG
date >> $LOG
SCRIPT
chmod +x /Volumes/Kindle/documents/net_diag.sh
```

Then eject the Kindle, tell the user to run `net_diag.sh` from the Library (tap it),
plug back in, and read `net_report.txt`:

```bash
cat /Volumes/Kindle/documents/net_report.txt
```

**Normal results:** WiFi CONNECTED, valid IP on same subnet as local network,
PING 0% loss, HTTP/HTTPS both return HTML.

## Step 4: Install/Reinstall Hotfix

When the x509 certificate chain is broken (common with LanguageBreak jailbreak),
install the KindleModding universal hotfix:

```bash
# Download universal hotfix 2.5.0+
cd /tmp
curl -sL --max-time 30 \
  "https://github.com/KindleModding/Hotfix/releases/download/2.5.0/Update_hotfix_universal.bin" \
  -o hotfix.bin

# Copy to Kindle root
cp hotfix.bin /Volumes/Kindle/
sync
diskutil eject /Volumes/Kindle
```

Then on the Kindle:
1. Type `;dsts` in search bar
2. Select **Update your Kindle** → confirm
3. Wait for progress bar (100%) → auto reboot

## Step 5: KOReader Plugin Installation

KOReader plugins go in `/Volumes/Kindle/koreader/plugins/<name>.koplugin/`.

### webbrowser.koplugin — Text-based web browser

This is the best available browser for jailbroken Kindles. It uses DuckDuckGo
search + Jina AI Markdown conversion for text-only web browsing.

```bash
cd /tmp
curl -sL --max-time 30 \
  "https://github.com/omer-faruq/webbrowser.koplugin/archive/refs/tags/v0.7.0.tar.gz" \
  -o wb.tar.gz

tar xzf wb.tar.gz
mkdir -p /Volumes/Kindle/koreader/plugins/webbrowser.koplugin/
cp -r webbrowser.koplugin-0.7.0/* /Volumes/Kindle/koreader/plugins/webbrowser.koplugin/

# Create config file (copy from sample)
cp /Volumes/Kindle/koreader/plugins/webbrowser.koplugin/webbrowser_configuration.sample.lua \
   /Volumes/Kindle/koreader/plugins/webbrowser.koplugin/webbrowser_configuration.lua

# Set default engine to DuckDuckGo (no API key needed)
patch --replace \
  --old "engine = \"brave_api\"" \
  --new "engine = \"duckduckgo\"" \
  --path /Volumes/Kindle/koreader/plugins/webbrowser.koplugin/webbrowser_configuration.lua

sync && diskutil eject /Volumes/Kindle
```

Then on the Kindle:
1. Fully restart KOReader (exit to Kindle home, reopen)
2. Menu → **Web Browser** (under search section)
3. Type query → DuckDuckGo results → tap result → Jina AI converts to Markdown

**Note:** The plugin registers itself with `sorting_hint = "search"` so it appears
under the search/tools section of KOReader's menu, not the tools section.

## Step 6: Wireless File Transfer to KOReader (No Exit Needed)

用户明确诉求：**不想退出 KOReader 再 USB 拷盘**。优先 OPDS（2026-07-17 已验收）。
完整步骤见 `references/kooreader-wireless-transfer.md`。

### 首选：Calibre Content Server → KOReader OPDS
```bash
/Applications/calibre.app/Contents/MacOS/calibre-server \
  --port 8089 --listen-on 0.0.0.0 --enable-local-write \
  --disable-use-bonjour "/Users/macos/Calibre Library"
~/kindle-bridge/current-opds-url.sh   # 打印当前 http://<IP>:8089/opds
```
Kindle：Search → OPDS catalog → Add → `http://<当前IP>:8089/opds`（http + /opds）→ Download。

### IP 跨场所（图书馆 vs 家里）
局域网 IP 换网必变，**禁止写死**单一 IP。
- OPDS 存两条：`Mac-馆` / `Mac-家`
- 换网跑 `~/kindle-bridge/current-opds-url.sh` 再改对应目录
- 家里可路由器 DHCP 保留；**不推荐** `.local`（Kindle 常解析失败）

### OPDS 失败先分侧
Mac `curl :8089/opds`=200 但 8089 无 Kindle 来源连接 → **Kindle 没连上**（同 WiFi/地址/https/菜单），不是书库坏。

### 次选：KOReader SSH 插件（WiFi :2222）
Tools → SSH → Start → `~/kindle-bridge/push-book.sh book.epub`

### 慎用：USBNet `192.168.15.244`
先过 `kindle-troubleshooting` 四条真伪校验；假在线勿调密钥。
`scripts/deliver-to-kindle.sh` 仅真 USBNet 路径。

## Pitfalls

- **Eject before testing**: Use `diskutil eject /Volumes/Kindle` before asking
  user to unplug. If eject fails (timeout), the write cache may not have flushed
  and files won't persist. Always verify by checking the file after remount.
- **Hotfix stuck at 1%**: Try different hotfix version. LanguageBreak-specific
  hotfix (`Update_hotfix_languagebreak-*.bin`) may fail; use KindleModding
  universal hotfix instead.
- **Browser still broken after hotfix**: The Experimental Browser is a very old
  WebKit — it may simply be too old for modern HTTPS. Don't spend too long
  debugging it; switch to KOReader + webbrowser.koplugin.
- **Network tests pass (curl works) but browser doesn't**: The Kindle's Linux
  network stack works fine (curl, ping). The issue is the browser application
  itself, not connectivity.
- **webbrowser.koplugin search works but pages won't load**: Try switching
  render mode between CRE, MuPDF, and Markdown in plugin settings. Markdown
  mode uses Jina AI gateway (r.jina.ai) which may be blocked from China.
  CRE/MuPDF fetch directly — if those fail, `socket.http` SSL may be the issue.
- **USBNet 假在线**：`ping`/`nc` 通 192.168.15.244 但 `route` 走 Docker `utun*`、
  Mac 无 `192.168.15.1`、SSH 无 banner → 假目标。`scripts/deliver-to-kindle.sh`
  已拒绝 utun 路由；细节见 `kindle-troubleshooting` 与
  `references/usbnet-false-positive-docker-utun-20260717.md`（在 troubleshooting 技能下）。
- **OPDS 地址写死 IP**：图书馆/家里 IP 不同。用 `current-opds-url.sh` + 双目录「Mac-家/馆」；
  家里可 DHCP 保留。不要交付 `.local` 当 Kindle 入口。
- **calibre-server 端口**：`9090` 常被占用；实测用 **8089**。起服后 `curl /opds` 确认是 atom 目录。
- **用户不要 USB 拷盘时**：优先 OPDS，不要默认回到「退出 KOReader + 插盘」。
