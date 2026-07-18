# TLS 握手超时诊断 — CONNECT 成功但 TLS 卡住

## 问题模式

```
curl -x http://127.0.0.1:10808 https://accounts.x.ai

→ CONNECT accounts.x.ai:443 HTTP/1.1 200 Connection established ✅
→ TLSv1.3 Client hello (318 bytes) 发出
→ 卡住直到超时 (30s)
```

**关键特征：** CONNECT 隧道建立成功（代理通道通），但 TLS ClientHello 发出后 ServerHello 不回来。同一代理能正常访问 Google/GitHub，手机同节点正常。

## 诊断框架（按概率排序）

| 原因 | 概率 | 快速验证 |
|------|------|---------|
| **MTU/PMTUD 黑洞**（Docker 网桥干扰） | 40% | `sudo ifconfig en0 mtu 1400` 再测 |
| **TLS fingerprint 被目标拒绝** | 30% | 改 xray outbound fingerprint: chrome→firefox→randomized |
| **IPv6 路径异常** | 15% | `curl -4` 强制 IPv4 再测 |
| **DNS 分流/特殊 CDN** | 10% | `--resolve accounts.x.ai:443:<IP>` 绕过 DNS |
| **Docker 代理环境变量污染** | 5% | `env -u HTTPS_PROXY curl ...` |
| **macOS PF 规则冲突** | 5% | `sudo pfctl -d` 关闭测试 |

## 排查步骤

### 1. 确认问题模式

```bash
# 基础测试 — 看卡在哪一步
curl -v --connect-timeout 10 -x http://127.0.0.1:10808 https://accounts.x.ai 2>&1 | head -20
```

如果输出：
```
CONNECT accounts.x.ai:443 HTTP/1.1 200 Connection established
* TLSv1.3 Client hello (318 bytes)
```
然后卡住 → 问题在 TLS 层，不是代理通道。

### 2. 排除 IPv6

```bash
curl -4 --max-time 30 -v -x http://127.0.0.1:10808 https://accounts.x.ai 2>&1 | head -20
```

如果 IPv4 也卡住 → 排除 IPv6 原因。

### 3. 检查 MTU

```bash
# 看各接口 MTU
for iface in lo0 en0 bridge100 docker0 utun0 utun1 utun2 utun3; do
  mtu=$(ifconfig $iface 2>/dev/null | grep "mtu" | awk '{print $4}')
  [ -n "$mtu" ] && echo "$iface mtu=$mtu"
done
```

**异常值：** utun 接口 MTU < 1400（如 utun3 mtu=1000）可能影响大 TLS 包。

```bash
# 测试降低 en0 MTU
sudo ifconfig en0 mtu 1400
curl -s --max-time 30 -x http://127.0.0.1:10808 -o /dev/null -w "HTTP:%{http_code}\n" https://accounts.x.ai
# 恢复
sudo ifconfig en0 mtu 1500
```

### 3. 检查 TLS fingerprint

xray outbound 配置中的 fingerprint 可能被目标拒绝：

```json
"streamSettings": {
  "security": "tls",
  "tlsSettings": {
    "fingerprint": "chrome"   # 尝试改为 "firefox" 或 "randomized"
  }
}
```

### 4. 检查代理环境变量冲突

```bash
env | grep -i proxy
```

常见冲突：`http_proxy=socks5h://127.0.0.1:10808` 但 `HTTPS_PROXY=http://127.0.0.1:10808` — 两种协议混用可能导致 curl 行为不一致。

### 5. 抓包确认

```bash
# 一个终端抓包
sudo tcpdump -i lo0 -nn port 10808

# 另一个终端发请求
curl -x http://127.0.0.1:10808 https://accounts.x.ai
```

如果看到 ClientHello 发出但 ServerHello 没回来 → 代理出口/MTU/TLS fingerprint 问题。

## 已知案例

| 环境 | 症状 | 根因 | 解决 |
|------|------|------|------|
| macOS + v2rayN + Docker | CONNECT 200 但 TLS 超时，Google/GitHub 正常，手机同节点正常 | 疑似 MTU/PMTUD 黑洞（Docker 网桥干扰）或 x.ai TLS fingerprint 严格检查 | 降低 en0 MTU 测试 / 改 fingerprint |

## 关键原则

- **手机同节点正常 → 节点没问题，问题在 Mac 本地网络路径**
- **Google/GitHub 能开不代表所有域名都能开** — 不同 CDN 的 TLS 包大小、fingerprint 检查严格度不同
- **CONNECT 200 只证明代理通道通，不证明 TLS 层通**
- **先问 AI 再动手** — 卡住 2 次以上就总结问题问 ChatGPT/Claude，不要自己硬撞
