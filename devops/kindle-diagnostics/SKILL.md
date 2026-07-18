---
name: kindle-diagnostics
description: >-
  越狱 Kindle（PW5 / LanguageBreak）的浏览器故障排查、热修复安装、KOReader 插件部署。
  覆盖有线诊断（USB 挂载读日志）、网络诊断（;dm / ;711 / 脚本跑测）、证书修复（KindleModding Hotfix）。
  另含传文件到 KOReader（Calibre / SSH 插件 / USB），与「上网」分路径。
category: devops
---

# Kindle Diagnostics

越狱 Kindle 浏览器打不开网页 / 系统证书损坏的全套排查与修复方案。
已验证机型: Kindle Paperwhite 5 (11th Gen), firmware 5.16.2.1.1, LanguageBreak 越狱。

## Trigger

- Kindle Experimental Browser 转圈/白屏/加载失败
- 用户说 "Kindle 浏览器打不开网页"
- 需要安装 KOReader 插件（如 webbrowser.koplugin）
- 越狱后 x509 证书报错 / Request Signing Failure
- **把 PDF/书传到 KOReader**（同局域网、Calibre、SSH 插件、USB）

## 排查路线

### Step 0: 确认网络能通（不要跳过）

Kindle 插 Mac → 写诊断脚本 → Kindle 上跑 → 插回读输出。

```bash
# 写入脚本到 Kindle（需先挂载）
cat > /Volumes/Kindle/documents/net_diag.sh << 'SCRIPT'
#!/bin/sh
LOG=/mnt/us/documents/net_report.txt
echo "=== 网络诊断 ===" > $LOG
date >> $LOG
echo "--- WiFi 状态 ---" >> $LOG
lipc-get-prop -s com.lab126.wifid cmState 2>/dev/null >> $LOG
echo "--- IP ---" >> $LOG
ifconfig wlan0 2>/dev/null >> $LOG
echo "--- DNS ---" >> $LOG
cat /etc/resolv.conf 2>/dev/null >> $LOG
echo "--- HTTP ---" >> $LOG
curl -s --max-time 10 http://example.com 2>/dev/null | head -3 >> $LOG
echo "--- HTTPS ---" >> $LOG
curl -s --max-time 10 https://example.com 2>/dev/null | head -3 >> $LOG
echo "--- Ping ---" >> $LOG
ping -c 2 -W 3 8.8.8.8 2>/dev/null >> $LOG
SCRIPT
# 弹出 → 用户点 diag_network.sh → 插回 → read net_report.txt
```

关键判断:
- HTTP 通 + HTTPS 通 = 网络层 100% OK，问题在 Experimental Browser 本身
- 网络通但浏览器转圈 = 浏览器软件问题，不是网络

### Step 1: 检查越狱状态

```bash
# 挂载后检查
ls /Volumes/Kindle/.demo        # 存在=仍处 demo 模式
cat /Volumes/Kindle/system/version.txt
cat /Volumes/Kindle/documents/Run\ Hotfix.run_hotfix  # 热修复版本
ls /Volumes/Kindle/mkk           # 存在=热修复后的正常状态
```

### Step 2: 系统日志分析

```bash
# 看最新日志
ls -lt /Volumes/Kindle/system/logbackup/ | head -3
# 搜索关键错误
gunzip -c /Volumes/Kindle/system/logbackup/*.txt.gz 2>/dev/null | \
  grep -iE "x509|certificate|JwtSigner|Unable to read device|Request Signing" | tail -10
```

| 错误 | 含义 |
|------|------|
| `x509 certificate couldn't be obtained` | Java keystore 证书损坏（常见于越狱后） |
| `Failed to open session with TEE: code 0xffff3024` | OP-TEE / DHAv2 证书会话失败（与 x509 同链） |
| `Unable to allocate memory for DHAv2 certificate` | 设备侧拿不到 DHAv2 证书材料 |
| `Request Signing Failure` | Amazon 设备消息签名失败 |
| `Unable to read device identifiers` | 浏览器初始化异常 |
| `getNewDeviceCredentials` 500 | Amazon 服务器返回错误（非设备端问题） |

### Step 3: 安装 KindleModding Hotfix（修复 x509 证书）

如果日志显示 x509 证书错误，安装通用热修复：

```bash
# 下载最新通用热修复
curl -sL --max-time 30 \
  "https://github.com/KindleModding/Hotfix/releases/download/2.5.0/Update_hotfix_universal.bin" \
  -o /tmp/Update_hotfix_universal.bin
cp /tmp/Update_hotfix_universal.bin /Volumes/Kindle/
```

用户操作:
1. 弹出 Kindle
2. 搜索栏输入 `;dsts` → 设置页
3. **更新你的 Kindle** → 确认
4. 进度条走完 → 自动重启

验证: `.demo` 目录消失 → `Run Hotfix.run_hotfix` 存在 → `mkk` 目录可选

**注意:** 如果 LanguageBreak 专用 hotfix 卡在 1%，强制重启后用 KindleModding 通用 hotfix 重试。

## KOReader 浏览器插件安装

KOReader 本身没有内置通用浏览器，但有社区插件:

### webbrowser.koplugin

文字浏览器，DuckDuckGo/Brave 搜索 + 本地 cre/mupdf 渲染（可选 markdown/Jina）。

```bash
# 下载
curl -sL --max-time 30 \
  "https://github.com/omer-faruq/webbrowser.koplugin/archive/refs/tags/v0.7.0.tar.gz" \
  -o /tmp/webbrowser.tar.gz
tar xzf /tmp/webbrowser.tar.gz
mkdir -p /Volumes/Kindle/koreader/plugins/webbrowser.koplugin/
cp -r /tmp/webbrowser.koplugin-0.7.0/* /Volumes/Kindle/koreader/plugins/webbrowser.koplugin/
```

**关键:** 复制配置文件（插件不会自动创建）:
```bash
cp /Volumes/Kindle/koreader/plugins/webbrowser.koplugin/webbrowser_configuration.sample.lua \
   /Volumes/Kindle/koreader/plugins/webbrowser.koplugin/webbrowser_configuration.lua
```

**默认配置（本舰队实测，2026-07-17）:**
```lua
engine = "duckduckgo",
render_type = "cre",   -- 禁止默认 markdown；r.jina.ai 常 TLS 超时
```

**双路径不要混:**
- 系统 Experimental Browser 坏 = x509/TEE（看 logbackup）
- 插件“能搜不能开” = 多半 `render_type=markdown` + Jina 不可达
- 网络 curl 全通也挡不住上面两条

**用户操作:** 完全退出 KOReader → 重新打开 → **Search 分区** → **Web Browser**（不是工具菜单）

### 插件入口位置
- `sorting_hint = "search"` → 出现在 KOReader 搜索分区（顶部菜单）
- 不是工具/齿轮菜单
- 如找不到: 去插件管理检查是否被禁用

### Mac Web Bridge（系统浏览器兜底）
- 目录：`~/kindle-bridge/proxy.py`
- 端口：优先 **8081**（8080 常被本机其他服务占用）
- Kindle 打开：`http://<Mac局域网IP>:8081`
- 详情见 `kindle-troubleshooting` / `kindle-webbrowser-plugin`

## 传文件到 KOReader（与「上网」分路径）

**目标是送书/送 PDF，不是修浏览器。** 系统 Experimental Browser 的 x509/TEE 问题**不等于**不能传文件。

### 禁止首选（本舰队已否定）
- ❌ 起 `python -m http.server` 让用户用 **Experimental Browser / KOReader 浏览器** 下载  
  用户原话（2026-07-17）：「浏览器问题 之前不是没解决么」  
  同局域网 ≠ 浏览器可用；**传文件不要再走浏览器**
- ❌ 依赖 USBNet 假在线（route 走 Docker `utun*`、无 `192.168.15.1`）上的 SSH
- ❌ 把代理 / PMTUD 当传文件根因

### 推荐路径（按「不退出 KOReader」优先）

| 优先级 | 路径 | 用户操作 | Mac 操作 | 备注 |
|--------|------|----------|----------|------|
| **1** | **Calibre 无线** | KOReader Tools → **Calibre** → Start wireless | 本机已装 `calibre`/`calibredb` 时用 GUI 或 CLI 推送 PDF | 2026.03 菜单已确认有 Calibre；不依赖浏览器 |
| **2** | **SSH.koplugin** | Settings → **Plugin management** 启用 SSH → **完全退出再开** KOReader | `scp -P 2222 file root@<kindle-ip>:/mnt/us/documents/`（端口以插件为准） | 密钥曾写 `settings/SSH/authorized_keys`；启用后 Tools 第二页才稳定出现 |
| **3** | **USB 挂盘** | 退出 KOReader → 插 USB → 拷 `documents/` | `cp` 到 `/Volumes/Kindle/documents/` → `sync` → `diskutil eject` | 最快；用户若不退出 KOReader则不可用 |
| 兜底 | Web Bridge 仅浏览 | 见上 | — | **只用于看网页**，不作为「下 12MB PDF」主路径 |

### 最短验收
1. KOReader 文件管理器 / 主列表能看到目标 PDF  
2. 点开正文（非封面转圈）  
3. 若刚拷过：完全重启 KOReader 一次再扫库

### 同局域网时的正确心智
- Mac IP 例：`192.168.0.171`  
- Kindle 与 Mac 同 WiFi **只保证 L3 可达**，**不保证** 系统浏览器 / webbrowser 插件可用  
- 先 `session_search` / 历史技能确认浏览器状态，再开口给方案（用户要求：「先去搜索你的上下文/会话历史」）

详见 `references/session-20260717-transfer-not-browser.md`。

## 已知陷阱

1. **插 Mac 后 `/Volumes/Kindle` 可能不立即出现** - 等几秒或重新插拔
2. **diskutil eject 可能超时** - 但磁盘实际已推出（用 `ls /Volumes/Kindle` 确认）
3. **Kindle 的网络脚本 `;dm` `;711` 等命令** 依赖越狱桥接（hotfix 安装后才可用）
4. **热修复卡 1%** — 强制重启（长按 40 秒）→ 换通用 hotfix 重试
5. **KOReader 插件装好后不显示** — 必须**完全退出** KOReader（回到 Kindle 主界面）再重开，只待机不行
6. **配置文件 .sample 不会自动加载** — 必须手动复制为 `.lua` 版本
7. **Experimental Browser 是真正废弃** — 不折腾原生 HTTPS。用 KOReader 插件（cre）或 Mac Web Bridge
8. **不要低估 Kindle PW5 的性能** — 1GHz + 512MB，处理纯文本渲染绰绰有余
9. **markdown/Jina 不是默认解** — 中国网络下 `r.jina.ai` 经常握手超时；默认 `render_type=cre`
10. **hotfix 后 x509 仍可能残留** — 日志继续出现 TEE/DHAv2 失败时，别反复刷同一 hotfix；改走插件/Bridge
11. **同局域网 ≠ 能用浏览器下书** — 传 PDF 走 Calibre / SSH 插件 / USB，不要起 http.server 让用户开浏览器（2026-07-17 纠正）
12. **给方案前先查历史** — 用户明确要求先 `session_search`/技能，再开口；浏览器已知坏时不要重新发明 HTTP 下载
