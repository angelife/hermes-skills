---
name: lan-ip-auto-sync
description: "Use when Mac 换网（图书馆↔家）后局域网 IP 变化，或用户说「回家了/IP 变了/服务地址全改」。自动改写 Kindle 桥/OPDS/展示 URL 与（有状态时）舰队配置中的旧 IP，并输出当前入口。"
version: 1.0.0
author: 土同学
license: MIT
metadata:
  hermes:
    tags: [kindle, lan-ip, opds, network, auto-sync]
    related_skills: [kindle-troubleshooting, kindle-diagnostics, proxy-management]
---

# 局域网 IP 自动同步（换网）

## Overview

Mac 在图书馆和家里 WiFi 的 IP 不同。凡是写死 `http://192.168.x.x:端口` 的入口（Kindle 桥、OPDS、书单、howto）都会挂。

**机制锁死：** 不靠记忆改配置，跑 `sync-lan-ip.sh`（或 launchd 每 5 分钟）自动同步。

## When to Use

- 用户说：「回家了」「到图书馆了」「IP 变了」「服务地址全改」
- OPDS / Web Bridge 突然连不上，但本机 `curl 127.0.0.1:8089/opds` 仍 200
- 新建 Kindle 相关说明里需要当前 URL

不要用于：
- 公网域名 / Tailscale 固定地址（另案）
- `192.168.15.244` USBNet（假在线，禁止当真设备 IP）

## 一键命令

```bash
# 换网后立刻同步 + 打印当前入口
~/kindle-bridge/sync-lan-ip.sh

# 只看状态
~/kindle-bridge/sync-lan-ip.sh --status

# 强制重写展示文件
~/kindle-bridge/sync-lan-ip.sh --force
```

当前入口也会写到：
- `~/kindle-bridge/CURRENT_URLS.txt`
- 状态：`~/.hermes/state/lan-ip.json`
- Kindle 挂盘时：`/Volumes/Kindle/documents/CURRENT_URLS.txt`

## 自动跑（推荐装一次）

```bash
~/kindle-bridge/install-lan-ip-watcher.sh
```

- launchd：`com.angelife.lan-ip-sync`
- 登录时 + 每 5 分钟；IP 未变几乎无操作
- 日志：`~/.hermes/logs/lan-ip-sync.log`

卸载：
```bash
launchctl bootout gui/$(id -u)/com.angelife.lan-ip-sync
rm -f ~/Library/LaunchAgents/com.angelife.lan-ip-sync.plist
```

## 会改什么 / 不改什么

| 改 | 不改 |
|----|------|
| `~/kindle-bridge/*` 展示 URL / howto | 日志、session dump |
| 挂盘时 Kindle `documents/` howto、`opds.lua`、浏览器 LocalStorage 里的旧 IP | `192.168.15.x` USBNet |
| **仅当** `lan-ip.json` 有明确 old→new 时，才改 `~/.hermes/state/*` 舰队配置里的 **old IP** | 乱把家网 `192.168.1.8` 改成馆网 IP |
| 始终写 `CURRENT_URLS.txt` + 状态文件 | 扫全盘 |

监听 `0.0.0.0` 的服务（calibre :8089、桥 :8081、书单 :8091）**不必因 IP 变而重启**。  
`proxy.py` 首页已 **动态取当前 IP** 展示。

## Agent 操作清单

用户说「回家了 / IP 变了」时：

1. 跑 `~/kindle-bridge/sync-lan-ip.sh`
2. 把输出的 OPDS / 桥地址直接给用户（纯中文、最短）
3. 若 Kindle 插着 USB：脚本会写盘；提醒用户安全弹出
4. 若 OPDS 仍失败：让用户在 KOReader OPDS 编辑条目为新 `http://IP:8089/opds`（设备端目录无法远程改时）
5. 确认 watcher 已装：`launchctl print gui/$(id -u)/com.angelife.lan-ip-sync 2>/dev/null | head`

### 舰队 IP 同步

当 Mac IP 变化时，所有 bot 的 config 都需要更新：

**受影响的服务/配置：**
- 本机 `.env` 中的 `HTTP_PROXY` / `HTTPS_PROXY`（通常是 192.168.x.x:10808）
- 金/水/火同学的 `config.yaml` 中的 `base_url`/`proxy_url`
- 金/水/火同学的 `.env` 中的 `HINDSIGHT_API_URL`/`HTTP_PROXY`

**标准流程（2026-07-18 经验）：**
1. 先确认本机新 IP：`ifconfig en0 | grep \"inet \"`
2. 搜所有硬编码旧 IP：`grep -r \"旧IP\" ~/.hermes/`
3. SSH 进火同学，更新 `~/.hermes/.env` 和 `config.yaml`
4. ADB 进金同学/水同学，更新 chroot 内的 `.env` 和 `config.yaml`
5. 统一检查 New API 端口（实际跑在 3000 不是 3001）
6. 全部改完再逐个重启 gateway

**跨子网代理方案（当设备在 192.168.1.x 而土同学在 192.168.2.x）：**
- 两个子网之间可能不对称路由（土→设备通，设备→土不通）
- 用 SSH 反向隧道从土同学到目标机器：
  ```bash
  ssh -R 10808:127.0.0.1:10808 -R 3000:127.0.0.1:3000 -R 8888:127.0.0.1:8888 -fN user@target-ip
  ```
- 目标机器的 config 改回 `127.0.0.1` 端口，全部走 SSH 隧道

**ADB reverse 刷新（金同学在 USB 上时）：**
- USB 重连后 ADB reverse 绑定丢失，需重新设置：
  ```bash
  adb -s <serial> reverse tcp:10808 tcp:10808
  adb -s <serial> reverse tcp:3000 tcp:3000
  adb -s <serial> reverse tcp:8888 tcp:8888
  ```
- 不设 reverse 直接拔线 → config 需改用公网 IP 或 cloudflared 地址

**Android 手机默认路由缺失：**
- ADB connect 成功但所有网络请求失败（curl 000, ping timeout）
- `ip route show` 无 default route → 手动加：
  ```bash
  ip route add default via <网关IP> dev <接口名>
  ```
- 走移动数据出口：`ip route add default via 10.238.171.1 dev rmnet_data4`（网关从直连路由获取）

## 相关服务端口

| 服务 | 端口 | URL 形态 |
|------|------|----------|
| Web Bridge | 8081 | `http://IP:8081/` |
| Calibre OPDS | 8089 | `http://IP:8089/opds` |
| 简易书单 | 8091 | `http://IP:8091/` |
| 五行舰桥 | 28080 | `http://IP:28080/`（建成进度+服务监管，见 `kindle-dashboard`） |

## Common Pitfalls

1. **写死 IP 进 skill 正文当唯一真相** — 正文写 `http://<当前IP>:8089/opds`，用脚本打印具体值。
2. **把舰队 192.168.1.8 当 bootstrap 全盘替换** — 只在 old→new 状态明确时改 fleet。
3. **依赖 `.local` 主机名** — Kindle 上常失败。
4. **https 桥** — 必须 http。
5. **IP 变了就乱 kill 服务** — bind 0.0.0.0 的不用重启；只有展示文件和客户端配置要改。

## Verification

```bash
~/kindle-bridge/sync-lan-ip.sh --status
cat ~/kindle-bridge/CURRENT_URLS.txt
cat ~/.hermes/state/lan-ip.json
curl -s -o /dev/null -w '%{http_code}\n' http://127.0.0.1:8089/opds
curl -s -o /dev/null -w '%{http_code}\n' http://127.0.0.1:8081/
```

## References

- `references/session-20260717-home-switch.md` — OPDS 验收 + 回家自动改 IP 的机制边界
- 相关：`kindle-troubleshooting`（OPDS/桥排障）
