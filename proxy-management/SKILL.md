---
name: proxy-management
title: "代理管理 — v2rayN + OpenWrt + sing-box/xray"
description: "本机代理工具链管理：v2rayN 客户端、SOCKS5 端口 10808、出口节点切换、全局模式设置、N1 OpenWrt 路由器代理。确保 AI 工具（NotebookLM、网络搜索）始终可用。"
category: network
tags: [proxy, v2ray, v2rayn, openwrt, sing-box, xray, socks5, n1]
---

# 代理管理

## 核心工作流：NLM 中心制（2026-07-16 确立）

所有代理问题的诊断流程：

```
发现问题 → 多渠道收集信息（搜索/Grok API/OpenBridge问AI/MoA）
        ↓
    全部喂 NotebookLM（统一分析）
        ↓
    NLM 输出综合方案（共识+分歧+优先级）
        ↓
    按方案执行 → 结果存档 Obsidian
        ↓
    有问题 → 回到收集，循环
```

**不要自己做综合判断。** 把 Grok 的回复、ChatGPT 的回复、搜索到的资料、自己的日志，全部作为原始材料喂进 NLM，让它出统一方案。NLM 是商业版（已付费），放心用。

## 操作铁律（2026-07-16 用户纠正）

### 永远先读说明书再动手

v2rayN 在 GitHub 有完整文档。任何代理问题先走：

1. **读 v2rayN 文档** — github.com/2dust/v2rayN (README + Wiki)
2. **读内核文档** — sing-box (SagerNet/sing-box) / xray (xtls/xray-core)
3. **搜 GitHub Issues** — 已知问题和讨论
4. **确认出口区域** — NotebookLM 需要美国等支持区域

### 代理是生命线

用户明确说："没代理你就没法说话。你就是靠代理活着。"
→ 不在理解清楚之前乱改代理配置。改坏了就会失去所有网络能力。

v2rayN.app (macOS) → sing-box/xray 双引擎 → SOCKS5 127.0.0.1:10808

```
本地进程 → SOCKS5 :10808 → v2rayN 路由规则 → 出口节点 → 目标服务
```

## 检查代理状态

- 进程状态：ps aux | grep -iE "v2ray|sing-box|xray"
- 端口监听：lsof -i :10808
- 核心确认：lsof -ti tcp:10808 | xargs ps -o comm= -p  # 确认哪个进程在监听（xray / sing-box）
- 出口地区：curl -x socks5://127.0.0.1:10808 http://ip-api.com/csv/

### 域名可达性快速诊断

代理路由规则不同，各域名的可达性可能不一致。新目标通不通，先测：

```bash
for url in \
  https://github.com \
  https://accounts.x.ai \
  https://api.openai.com \
  https://generativelanguage.googleapis.com; do
  code=$(curl -s -x http://127.0.0.1:10808 --max-time 5 -o /dev/null -w "%{http_code}" "$url" 2>&1)
  echo "$code  $url"
done
```
返回 200=通，000=不通（代理路由拦截或上游不可达）。

### 代理与 curl_cffi 兼容性

macOS 上 v2rayN 代理能与系统 `curl` 和 Python `requests` 正常通信，但与 `curl_cffi` 的 bundled libcurl 存在兼容性问题（连接超时）。根因是 curl_cffi 编译参数与特定代理类型不兼容。解法：
1. **socks5h://** — 优先用 SOCKS5 协议
2. **系统 curl 子进程** — 用 subprocess 调用系统 curl（见 free-ai-api-farming references）
3. **标准 requests** — 换用标准 requests 库（牺牲 TLS 指纹但兼容性最好）

### 目标域名可达性诊断：分清 GFW 封锁 vs 代理路由封锁

当目标无法通过代理访问时（返回 000），需要确定原因：

```bash
# 测试集：包括已知通的 + 未知目标 + 已知不通的
for url in \
  https://github.com \
  https://www.google.com \
  https://www.baidu.com \
  https://accounts.x.ai; do
  code_direct=$(curl -s --noproxy '*' --max-time 5 -o /dev/null -w '%{http_code}' "$url" 2>&1)
  code_proxy=$(curl -s -x http://127.0.0.1:10808 --max-time 5 -o /dev/null -w '%{http_code}' "$url" 2>&1)
  echo "$code_direct/$code_proxy  $url"
done
```

| 结果模式 | 含义 |
|---------|------|
| 代理通其它、不通目标 | **代理路由封锁**（换节点/换代理） |
| 直连通其它、不通目标 | **GFW 封锁**（必须用代理） |
| 代理和直连都不通 | DNS/IP 无法解析或全线阻断 |

### TLS 握手卡住诊断（Mac 特定）

当 CONNECT 隧道建立成功（HTTP/1.1 200）但 TLS ClientHello 发出后超时，说明代理通道本身 OK，问题在 TLS 流量路径上。

**确认步骤（按顺序，不要跳步）：**

```bash
# 1. CONNECT 通不通？
curl -v --connect-timeout 10 -x http://127.0.0.1:10808 https://accounts.x.ai 2>&1 | grep -E "CONNECT|HTTP/1.1 200|TLS|error"
```

| 症状 | 原因（按概率排列） |
|------|------------------|
| CONNECT 200 + ClientHello 发出后超时 | MTU/PMTUD 黑洞（Docker 网桥） |
| | x.ai TLS fingerprint 拒绝 |
| | IPv6 路径异常 |
| CONNECT 失败 | 代理端口 / 内核 / 节点问题 |

**优先级排查：**

1. **强制 IPv4：** `curl -4 -x http://127.0.0.1:10808 https://accounts.x.ai`
2. **MTU 测试：** `sudo ifconfig en0 mtu 1400` 后重测（恢复：`networksetup -setMTU Wi-Fi 1500`）
3. **TLS fingerprint 修改：** xray 配置中 `fingerprint: "chrome"` 改为 `"randomized"` 或 `"firefox"`
4. **代理环境变量污染：** 检查 `env | grep -i proxy`，Docker Desktop 可能注入 `HTTPS_PROXY/HTTP_PROXY` 干扰
5. **抓包确认：** `sudo tcpdump -i lo0 -nn port 10808` 另开 `curl -x http://127.0.0.1:10808 https://accounts.x.ai`

**关键修复：xray 出站 tcpMaxSeg（PMTUD 黑洞最对症）**

当 CONNECT 隧道成功但 TLS 握手卡死，应为路径 MTU/PMTUD 黑洞。最有效的无权限修复是在 v2rayN 当前使用的节点 outbound 的 `streamSettings` 中加 `sockopt`：

```json
"streamSettings": {
  "sockopt": {
    "tcpMaxSeg": 1360,
    "tcpNoDelay": true
  }
}
```

若 1360 仍卡，降为 **1280 → 1200**。原理：压小出站 TCP 段长，避免包超过路径有效 MTU。 注：`sockopt` 对 HTTP CONNECT 出站不生效，需改在 VLESS/VMess/Trojan 等隧道出站上。 不可在 v2rayN 运行时直接修改临时 config（`binConfigs/` 由 GUI 动态生成），应通过 GUI 配置编辑界面或 `guiNConfig.json` 修改后重启内核。

注意：**避免用 standalone xray 实例代替 v2rayN 测试。** 本机 v2rayN 的 xray 进程已经过 v2rayN 初始化（含 DNS、路由、proxy env 适配），独立 xray 可能缺乏这些配置，且 macOS 上可能绕经 Docker 网桥（172.18.0.x）。

**关键区分：不要误诊为 CF→CF 路由冲突。** 同一 v2rayN 代理、同节点，手机上用 VPN/SOCKS5 可能正常打开 x.ai，但 Mac 上 curl/code 走代理时 TLS 握手超时。说明节点本身没问题，问题在 Mac 端 TLS 路径。不是换个节点就能解决的。

### 私享订阅（自建节点）的发现与使用

用户可能拥有未记录在 ProfileItem 表中的自建节点，存储在单独的订阅链接中（raw GitHub URL 等）。这些节点通常是非 CF 的真实服务器。

**获取方式：** 用户直接提供 URL，或从 v2rayN GUI 中查看订阅列表。
**测试链路：**
1. 先确认端口开放：`python3 socket.connect((host, port), timeout=5)`
2. 再确认 TLS 握手正常：`ssl.wrap_socket(server_hostname=sni)`
3. 最后配 xray config 通过代理测试目标可达性

### xray 独立实例测试（macOS 专用）

当需要测试非活跃订阅中的节点时，可以创建独立 xray config 文件，在独立端口运行 xray 实例。注意 macOS 上 xray 独立实例的出站可能绕经 Docker 网桥（172.18.0.x）而非物理接口，可添加 `"sendThrough": "本机IP"` 绑定物理接口。

debug 日志级别帮助定位问题：`"log": {"loglevel": "debug"}`

**常见失败模式：**

| 日志片段 | 含义 | 排查方向 |
|---------|------|---------|
| `REALITY: processed invalid connection` | Reality 服务器拒绝握手 | 节点已失效/公钥/短ID 过期；换其他节点 |
| `REALITY localAddr: 172.18.0.1 DialTLSContext` | 经过 Docker 路由 | 添加 `sendThrough` 或停 Docker 测试 |
| 连接被 accepted 但无后续日志 | TCP 连接建立但应用层未响应 | 检查端口是否真的开放；换协议类型 |

### WARP+ 密钥获取

免费 WARP 不通时可尝试 WARP+ 密钥。来源：Telegram 频道 @warpplus 和 @generatewarpplusbot。macOS 上 xray 的 wireguard 出站使用 gVisor TUN 不工作，需系统级 WireGuard 或 Docker 容器。

### 从 Telegram 群聊导出数据中获取代理订阅

当需要通过代理访问的域名被当前代理节点阻断时，可从 Telegram 导出 JSON 中搜索有效的代理订阅链接：

```bash
# 搜索关键词
grep -r "订阅链接:" ~/.hermes/telegram_exports/ | head -10
grep -r "subscribe?token" ~/.hermes/telegram_exports/ | head -10

# 常用代理分享频道
# @wxdy666, @wxdy_bot, @freeVPNjd, @proxyshareCN
```

找到订阅链接后，通过当前代理抓取验证：
```bash
curl -s -x http://127.0.0.1:10808 --max-time 10 "订阅URL" | head -5
# 返回 base64 编码的节点列表 = 有效
# 返回 {"message":"token is error"} = 已过期
```

验证后可通过程序化方式添加至 v2rayN（见 references/v2rayn-db-operations.md）。

## 节点管理

- 节点切换：v2rayN GUI → 选中节点 → 设为活动服务器
- 订阅更新：v2rayN → 订阅分组 → 更新全部订阅（不通过代理）
- 当前出口检测：通过 curl 走代理访问 IP 定位服务

## 路由模式

| 模式 | 行为 | 适用场景 |
|------|------|---------|
| 绕过大陆(白名单) | 国内直连，国外走代理 | 日常使用 |
| 黑名单 | 仅指定网站走代理 | 特定需求 |
| 全局(Global) | 所有流量走代理 | NotebookLM/Google 服务 |

## NotebookLM 需求

NotebookLM 需要出口节点在**境外支持区域**（美国等）。当前出口在上海（中国联通），需要切换到海外节点。

让 nlm CLI 走代理：
```bash
ALL_PROXY=socks5://127.0.0.1:10808 nlm notebook list
```
或设置环境变量后运行：
```bash
export ALL_PROXY=socks5://127.0.0.1:10808
```

## v2rayN 位置

- 应用：/Applications/v2rayN.app
- 配置：~/Library/Application Support/v2rayN/
- GUI 配置：~/Library/Application Support/v2rayN/guiConfigs/guiNConfig.json
- 内核配置：~/Library/Application Support/v2rayN/binConfigs/

## 长期目标

将代理整体从本机 v2rayN 迁移到 N1 OpenWrt（路由器级代理），所有设备自动走代理。

## 参考文档

- github.com/2dust/v2rayN — v2rayN 客户端
- github.com/SagerNet/sing-box — sing-box 内核
- github.com/xtls/xray-core — xray 内核
- kodi.wiki — Kodi 官网
- references/v2rayn-db-operations.md — v2rayN SQLite 数据库操作、订阅添加、节点查询
