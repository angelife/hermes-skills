---
name: session-orientation
description: 新会话/位置变更时的环境感知流程 — 先查清当前网络拓扑再动手
tags: [meta, workflow, session, awareness]
---

# Session Orientation — 环境感知流程

## 触发条件

- 新会话开始（尤其是用户从不同网络接入时）
- 用户提到位置变化（"我在外面"、"换个地方"、"IP 变了"）
- 涉及远程设备操作（ADB / SSH / 代理）的任务前
- 上次会话结束时有未完成的远程操作

---

## 扫描流程

用户未主动告知网络情况时，先扫描环境，再假设基础设施可及。

### Step 0: ARP 扫描（先看有什么，不靠记忆）

不要从记忆或历史会话推断当前在线设备。先扫局域网实际设备：

```bash
# 扫 ARP 表 - 看当前网段有哪些 MAC 地址
arp -a | grep -i "192.168."

# 对每个在线 IP 做 ping 验证
for ip in $(arp -a | grep -i "192.168." | grep -oE '\d+\.\d+\.\d+\.\d+'); do
  echo -n "$ip: "
  ping -c1 -W1 $ip 2>/dev/null | grep "bytes from" >/dev/null && echo "UP" || echo "DOWN"
done
```

根据实际在线设备列表匹配已知角色。**不在 ARP 表中的设备视为离线，不做假设。**

### Step 1: 本机网络

```bash
# IP + 网段
ifconfig | grep "inet " | grep -v 127.0.0.1

# 默认网关
netstat -rn | grep default

# 代理环境变量
env | grep -i "proxy"

# DNS
scutil --dns 2>/dev/null | grep "nameserver" | head -3
```

### Step 2: 关键设备可达性

```bash
# 基于 ARP 扫描结果，只探测实际在线的已知设备
# 先确认本机 IP 和网关
ifconfig | grep "inet " | grep -v 127.0.0.1
netstat -rn | grep default
```

### Step 3: 服务端口

```bash
nc -z -w 2 192.168.1.8 10808 && echo "PROXY_OK" || echo "PROXY_DOWN"
```

---

## 输出报告

扫描后向用户输出简明的环境摘要，**只列实际在线的设备**：

| 项 | 值 |
|----|-----|
| 本机 IP | 192.168.0.x / 192.168.1.x / 其他 |
| 网关 | xxx |
| 代理 | 有/无 |
| 在线设备 | 据 ARP 结果列出实际在线 IP 和对应的已知角色 |

## 原则

**不要从记忆或上一会话推断当前网络拓扑。** 用户换网络是常态，默认所有远程设备不可达，确认后再用。

**先 ARP 扫网再看怎么做。** 连当前网段有什么设备都不知道就动手，会被严厉纠正。

**典型失败模式**：
1. 从记忆里捞出一堆历史设备（水同学/火同学/蜗牛星际/NAS 等），直接当在线处理 — ❌
2. 看到端口 5555 开放就直奔 ADB 协议调试，没先确认 adbd 是否活着 — ❌
3. 用户明确说了"只有这么一台"，还去扫不存在的设备 — ❌

**正确流程**：
1. `arp -a | grep "192.168."` → 只看实际有 MAC 地址的设备
2. 对每个在线 IP 做 `ping -c1 -W1` 确认真在线
3. 把在线 IP 列表和已知设备角色做匹配，**不在列表的一律视为不存在**
4. 用户问"还有别的机器吗"之前，不要主动假设历史设备还在线

## 相关参考

- `references/session-lifecycle.md` — 会话生命周期管理：何时应该 `/new`
