# 域名阻断诊断流程

用于判断某个域名无法访问时，是 GFW 封锁还是代理路由封锁。

## 快速诊断

```bash
# 测试3个关键节点
for url in \
  https://www.baidu.com \
  https://github.com \
  https://accounts.x.ai; do
  d=$(curl -s --noproxy '*' --max-time 5 -o /dev/null -w '%{http_code}' "$url" 2>&1)
  p=$(curl -s -x http://127.0.0.1:10808 --max-time 5 -o /dev/null -w '%{http_code}' "$url" 2>&1)
  echo "直连=$d  代理=$p  $url"
done
```

## 结果解读

| 直连 | 代理 | 结论 |
|:---:|:---:|------|
| 200 | 200 | 域名正常，代理可选 |
| 000 | 200 | **GFW 封锁**，必须走代理 |
| 200/000 | 000 | **代理路由拦截**，换节点/换代理方案 |
| 000 | 000 | 网络全线不通或域名失效 |

## x.ai/Grok TLS 握手卡住（不要误诊为 CF→CF 路由冲突）

**2026-07-16 诊断更新：** 此前记载的「CF WARP → x.ai 不通，推测为 CF→CF 路由冲突」经用户现场验证为误判。同一 v2rayN 代理、同一节点，手机上 VPN 能正常打开 accounts.x.ai。说明节点没问题，问题在 Mac 端 TLS 路径。

### 正确诊断流程

```bash
# 1. 确认 CONNECT 隧道能建
curl -v --connect-timeout 10 -x http://127.0.0.1:10808 https://accounts.x.ai 2>&1 | grep -E "CONNECT|200|established"
# 看到 "HTTP/1.1 200 Connection established" + "TLS handshake" 卡住
# → 隧道通，TLS 握手卡

# 2. 排除 IPv6
curl -4 -x http://127.0.0.1:10808 --max-time 10 https://accounts.x.ai

# 3. 排除 MTU/PMTUD 黑洞（Docker 网桥常见）
sudo ifconfig en0 mtu 1400
curl -x http://127.0.0.1:10808 --max-time 10 https://accounts.x.ai
# 恢复：networksetup -setMTU Wi-Fi 1500
```

### 排查方向（按概率排序）

| 原因 | 概率 | 快速验证 |
|------|------|---------|
| Docker 网桥 MTU/PMTUD 黑洞 | 40% | `sudo ifconfig en0 mtu 1400` 后重测 |
| x.ai TLS fingerprint 拒绝 | 30% | xray 配置 fingerprint 改 `"randomized"` 或 `"firefox"` |
| IPv6 路径异常 | 15% | `curl -4` 重测 |
| Docker 代理环境变量污染 | 5% | `env -u HTTPS_PROXY -u HTTP_PROXY curl ...` |
| macOS PF 防火墙规则冲突 | 5% | `sudo pfctl -d` 后重测 |
