---
name: environment-assessment
description: 每次启动新会话时先扫描运行环境——网络段、设备可达性、代理、办公位置，避免在错误假设下操作
disable-model-invocation: true
domain: meta
tags: [startup, environment, network, context, scanning]
---

# 环境评估协议

## 触发条件

**每次新会话开始时**，或在用户说"我在外面"、"IP变了"、"当前环境"等暗示位置改变的信号后，**必须立即执行**。

不要在接到任务后直接假设「家内网络环境」，先确认当前在哪个网段。

---

## 执行步骤

### 第一步：ARP 扫描（先看有什么，不靠记忆）

```bash
# 扫 ARP 表 - 当前网段实际在线的设备
arp -a | grep -i "192.168."
```

**这一步必须在任何假设之前执行。** 不在 ARP 表中的设备视为离线。

### 第二步：获取本机网络信息

```bash
# IP 地址
ifconfig | grep -E "inet " | grep -v 127.0.0.1

# 默认网关 + 网段
netstat -rn | grep default

# DNS
# macOS:
scutil --dns 2>/dev/null | grep "nameserver" | head -5
# Linux:
cat /etc/resolv.conf 2>/dev/null | grep nameserver

# 代理环境变量
echo "http_proxy=$http_proxy"
echo "https_proxy=$https_proxy"
echo "ALL_PROXY=$ALL_PROXY"
echo "NO_PROXY=$NO_PROXY"
```

### 第三步：判断位置

| 网段 | 场景 | 说明 |
|------|------|------|
| `192.168.1.x` | 家里 | 可能有在线设备，据 ARP 结果判断 |
| `192.168.0.x` | 外网 | 仅有本机，无代理，无其他五行设备 |
| 其他 | 未知 | 需要用户告知 |

### 第四步：检查关键服务可达性（仅当 ARP 显示设备在线时）

```bash
# 基于 ARP 结果，只探测实际在线的地址
# ⚠️ macOS 可能没有 ping，用 nc 作为替代
HAVE_PING=$(command -v ping 2>/dev/null && echo 1 || echo 0)
arp -a | grep -E "192\\.168\\.1\\." | while IFS= read -r line; do
  ip=$(echo "$line" | grep -oE '\\d+\\.\\d+\\.\\d+\\.\\d+')
  echo -n "$ip: "
  if [ "$HAVE_PING" = "1" ]; then
    ping -c 1 -W 2 "$ip" >/dev/null 2>&1 && echo "UP" || echo "DOWN"
  else
    nc -z -G 2 "$ip" 22 2>/dev/null && echo "UP" || echo "DOWN"
  fi
done
```

### 第五步：根据环境调整策略

| 环境 | 可行操作 | 禁止操作 |
|------|---------|---------|
| 家里(192.168.1.x) | SSH 到其他设备、走代理、全量操作 | — |
| 外网(192.168.0.x) | 本机直连、安装工具、本地开发 | ❌ 推送到远程设备 ❌ 依赖代理 ❌ 访问 192.168.1.x 设备 |
| 未知 | 等用户说明 | ❌ 任何假设性远程操作 |

---

## 参考文件

- `references/graphify-walkthrough.md` — 环境直连时可安装的 graphify 项目地图工具

## 关键陷阱

- 🔴 **不要假设用户在家** — 用户可能在任何地方用 Telegram 接入
- 🔴 **代理不是默认有** — 只有在家内网才配置了 192.168.1.8:10808
- 🔴 **SSH 连接失败不一定是服务挂了** — 可能是不在同一个局域网
- 🔴 **".env"中的代理设定只在家的环境中有效** — 外网时不要依赖它
- 🔴 **先扫网络再假设设备存在** — 不要凭空想象机器列表。`arp -a` + 端口扫描是必须的前置步骤
- 🔴 **不要从记忆推断设备在线列表** — "以前有 Mi6/Mi8/火同学" 不等于它们现在还在。用户明确说"目前只有这么一台"时，只报告 `arp -a` 确认的设备，不补充记忆中的其他设备
- 🔴 **ADB 端口开放 ≠ ADB 可用** — 两种已知失败模式：
  - **Daemon 挂掉**：端口 5555 开放但 ADB 守护进程已死（TCP 连上但无 CNXN 握手）。`nc -zv` 只能证明 TCP 端口在监听，必须用 raw socket 收 ADB CNXN 协议包才能确认 daemon 存活
  - **No route to host**：`nc -zv` 显示端口开放，但 `adb connect` 报 "No route to host" — 特定于 ADB 连接层，直连 TCP 正常但 ADB 握手路由失败。通常需要物理操作：`stop adbd; start adbd; setprop service.adb.tcp.port 5555; stop adbd; start adbd`
- 🔴 **用户说"去读微信" ≠ "去读群聊天"** — 用户提到"小米 微信"时指的是手机上的微信聊天数据库，不是 Telegram 群消息。区分清楚后再动手

---

## 执行后报告格式

向用户简洁报告：

```
**环境扫描：**
- 本机 IP：`xxx.xxx.xxx.xxx`
- 网段：`xxx.xxx.x.x`（家里/外网）
- 代理：有/无
- 可达设备：...
- 结论：可以做 X，不能做 Y
```
