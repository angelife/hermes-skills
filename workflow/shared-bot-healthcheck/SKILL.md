---
name: shared-bot-healthcheck
description: 五行团队各 bot 健康检查与状态报告
disable-model-invocation: true
tags: [wuxing, workflow, healthcheck, monitoring]
---

# Shared: Bot 健康检查

## 适用 bot
土同学（调度者）

## ⚠️ 先决条件：Step 0 — 环境预扫描

在任何远程操作（SSH、ADB、ping）之前，必须先扫描当前网络环境。
不扫描就远程操作是已知翻车模式——被用户明确指正过。

```bash
# 必扫项
echo "=== 本机 IP ===" && ifconfig | grep -E "inet " | grep -v 127.0.0.1
echo "=== 网关 ===" && netstat -rn | grep default | head -3
echo "=== DNS ===" && scutil --dns 2>/dev/null | grep "nameserver" | head -3
echo "=== PROXY ===" && echo "http=$http_proxy https=$https_proxy"
```

### 网络环境判断

本机（土）在不同环境下的典型 IP 段。注意 192.168.2.x（家网）与 192.168.1.x（火同学所在网段）之间路由可达，不要仅因 IP 段不同就跳过检查。

| 网络 | 特征 | 可达设备 |
|------|------|---------|
| 🏠 家（192.168.2.x） | 网关 192.168.2.x | 金(Mi8) 2.127 (ADB TCP), 火(1.27 路由可达) |
| 🏢 办公（192.168.1.x） | 网关 192.168.1.x | 火(1.27), 金(Mi8 via USB), 代理 |
| ❓ 未知 | 其他网段 | 先 ping 目标 IP 确认 |

**规则：** 检查网络环境后再判断哪些 bot 可达。金同学在家网走 ADB TCP 5555（已知假开放问题），在办公网走 USB 直连。

**陷阱：** 不要仅因本机 IP 段不同就判断远程 bot 不可达。家网（192.168.2.x）到火同学（192.168.1.27）路由可达，必须实际 ping 验证。

## 检查流程

### 1. 连接性检查
```bash
# 金同学（Mi8）— 家网 ADB TCP
adb -s 192.168.2.127:5555 shell "su 0 -c 'echo ALIVE'" 2>/dev/null || echo "TCP offline"
# 办公网 USB 直连
adb devices 2>/dev/null | grep dipper || echo "USB offline"

# 火同学（Arch Linux TV — 192.168.1.27）
ping -c 1 -W 2 192.168.1.27 2>/dev/null && echo "ping OK" || echo "DEAD"

# 进阶诊断（ping 通但 SSH 失败时）
# 已知故障模式：端口开放 + ping 通但 SSH 被远端关闭
# ("Connection closed by remote" / "Connection timed out during banner exchange")
# 可能原因：SSHD 卡死、系统负载过高、MaxAuthTries 耗尽
nc -z -G3 192.168.1.27 22 2>&1 && echo "port 22 open" || echo "port 22 closed"
nc -z -G3 192.168.1.27 80 2>&1 && echo "port 80 open" || echo "port 80 closed"

# 水同学（Mi6）
adb devices 2>/dev/null | grep -i mi6 || echo "water offline"
```

### 2. Gateway 状态检查
```bash
hermes gateway list 2>&1
```

### 3. 日志健康
```bash
# 最近错误
tail -50 ~/.hermes/logs/gateway.log | grep -i "error\|exception\|traceback"
```

### 4. 资源检查
```bash
# 磁盘
df -h ~/.hermes/logs

# 日志大小
du -sh ~/.hermes/logs/
```

## 输出格式

```
## 🟢/🟡/🔴 五行健康报告

| bot | 网络 | Gateway | 日志 | 磁盘 |
|-----|------|---------|------|------|
| 🪨 土 | ✅ | ✅ | ✅ | 45M |
| 🔥 火 | ✅ | ✅ | ⚠️ 1 error | 12M |
| 🥇 金 | ✅ | ❌ | — | — |
| 💧 水 | ❌ | — | — | — |

### 需关注
1. 火同学日志有 1 条 error — 时间戳 / 内容
2. 金同学 gateway 挂了 — 上次重启时间
```
