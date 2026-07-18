# Mi8 有线网卡上网配置记录

## 物理连接
```
Mi8(USB-C) → USB-C Hub → RTL8153 USB 以太网适配器 → 网线 → 路由器LAN
                                                             ↑
Mac WiFi ─────────────────────────────────────────────────┘
```

## Mi8 端网络信息
- `ip addr show eth0` → `inet 192.168.1.21/24`
- 网卡驱动：原生 CDC-Ethernet（Linux 内核自带）
- 网关：192.168.1.1（路由器）
- DNS：路由器分配

## Mi8 端 ADB 配置
```bash
# 确认 ADB TCP 已监听
getprop persist.adb.tcp.port  # 应输出 5555
getprop service.adb.tcp.port  # 应输出 5555

# 如果未配置，手动开启
adb tcpip 5555
```

## Mac 端连接
```bash
# 直接连 Mi8 局域网 IP（同一广播域）
adb connect 192.168.1.21

# 验证
adb -s 192.168.1.21 shell "getprop ro.build.version.release"
# 应输出：15
```

## 关键发现

### 1. Mi8 有多张网卡导致路由不对称
- 移动数据 IP：192.168.50.3、192.168.114.141
- RNDIS IP：192.168.45.184
- 有线网卡 IP：192.168.1.21
- ping 移动数据 IP 通 ≠ ADB 能通（回程路由问题）

### 2. RTL8192 vs RTL8192LE 芯片区别
- **RTL8153/RTL8152**：USB 以太网芯片，macOS 原生驱动，en9 拿 IP → ✅ 可用
- **RTL8192LE**：WiFi USB 网卡，macOS 无驱动 → ❌ 不可用
- 鉴别：`system_profiler SPNetworkDataType` 显示 "USB 10/100 LAN" = 以太网芯片

### 3. Mi8 wlan0 不存在
- LineageOS 精简版 WiFi 驱动被移除或硬件损坏
- `ls /sys/class/net/` 无 wlan0 条目
- 只能用有线网卡上网

## 路由表（Mi8 端）
```
default via 192.168.1.1 dev eth0 proto dhcp
192.168.1.0/24 dev eth0 proto kernel scope link src 192.168.1.21
```

## 故障排查流程

1. **ping 不通 192.168.1.21** → 检查网线和路由器连接
2. **ping 通但 adb connect 超时** → 确认 Mi8 上 `adb tcpip 5555` 已执行
3. **device offline** → 路由不对称，检查是否连错 IP（移动数据 IP 不能用）
4. **Mac 上没有 en 接口** → USB 网卡是 RTL8192LE（WiFi 网卡），不是以太网芯片

## 推荐配置
- Mi8 用 RTL8153/RTL8152 USB 以太网适配器（macOS 原生驱动）
- 通过 OTG Hub 分出 USB-A 口同时支持 ADB 调试
- Mi8 DHCP 获取 192.168.1.x 后 Mac 直接 `adb connect <该IP>` 即可