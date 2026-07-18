# 遗留静态 IP 导致 USB 网卡 `status=inactive`

## 场景

把 USB 以太网适配器（RTL8152）插到 Mac 后：
- `system_profiler SPUSBDataType` 认到了设备
- `networksetup -listallhardwareports` 新建了 `enX` 接口
- `ifconfig enX` 显示 `status: inactive`

## 根因

之前因为某种 USB 网络用途（如 Android 手机 RNDIS USB 共享、旧 USB 设备），macOS 上保存了一份**手动（Manual）IP 配置**。新插入的 USB 网卡复用了这个配置，静态 IP 不在当前网络网段，导致接口显示 inactive。

## 检查

```bash
# 查 IP 配置模式
networksetup -getinfo "USB 10/100 LAN"

# 如果返回：
#   Manual Configuration
#   IP address: 192.168.45.2
#   Router: 192.168.45.184
#   说明是遗留手动配置
```

## 修复

```bash
networksetup -setdhcp "USB 10/100 LAN"
```

立即生效。接口自动拿到 DHCP IP，`status` 变为 `active`。

## 常见遗留网段

| 来源 | 常用网段 |
|---|---|
| Android RNDIS / USB 网络共享 | 192.168.42.x, 192.168.45.x |
| macOS Internet Sharing（旧版） | 192.168.2.x |
| 第三方 VPN / 代理工具 | 各厂商不同 |

## 同类排查命令速查

```bash
# 列出所有网络服务和对应配置模式
networksetup -listallhardwareports

# 看具体某个服务是 Manual 还是 DHCP
networksetup -getinfo "服务名"

# 批量检查所有服务配置模式
networksetup -listallnetworkservices | while read svc; do
  echo "=== $svc ==="
  networksetup -getinfo "$svc" 2>/dev/null | grep -E "Configuration|IP address|Router"
done
```
