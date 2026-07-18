# wgcf 免费 Cloudflare WARP 注册与使用

## 用途

当 v2rayN 的 CF 优选节点无法路由到特定目标（如 x.ai/Grok，CF→CF 路由限制）时，
可注册官方免费 WARP 账号作为独立出站通道。

## 注册流程

```bash
# 1. 下载 wgcf
curl -Lo /tmp/wgcf https://github.com/ViRb3/wgcf/releases/download/v2.2.22/wgcf_2.2.22_darwin_amd64
chmod +x /tmp/wgcf

# 2. 注册（自动应答 EULA）
cd /tmp && echo "Yes" | /tmp/wgcf register
# → 生成 wgcf-account.toml

# 3. 生成 WireGuard 配置
/tmp/wgcf generate
# → 生成 wgcf-profile.conf
```

## 配置内容示例

```
[Interface]
PrivateKey = xxx...
Address = 172.16.0.2/32
DNS = 1.1.1.1
MTU = 1280

[Peer]
PublicKey = bmXOC+F1FxEMF9dyiK2H5/1SUtzH0JuVo51h2wPfgyo=
AllowedIPs = 0.0.0.0/0
Endpoint = engage.cloudflareclient.com:2408
```

## macOS 集成方式

### 方案A：xray WireGuard 出站（已验证：不可用）

用 xray 的 `wireguard` 协议作为 outbound，发往 WARP。

**配置片段：**
```json
{
  "outbounds": [{
    "tag": "warp",
    "protocol": "wireguard",
    "settings": {
      "secretKey": "<PrivateKey from wgcf>",
      "address": ["172.16.0.2/32"],
      "peers": [{
        "publicKey": "<PublicKey>",
        "endpoint": "engage.cloudflareclient.com:2408",
        "keepAlive": 25
      }],
      "mtu": 1280
    }
  }]
}
```

**坑：** xray 在 macOS 上使用 gVisor TUN（用户态 WireGuard），handshake 不完整。log 中连接显示 "accepted" 但实际 TCP/HTTP 全部超时（exit 28/000）。**macOS 上不要依赖 xray wireguard outbound。**

### 方案B：系统 WireGuard 接口（推荐，需要 brew, wireguard-tools）

```bash
brew install wireguard-tools
sudo cp wgcf-profile.conf /usr/local/etc/wireguard/wgcf.conf
sudo wg-quick up wgcf
# WARP 接口上线后，curl 指定网卡：
curl -s --interface utun3 --max-time 5 https://accounts.x.ai
```

注：brew/apt 在 CF WARP 代理下可能超时（TLS handshake timeout），需要非 CF 代理通道。

### 方案C：Docker 容器（需要可用 registry）

国内 Docker Hub / ghcr.io 在 CF WARP 下不可达（TLS handshake timeout）。需要非 CF 代理才能拉取镜像。

## 已验证结论

| 方法 | 状态 | 说明 |
|------|------|------|
| xray wireguard outbound (gVisor) | ❌ 不可用 | macOS 上 handshake 不完整 |
| 系统 WireGuard 接口 | ⚠️ 需要 brew | 未验证 |
| Docker WARP 容器 | ⚠️ Registry 不可达 | ghcr.io 拉取超时 |
| 官方 WARP 客户端 | ⚠️ 需要 brew cask | 未安装，brew cask install cloudflare-warp |
