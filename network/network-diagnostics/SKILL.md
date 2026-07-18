---
name: network-diagnostics
title: "网络诊断 — 代理不稳定/慢/断连排查"
description: "系统化诊断网络问题：代理不稳定、国际出口限速、DNS 污染、WiFi 拥堵。先做对比测试找瓶颈层，再针对性解决。覆盖中国大陆常见场景（免费 WiFi 限速、公共热点拥堵、运营商 QoS）。"
category: network
tags: [network, proxy, dns, diagnostics, wifi, troubleshooting]
---

# 网络诊断 — 代理不稳定/慢/断连排查

## 核心原则

> **先找瓶颈层，再动手修。**

网络慢有四个可能瓶颈层，必须逐层定位：
1. **局域网**（WiFi 信号、路由器负载）
2. **国内宽带**（国际出口带宽、ISP QoS）
3. **代理服务器**（带宽、响应速度）
4. **DNS**（解析慢、污染）

手机热点正常 → 代理服务器正常 → 问题在局域网或国际出口。

## 标准诊断流程

### 第 0 步：确认代理本身正常

```bash
# 检查本地代理端口是否在监听
lsof -i :10808 2>/dev/null
nc -zv 127.0.0.1 10808 2>&1
```

### 第 1 步：基础网络检查

```bash
# WiFi 信号
airport -I 2>/dev/null | grep -E "SSID|signal|noise|channel|rate"

# 网关延迟（正常 <5ms）
ping -c5 -W2 <gateway_ip> 2>&1 | tail -3

# DNS 解析速度（正常 <0.1s）
time dig +short google.com @8.8.8.8 2>&1
```

### 第 2 步：对比测试定位瓶颈

```bash
# 国内网站（正常 <0.5s）
curl -s -o /dev/null -w "baidu: %{http_code} (%{time_total}s)\n" \
  --connect-timeout 5 https://www.baidu.com

# 国际直连（正常 <1s）
curl -s -o /dev/null -w "google: %{http_code} (%{time_total}s)\n" \
  --connect-timeout 10 https://www.google.com

# 经代理到国际
curl -s -o /dev/null -w "proxy: %{http_code} (%{time_total}s)\n" \
  --connect-timeout 10 -x socks5://127.0.0.1:10808 https://www.google.com
```

**对比判断：**
| 国内快 + 国际直连慢 + 代理也慢 → **国际出口拥堵**（宽带本身问题）|
| 国内快 + 国际直连慢 + 代理快 → **代理生效正常**（需要代理）|
| 国内快 + 国际直连快 + 代理慢 → **代理服务器问题** |
| 国内慢 → **局域网或国内宽带问题** |

### 第 3 步：局域网深度诊断

```bash
# 设备数（20+在线 = 网络可能拥堵）
arp -a | wc -l

# MAC 随机化比例（iOS/Android 隐私MAC多 = 公共热点）
arp -a | grep -cE "^..:(..:){4}.."

# 网关指纹（判断路由器老旧）
curl -s -I --connect-timeout 5 http://<gateway_ip> 2>&1 | head -5

# DHCP 租约（<4h = 公共热点典型配置）
ipconfig getpacket en0 | grep lease_time
```

### 第 4 步：DNS 污染诊断

```bash
# 对比多个 DNS 的解析速度
time dig +short google.com @8.8.8.8     # 可能被污染/慢
time dig +short google.com @223.5.5.5   # 阿里 DNS（国内节点）
time dig +short google.com @119.29.29.29# 腾讯 DNS
time dig +short google.com @114.114.114.114 # 114 DNS
```

国内 DNS 比 8.8.8.8 快很多 → 8.8.8.8 在免费 WiFi 被限速/污染。

### 第 5 步：连续监测（判断是否有时段性）

```bash
# 每隔 30s 测一次代理速度，跑 5 次
for i in 1 2 3 4 5; do
  curl -s -o /dev/null -w "[$i] proxy: %{time_total}s\n" \
    --connect-timeout 10 -x socks5://127.0.0.1:10808 https://www.google.com
  sleep 30
done
```

## 常见场景及方案

| 场景 | 诊断结论 | 方案 |
|------|---------|------|
| 国内快、国际直连慢、代理慢 | **国际出口拥堵**（免费 WiFi/校园网常见） | 切手机热点 / 错峰 / Warp 中转 |
| 国内快、国际直连快、代理慢 | 代理服务器问题 | 检查代理服务器负载 / 换节点 |
| 国内快、国际直连慢、代理快 | 代理正常 | 保持代理，无需额外操作 |
| 国内也慢 | **局域网/宽带问题** | 查 WiFi 信号 / 路由器重启 / 宽带报修 |
| DNS 8.8.8.8 慢，国内 DNS 快 | **DNS 污染/限速** | 改 DNS 到 223.5.5.5 或 119.29.29.29 |

## 具体操作

### 改 DNS（macOS）

```bash
# 需要 sudo 权限
sudo networksetup -setdnsservers Wi-Fi 223.5.5.5 114.114.114.114
```

### 测代理端口是否被 QoS

```bash
# 换 HTTP 代理端口（如 7890 或 443）
curl -x http://127.0.0.1:7890 https://www.google.com
```

## 参考文件

- `references/tls-handshake-timeout-diagnosis.md` — TLS 握手超时诊断：CONNECT 隧道成功但 TLS 卡住（特定域名），含 MTU/PMTUD 黑洞排查、TLS fingerprint 调整、IPv6 排除等

## 已知陷阱

| 陷阱 | 现象 | 解决 |
|------|------|------|
| **单次测试不准** | 速度波动大 | `ping -c10` 或 `for` 循环连续测 5 次 |
| **代理端口堵塞** | SOCKS5 10808 不通但代理正常 | 换 HTTP 7890 或自定义端口 |
| **WiFi 5GHz/2.4GHz 混用** | 信号好但速度慢 | 确认连的是 5GHz 频段 |
| **DNS 缓存迷惑** | dig 一次快一次慢 | `dscacheutil -flushcache` 清缓存再测 |
| **对比法失效** | 手机热点和免费 WiFi 不同设备 | 让同一设备在两种网络下测，控制变量 |
| **跨子网不通** | 两个设备在同一路由器下但不同子网（如 192.168.1.x 和 192.168.2.x），A→B 通但 B→A 不通（非对称路由/防火墙拦截） | 从可达侧建 SSH 反向隧道桥接端口：`ssh -R 远端端口:127.0.0.1:本机端口 user@远端IP`。把远端 bot config 的代理/API/hindsight 地址全改 `127.0.0.1`，隧道自动转发。**验证**：在远端 `curl -x socks5://127.0.0.1:10808 https://api.telegram.org` 应返回 302 |
| **Docker macOS host.docker.internal IPv6 陷阱** | 容器设 `https_proxy=socks5://host.docker.internal:10808` 后反而连不上上游 | Docker for Mac 上 host.docker.internal **只解析到 IPv6**（`fdc4:f303:9324::254`），而 v2rayN SOCKS5 只监听 IPv4 `127.0.0.1:10808`。容器尝试通过 IPv6 连代理 → 失败 → wget 返回空（exit 0）或 server error（exit 8）。**解决**：不设 proxy env var 直接测容器直连；如果容器能通就裸跑，不用代理。三路法见 `new-api-administration` 的「路由诊断完整流程」|
