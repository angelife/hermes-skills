# WiFi 坏了时的替代网络方案

设备: Mi8 (dipper), LineageOS 22.2, Android 15
场景: 手机 WiFi 硬件损坏，需要通过其他方式上网

## 诊断

```bash
# 确认 WiFi 不可用
adb shell "ip addr show" | grep wlan
# 无输出 → 物理损坏，不要尝试软件修复

# 确认 RNDIS 接口存在（USB 连接电脑时有）
adb shell "ip addr show" | grep rndis
# → 192.168.128.177/24

# 检查内核驱动支持
adb shell "zcat /proc/config.gz | grep -E 'CONFIG_USB_NET|AX8817|RTL815|CDC_ETHER|RNDIS'"
```

## 方案排名

### 方案 1: RNDIS (通过 Mac 共享网络)

Mac 端操作: 系统设置 → 共享 → 互联网共享
- "共享以下来源的连接": WiFi
- "使用以下端口共享给": USB 10/100/1000 LAN (或 iPhone USB / RNDIS 接口)
- 需要 Mac 管理员密码

手机获得 192.168.128.x 网段 IP，走 Mac 的 WiFi 网络。

**验证**:
```bash
# Mac 侧
ifconfig | grep 192.168.128

# 手机侧
adb shell ping -c 2 8.8.8.8
```

### 方案 2: OTG + USB 以太网卡

硬件: ASIX AX88772D / RTL8153 通过 USB OTG 连接手机
网线: 从路由器连接到 USB 网卡

Mi8 内核已知包含 asix 和 ax88179_178a 驱动，即插即用。

**不推荐**: 如果 Mac 侧的 USB 网卡需要额外调试（MAC 地址 null 等问题），会更折腾。

### 方案 3: 另一台 Android 手机 USB Tethering

硬件: Mi6 (数据线连接 Mi8 和 Mi6)
Mi6 操作: 设置 → 热点与网络共享 → USB 网络共享
Mi8 获得 rndis0 接口，走 Mi6 的数据网络。

## 对 Termux 的影响

如果手机本身没网络，Termux 的 apt-get 也会失败:

```
Unable to resolve 'packages-cf.termux.dev:https' (7 - No address associated with hostname)
```

解决顺序: 先解决手机网络 → 再 apt-get update/install。