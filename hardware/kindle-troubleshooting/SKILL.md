---
name: kindle-troubleshooting
description: Diagnose and fix Kindle e-reader (jailbroken or stock) issues — browser not loading pages, WiFi connectivity, jailbreak certificate corruption, system log analysis via USB mount, and captive portal workarounds
category: hardware
---

# Kindle Troubleshooting

Diagnose Kindle e-reader issues by reading system logs from the USB-mounted volume and interpreting common failure patterns. Covers both stock and jailbroken devices.

## Trigger

Use this skill when:
- User says "Kindle 浏览器打不开网页" (browser won't load pages)
- Kindle Experimental Browser shows errors but WiFi is connected
- Kindle connected to Mac via USB, need to diagnose logs
- Known-working home WiFi suddenly stops working on Kindle
- User reports jailbroken Kindle with certificate / signing errors

## Diagnostic: Accessing Kindle Logs via USB

When a Kindle is connected to a Mac via USB, it mounts as `/Volumes/Kindle/`. System logs are stored in compressed `.gz` files under:

```bash
/Volumes/Kindle/system/logbackup/log_backup_YYMMDDHHMMSS.txt.gz
```

### Quick device info
```bash
# Firmware version
cat /Volumes/Kindle/system/version.txt
# Format: Kindle 5.16.2.1.1 (409748 002)

# KOReader version (if installed) — also tells model
cat /Volumes/Kindle/koreader/version.log 2>/dev/null
# Example: "2026-06-09, 02:06:13, v2026.03, KindlePaperWhite5"

# Jailbreak detection: look for koreader/, extensions/, mrpackages/
ls -d /Volumes/Kindle/koreader /Volumes/Kindle/extensions 2>/dev/null

# Hotfix version tracking
cat /Volumes/Kindle/documents/Run\ Hotfix.run_hotfix 2>/dev/null
# Content is a version number like "2.5.0"
```

### Read network-related errors
```bash
# Most recent log
ls -t /Volumes/Kindle/system/logbackup/*.gz | head -1 | xargs gunzip -c | grep -iE "wifi|network|dns|proxy|browser|error|fail|connect|http|ssl|tls|cert|signing"

# Search for specific patterns across all logs
for f in /Volumes/Kindle/system/logbackup/*.gz; do
  gunzip -c "$f" 2>/dev/null | grep -iE "Request Signing|JwtSigner|Unable to read device|getNewDeviceCredentials" | tail -5
done
```

### Network diagnostic via shell script bridge (USB-read output pattern)

When browser won't load but ping works, use the hotfix `.sh` bridge. Create a script that saves output to a file visible over USB — user runs it, plugs back, agent reads the log. Avoids asking user to read screen output.

```bash
cat > /Volumes/Kindle/documents/net_diag.sh << 'SCRIPT'
#!/bin/sh
LOG=/mnt/us/documents/net_report.txt
echo "=== Kindle Network Diag ===" > $LOG
date >> $LOG
lipc-get-prop -s com.lab126.wifid cmState >> $LOG 2>/dev/null
ifconfig wlan0 >> $LOG 2>/dev/null
route -n >> $LOG 2>/dev/null
cat /etc/resolv.conf >> $LOG 2>/dev/null
ping -c 2 -W 3 8.8.8.8 >> $LOG 2>/dev/null
nslookup example.com >> $LOG 2>/dev/null
curl -s --max-time 10 http://example.com | head -5 >> $LOG 2>/dev/null
curl -s --max-time 10 https://example.com | head -5 >> $LOG 2>/dev/null
echo "Done" >> $LOG
echo "Done. Plug Kindle back to PC to read log."
SCRIPT
```

Key processes in logs:
- `mesquite` — The Experimental Browser process
- `wifid` — WiFi daemon (connection, scanning, DHCP)
- `ADM` — Amazon Device Messaging (signing/auth)
- `cvm` — Java VM (Kindle's app framework)
- `kpMainApp` — Kindle's home screen / launcher

## Common Error Patterns

### 1. Jailbreak Certificate Corruption (x509 / JwtSigner) — LanguageBreak

This pattern is specific to Kindles jailbroken via **LanguageBreak** (notmarek/LanguageBreak on GitHub, supports FW ≤5.16.2.1.1). The jailbreak modifies system files needed for Amazon's certificate infrastructure.

**Log signatures:**
```log
x509 certificate couldn't be obtained
UnsupportedOperationException while adding headers. Message: x509 certificate couldn't be obtained
ADM: terminate called after throwing an instance of 'std::runtime_error'
  what():  Request Signing Failure. StatusCode: 1
Unable to read device identifiers
Server returned HTTP response code: 500 for URL: https://firs-ta-g7g.amazon.com/FirsProxy/getNewDeviceCredentials
```

**Root cause:** The Kindle cannot obtain or load its x509 certificate for JWT signing. This breaks:
- Amazon device registration (ADM signing fails)
- SSL/TLS certificate validation in the browser
- Browser's NetworkManager initialization (`Unable to read device identifiers`)
- All HTTPS page loads fail even though WiFi connects successfully

**Fix sequence:**

1. **Restart the Kindle** — hold power button 40 seconds, release. Clears transient certificate cache.
2. **Sync the device** — Settings → Sync My Kindle. Forces device to contact Amazon and attempt credential renewal.
3. **Set correct date/time** — Settings → Device Options → Device Info. If time is wrong, SSL validation fails. Correction: connect to WiFi and sync.
4. **Forget and reconnect to WiFi** — forget network → reconnect. Forces fresh DHCP lease and DNS.
5. **Deregister and re-register** — Settings → My Account → Deregister → Register again. Forces device to re-obtain credentials from Amazon.
6. **Reinstall LanguageBreak Hotfix** — The LanguageBreak hotfix patches the certificate chain to coexist with the jailbreak. This is NOT installed via MRInstaller — it's a system update `.bin` file:

   **Step A — Download hotfix on Mac:**
   ```bash
   cd /tmp
   curl -sL --max-time 30 "https://github.com/notmarek/LanguageBreak/releases/download/1.0.2.1/LanguageBreak-16.11.23.tar.gz" -o LanguageBreak.tar.gz
   tar xzf LanguageBreak.tar.gz "./Update_hotfix_languagebreak-en-US.bin"
   ```
   Available language variants: `en-US`, `zh-Hans-CN`, `ja-JP`, `fr-FR`, `de-DE`.

   **Step B — Copy to Kindle root:**
   ```bash
   cp /tmp/Update_hotfix_languagebreak-en-US.bin /Volumes/Kindle/
   ```
   Then eject the Kindle (Finder → Eject).

   **Step C — Apply on Kindle:**
   1. Type `;dsts` in Kindle search bar → opens Settings page
      - If the Kindle interface is in Chinese, the menu reads "设置" (Settings)
      - Look for "更新你的 Kindle" — may be near the bottom of the list
   2. Find **Update your Kindle** (in Chinese: "更新你的 Kindle")
   3. Tap it → confirm
   4. Kindle reboots and applies the hotfix
   5. After reboot, x509 certificate chain is restored → browser should work

   **Important:** The hotfix must match the LanguageBreak jailbreak. Other jailbreaks (WinterBreak, etc.) use different hotfix files.

   **If LanguageBreak hotfix fails (stuck at 1% or "Update Error"):**

   The LanguageBreak-specific hotfix sometimes gets stuck at 1% progress when the device has OTA updates disabled (common post-jailbreak). Force-restart via 40s power button → device shows "Update Error" → returns to previous state. No data loss.

   **实测经验 (2026-07-13):** LanguageBreak hotfix 卡在 1% 超过 5 分钟不动 → 40 秒强制重启 → 显示 "更新失败" → 设备重启。**这是已知 bug，不是设备坏了。** 不要反复重试同一个 hotfix。

   **Fallback: KindleModding Universal Hotfix v2.5.0+（推荐直接使用通用 hotfix）**

   The [KindleModding Universal Hotfix](https://github.com/KindleModding/Hotfix/releases) is a comprehensive hotfix that:
   - Updates the Java keystore with KMC signing keys (valid 1970-9999)
   - Works across all jailbreak types (LanguageBreak, WinterBreak, NiLuJe)
   - Often succeeds when LanguageBreak-specific hotfix fails at 1%
   - Release 2.5.0+ (May 2026) includes the latest KMC keys
   - **实测 3.6MB 比 LanguageBreak 专用版 158KB 大得多，包含完整 Java 证书库更新**

   ```bash
   # Download universal hotfix (preferred over LanguageBreak-specific)
   cd /tmp
   curl -sL --max-time 30 "https://github.com/KindleModding/Hotfix/releases/download/2.5.0/Update_hotfix_universal.bin" -o up.bin
   # Remove any failed previous hotfix files
   rm -f /Volumes/Kindle/Update_hotfix_*.bin
   cp /tmp/up.bin /Volumes/Kindle/Update_hotfix_universal.bin
   ```
   Then apply via `;dsts` → Update your Kindle, same procedure as above.

   **Verifying universal hotfix applied:**
   - `.demo/`, `DONT_CHECK_BATTERY`, `jb` files all disappear (exited demo mode)
   - KOReader, KUAL, MRInstaller survive (jailbreak preserved)
   - `Run Hotfix.run_hotfix` version tracking file still present
   - If browser still won't load pages after hotfix: the x509 issue was likely not the sole cause → run `;711` bridge check, then `net_diag.sh` for network

   **Verifying hotfix applied successfully:**
   ```bash
   # Check these indicators on USB mount after Kindle reconnects

   # .bin file should be gone (consumed by update process)
   ls /Volumes/Kindle/Update_hotfix_*.bin 2>/dev/null || echo "Consumed ✅"

   # Demo-mode files should be gone (hotfix exits demo mode)
   ls /Volumes/Kindle/.demo/ 2>/dev/null || echo "Demo mode exited ✅"
   ls /Volumes/Kindle/DONT_CHECK_BATTERY 2>/dev/null || echo "DONT_CHECK_BATTERY removed ✅"
   ls /Volumes/Kindle/jb 2>/dev/null || echo "jb removed ✅"

   # Run Hotfix tracking file still present (jailbreak bridge survives)
   cat /Volumes/Kindle/documents/Run\\ Hotfix.run_hotfix 2>/dev/null || echo "Missing"

   # Jailbreak components should survive
   ls -d /Volumes/Kindle/koreader /Volumes/Kindle/extensions /Volumes/Kindle/libkh 2>/dev/null

   # Firmware version unchanged (hotfix doesn't modify system)
   cat /Volumes/Kindle/system/version.txt

   # Hotfix version tracking (typically still "2.5.0")
   xxd /Volumes/Kindle/documents/Run\\ Hotfix.run_hotfix
   ```

   **Jailbreak bridge health check (`;711`):**
   After the hotfix, type `;711` in the Kindle search bar. The screen corner should briefly show text confirming the bridge is alive. If nothing appears, the jailbreak's bridge component may need re-installation via MRInstaller.

   **Post-hotfix crash recovery:**
   If the hotfix installation crashes the Kindle during boot (black screen, flashing LED):
   1. Hold power button 40s to force shutdown
   2. Plug into USB charger for 30 minutes
   3. Retry the forced restart
   4. If still stuck, the hotfix .bin may have been corrupted during download — re-download and retry

### 2. Captive Portal (Library / Hotel / Café WiFi)

**Symptom:** Kindle connects to WiFi but browser can't load pages. Works on home WiFi.

**Diagnosis:** WiFi requires a login/accept page (captive portal). Kindle's Experimental Browser is too basic to render the JavaScript/redirect.

**Workarounds:**
- Point the browser to `http://example.com` or `http://1.1.1.1` — HTTP (not HTTPS) sometimes triggers the captive portal redirect
- Use a phone hotspot instead of the public WiFi
- Use Mac Internet Sharing: Mac authenticates on WiFi → creates a separate hotspot for Kindle (requires Ethernet or USB tether on Mac side)
- If Kindle is jailbroken, install USBNetwork for SSH access and route traffic through Mac's connection

### 3. Stock Kindle Browser Limitations

Kindle Experimental Browser is based on an ancient WebKit and:
- No JavaScript support
- Very limited HTTPS/SSL support
- No modern CSS
- Cannot handle complex login pages
- May fail on sites with strict TLS versions (TLS 1.3)

### Browser-vs-Network Diagnosis (critical fork)

When Kindle browser won't load pages, the most important fork is: **is the network stack working?**

Use the `net_diag.sh` bridge script (see section above) to test:

| Test passes | Test fails | Conclusion |
|------------|-----------|------------|
| ping 8.8.8.8, DNS, HTTP curl, HTTPS curl | None | **Browser problem** — OS networking is fine, Kindle's browser application is broken. Fix: Web Bridge proxy or alternative browser |
| None | ping 8.8.8.8 fails | **Network problem** — WiFi not connected, no route to internet. Fix: check WiFi connection, gateway, DHCP |
| ping OK, DNS OK | HTTP/HTTPS curl fails | **Proxy/firewall/SSL problem** — DNS works but HTTP blocked or certificate issue. Fix: check proxy settings, captive portal |

**实测经验 (2026-07-13, Kindle PW5 on wifi-5GHz library WiFi):** All OS-level networking passed (ping/DNS/HTTP/HTTPS curl all worked from the Kindle's shell) but the Kindle Experimental Browser itself spun on every URL. Conclusion was clear: browser application is broken, not the network. The Web Bridge proxy solved this.

### 4. Kindle Web Bridge Proxy (When Browser Is Fundamentally Broken)

If OS-level networking passes (ping, DNS, HTTP/HTTPS curl all work) but the Experimental Browser still spins on pages, the most practical solution is a **web-to-Kindle proxy** on a companion computer on the same WiFi.

**How it works:**
```
Kindle Browser → HTTP://Mac:8081 → Python proxy fetches page via proper SSL
                                   → strips JS/CSS/complex elements
                                   → returns minimal HTML Kindle can render
```

**Setup on Mac:**
```bash
# requests already available in fleet env; otherwise: pip3 install requests
mkdir -p ~/kindle-bridge && cd ~/kindle-bridge
# Create/update proxy.py (see references/kindle-web-bridge-proxy.md)
# Prefer PORT=8081 — 8080 is frequently occupied by local test servers/dashboards
python3 proxy.py
```

**Usage on Kindle:**
1. Experimental Browser → `http://<Mac-LAN-IP>:8081`（**禁止 https**）
2. Enter URL → tap Open
3. Proxy fetches, strips, and renders clean text

**Best for:** Wikipedia, blogs, news, documentation, text-heavy sites.
**Limitations:** Images unreliable, no interactive features, Mac must stay on same WiFi, proxy process must keep running.

**实测 (2026-07-17):** 本机 `~/kindle-bridge/proxy.py` 监听 `0.0.0.0:8081`，`/?url=http://example.com` 返回 200 且含 Example Domain。系统浏览器侧仍有 x509/TEE 日志，不依赖修复系统证书即可浏览。

**实测 (2026-07-17 下午插盘):** 插件 history 多次 `https://192.168.0.171:8081` —— 失败路径。Bridge 首页应写死 “Use HTTP only / Do NOT use https”。进程启动用 `terminal(background=true)` 跑 `python3 ~/kindle-bridge/proxy.py`，**禁止 nohup/disown/setsid**。

**用户「完全授权 / 调试到可用」插盘清单：** 盖戳 cre 配置 + HOW_TO + net_diag + authorized_keys 校验 + sync + eject + 重启 bridge + 3 步验收。不要只报「配置已是 cre」。见 `references/usb-mount-end-to-end-fix-20260717.md`。

## KOReader Browser

If KOReader is installed, it has its own basic browser that may work better than Experimental Browser for:
- OPDS catalog access
- Simple web pages
- File downloads

### webbrowser.koplugin (文字浏览器)

专为 e-ink 设计的 KOReader 插件，通过 DuckDuckGo/Brave 搜索 + Jina AI 转 Markdown 显示网页内容。v0.7.0+，作者 omer-faruq。

**安装步骤：**
```bash
# 1. 下载
curl -sL "https://github.com/omer-faruq/webbrowser.koplugin/archive/refs/tags/v0.7.0.tar.gz" -o /tmp/wb.tar.gz
tar xzf /tmp/wb.tar.gz -C /tmp/

# 2. 复制到 Kindle
mkdir -p /Volumes/Kindle/koreader/plugins/webbrowser.koplugin/
cp -r /tmp/webbrowser.koplugin-0.7.0/* /Volumes/Kindle/koreader/plugins/webbrowser.koplugin/

# 3. 创建配置文件（关键步骤！sample 文件不会被自动加载）
cp /Volumes/Kindle/koreader/plugins/webbrowser.koplugin/webbrowser_configuration.sample.lua \
   /Volumes/Kindle/koreader/plugins/webbrowser.koplugin/webbrowser_configuration.lua

# 4. 默认引擎改为 DuckDuckGo（免 API key）
# 编辑 webbrowser_configuration.lua，将 engine = "brave_api" 改为 engine = "duckduckgo"

# 5. 同步并弹出（sync 很重要，防止写入丢失）
sync && diskutil eject /Volumes/Kindle
```

**⚠️ USB 写入陷阱：** eject 中断（超时/强行拔线）会导致写入不持久。必须 `sync` + 正常 eject。如果下次挂载后发现文件不存在，就是写入没落盘。

**使用：**
1. 完全退出 KOReader → 重新打开（插件只在启动时加载）
2. 菜单路径：**Web Browser**（位于 search 分区，不是工具分区）
3. 输入关键词搜索（默认 DuckDuckGo，无需 API key）
4. 点结果 → Jina AI 转 Markdown 显示

**默认配置（强制）：**
```lua
engine = "duckduckgo",
render_type = "cre",
```

**已知限制 / 实测坑：**
- Jina AI (`r.jina.ai`) 在中国/当前家用出口常 **TLS handshake timeout**
- 搜索可用但点开结果失败 → 先查是否 `render_type=markdown`，改 `cre`，不要先折腾代理
- `markdown` 只有在 `curl https://r.jina.ai/http://example.com` 成功后才可启用
- Experimental Browser 的 x509/TEE 坏了 **与** 插件 Jina 问题是两条独立链路；网络 curl 全通也挡不住
- 额外日志签名（2026-07-17）：`Failed to open session with TEE: code 0xffff3024`、`Unable to allocate memory for DHAv2 certificate`

- `;711` — Jailbreak bridge health check. Type in search bar; text appears in screen corner if bridge is working. If nothing appears, bridge component needs re-installation.

### Jailbreak Bridge Command Reference

These commands work after LanguageBreak jailbreak + hotfix. Type in the Kindle search bar.

| Command | Function |
|---------|----------|
| `;dsts` | Open settings page (to find "Update your Kindle") |
| `;711` | Bridge health check — text appears in screen corner if bridge is alive |
| `;uzb` | Enable USB access from demo mode |
| `;demo` | Open Demo Mode config screen |
| `;enter_demo` | Re-enter demo mode (used during jailbreak process) |
| `;log mrpi` | Launch MRPI package installer (installs from `mrpackages/`) |
| `;dm` | Show device info (IP, model, firmware) |
| `;kpm` | KUAL Package Manager (if KUAL is installed) |

**Note:** Some semicolon commands (especially `;dm`) may not work after the universal hotfix since the device exits demo mode. Only `;dsts` and `;711` are guaranteed post-hotfix.

## USBNet / SSH 真伪校验（必做，先于 scp）

`ping 192.168.15.244` + `nc -z … 22 open` **不等于** 真 USBNet。Docker Desktop 的 `utun*` 会把 `192.168.15.0/24` 变成可达黑洞。

四条**全部**通过才可宣称 USBNet/SSH 可用：

```bash
# 1) Mac 侧必须有 USBNet 本端地址（常见 192.168.15.1）
ifconfig | grep -E '192\.168\.15\.'

# 2) 路由不得走 Docker/VPN utun
route get 192.168.15.244 | grep interface
# 期望：en* / bridge* / 明确 USB RNDIS
# 拒绝：utun15 等 Docker Desktop 接口

# 3) USB 身份
system_profiler SPUSBDataType | grep -iE 'Kindle|Lab126|Amazon'
ls /Volumes/Kindle 2>/dev/null   # 大容量模式；USBNet 模式可能不挂盘

# 4) SSH 必须完成 banner/kex，不能只是 TCP open
ssh -vvv -o BatchMode=yes -o ConnectTimeout=5 -i ~/.ssh/id_rsa \
  root@192.168.15.244 true 2>&1 | tail -20
# 失败签名：kex_exchange_identification: Connection closed by remote host（无 banner）
```

**失败时的正确结论：**
- 假在线 → **不要**继续调密钥/cipher；改走 `/Volumes/Kindle` 拷文件，或 WiFi + Calibre / Web Bridge `:8081`
- 真 USBNet 但密钥失败 → 再谈 `authorized_keys`
- 浏览器上网不依赖 SSH：直接 `http://<Mac-LAN-IP>:8081`

详见 `references/usbnet-false-positive-docker-utun-20260717.md`。

## 流行方案交付模板（用户说「推给3AI/按流行处理」时）

先跑 dual-path + USBNet 真伪校验，再 3AI（OpenBridge 失败则 multi-model API）。**最终对人只交付这三块，不给选项汤：**

1. **立刻上网**：`http://<Mac-LAN>:8081`（http，同 WiFi，桥进程活）
2. **插件**：`engine=duckduckgo` + `render_type=cre`（禁止 markdown/Jina）
3. **传文件（不退出 KOReader 优先）**：`calibre-server :8089` → OPDS `http://<当前IP>:8089/opds`；
   查 IP 用 `~/kindle-bridge/current-opds-url.sh`；家/馆各存一条 OPDS。USB 盘与 SSH 仅后备。

**不要做**：ssh 假在线 15.244、修系统证书、为浏览器重刷 Hotfix（marker 已在且桥可用时）、把局域网 IP 写死成永久地址。

过程与幻觉过滤：`triple-ai-nlm-synthesis` → `references/kindle-pw5-3ai-partial-channel-20260717.md`  
交付模板：`references/popular-path-3ai-delivery-20260717.md`  
无线传书/IP 漂移：`references/opds-wireless-transfer-ip-drift-20260717.md`  
服务监管/建成进度：`kindle-dashboard` → `http://<IP>:28080/`（含 OPDS/桥端口状态）

## References

- `references/kindle-log-analysis.md`: Full log analysis methodology and error taxonomy
- `references/kindle-jailbreak-cert-fix.md`: Detailed steps for fixing jailbreak certificate corruption on common Kindle models
- `references/kindle-web-bridge-proxy.md`: Full Python source for the web-to-Kindle proxy server
- `references/dual-path-browser-diagnosis-2026-07-17.md`: 2026-07-17 dual-path root cause (x509/TEE vs Jina markdown) and 8081 Web Bridge verification
- `references/usbnet-false-positive-docker-utun-20260717.md`: Docker utun 导致 192.168.15.244 假在线；SSH banner 校验四条清单
- `references/popular-path-3ai-delivery-20260717.md`: 3AI 流行方案交付模板与验收清单
- `references/usb-mount-end-to-end-fix-20260717.md`: 插盘「完全授权」端到端写盘清单 + 3 步验收
- `references/opds-wireless-transfer-ip-drift-20260717.md`: OPDS 无线传书验收路径 + 图书馆/家里 IP 漂移处理

## 已知陷阱
1. **USB 写入不持久**：`diskutil eject` 中断会导致写入丢失。写完后必须 `sync` + 正常 eject。
2. **Kindle 版本**：LanguageBreak 越狱仅支持固件 ≤5.16.2.1.1，高于此版本需要其他越狱方法（Sanctuary/WinterBreak）。
3. **先排查再让用户操作**：不要跳过诊断步骤直接让用户去试。先读日志、写诊断脚本、确认根因，再给出具体操作指令。用户明确纠正过这种跳过排查直接操作的行为。
4. **系统代理残留**：Kindle 的 macOS 系统代理设置（127.0.0.1:10808）在切换网络环境时会让 Telegram 等网络服务失效（跨技能引用）。
5. **webbrowser.koplugin 配置文件**：必须重命名为 `webbrowser_configuration.lua`（不是 .sample.lua 就能用），默认引擎 `duckduckgo`，默认渲染 **`cre`（不要默认 markdown）**。
6. **Web Bridge 端口**：优先 8081；8080 经常被占用。给用户地址时写死当前 Mac LAN IP + 端口。
7. **解释 Jina**：用户问 “jina 是啥” 时答：插件 markdown 模式用的网页转 Markdown 网关 `r.jina.ai`；被墙/超时只影响打开结果页，不证明 WiFi 坏了。
8. **会话诊断细节**：见 `references/dual-path-browser-diagnosis-2026-07-17.md`。
9. **USBNet 假在线（Docker utun）**：`ping`/`nc` 通不够；`route` 若走 `utun*` 且 Mac 无 `192.168.15.1` → 假目标。见上节。
10. **USB 上不一定是 Kindle**：可能只有 Mi8（`a6520fa3`）。没有 `/Volumes/Kindle` 就不能改插件 / 写 keys / 读 system log。
11. **Bridge 必须 http**：history 常误用 `https://<mac-ip>:8081`，会挂在证书/TEE。只交付 `http://`。
12. **完全授权不等于只检查**：插盘后配置已正确也不能停；走完整写盘清单（盖戳/HOW_TO/net_diag/keys/sync/eject/bridge）。
13. **Bridge 后台启动**：`terminal(background=true)`，禁止 nohup/disown。
14. **跨场所 IP 漂移**：图书馆/家里局域网 IP 不同。OPDS/桥地址用当前 IP；**优先** `~/kindle-bridge/sync-lan-ip.sh`（技能 `lan-ip-auto-sync`）+ 双目录「Mac-家/馆」；勿写死、勿依赖 `.local`。
15. **出厂百度书签**：中国区 Experimental Browser 书签/lastUrl 常预设百度；清 LocalStorage 书签 + lastUrl + 缓存，Bridge 放首位。
16. **OPDS「不行」先分侧**：Mac `/opds` 200 且 8089 无 Kindle 来源连接 → 修 Kindle 网/地址/菜单，不要重启 calibre。
