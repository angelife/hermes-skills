# Mi8 USB RNDIS 网络共享配置

## 设备信息

- 型号：Mi8 (dipper)
- ADB ID：a6520fa3
- Android 版本：LineageOS（具体版本见 `getprop ro.build.version.release`）
- USB 网络共享接口：rndis0（Android 侧）、en5（Mac 侧 RNDIS Gadget）、en8（Mac 侧 AX88772D）

## 配置步骤

### 1. 启用 RNDIS（USB 网络共享）

```bash
# 普通 shell（已授权 root）
adb -s a6520fa3 shell "svc usb setFunctions rndis"

# 需要 su 的设备
adb -s a6520fa3 shell "su -c 'svc usb setFunctions rndis'"
```

验证：
```bash
adb -s a6520fa3 shell "svc usb getFunctions"
# 应输出：rndis

adb -s a6520fa3 shell "ip addr show rndis0"
# 应显示类似：inet 192.168.114.141/24
```

### 2. 确保移动数据开启（重要！）

```bash
# 启用移动数据
adb -s a6520fa3 shell "svc data enable"

# 或者手动设置
adb -s a6520fa3 shell "settings put global mobile_data 1"
```

**否则**：Mi8 的默认路由表没有 0.0.0.0，ping 8.8.8.8 会报 "Network is unreachable"。

验证：
```bash
adb -s a6520fa3 shell "ip route show all | grep default"
# 应显示 rmnet_dataX 的默认路由
```

### 3. AX88772D USB 网卡路径（推荐）

当 Mi8 连接「USB 充电」+ 以太网共享模式，Mac 通过 AX88772D USB 网卡直连 Mi8 有线口：

```bash
# Mac 侧刷新 DHCP
networksetup -setdhcp "AX88772D"
sleep 3
ipconfig getpacket en8
# 应显示：yiaddr = 192.168.50.x, router = 192.168.50.1

# 验证连通性
ping -c 2 192.168.50.1
curl -s --interface en8 https://ipinfo.io/json --max-time 8
```

### 4. RNDIS Gadget 路径（备用）

当 Mi8 开启 RNDIS USB 网络共享，Mac 识别为「RNDIS/Ethernet Gadget」（en5）：

```bash
# 确认 Mac 侧接口
system_profiler SPNetworkDataType 2>/dev/null | grep -B1 -A 6 "RNDIS"
# 应显示 BSD Device Name: en5

# 如果 DHCP 拿不到 IP，尝试静态配置
sudo networksetup -setmanual "RNDIS/Ethernet Gadget" 192.168.114.142 255.255.255.0 192.168.114.141

# 验证
ping -c 2 192.168.114.141
```

### 5. Mac → Mi8 → WiFi 路由配置

如果要让 Mi8 的流量走 Mac 的 WiFi（而不是 Mi8 自己的 4G，4G 要花钱），需要在 Mac 开启「互联网共享」：

1. Mac 系统设置 → 通用 → 共享 → 互联网共享
2. 共享「WiFi」连接到「RNDIS/Ethernet Gadget」或「AX88772D」
3. macOS 自动配置 NAT + DHCP + DNS，无需 sudo

**没有 GUI 时**（需要 sudo 密码才能手动配置）：
```bash
# Mac 开启 IP forwarding
sudo sysctl -w net.inet.ip.forwarding=1

# Mac 设置 NAT（需要 root）
sudo natd -interface en0 -dynamic

# Mi8 添加默认路由指向 Mac
adb -s a6520fa3 shell "ip route add default via 192.168.114.142 dev rndis0"
```

### 6. 测试连通性

```bash
# Mac → Mi8 直 ping
ping -c 2 192.168.114.141

# Mi8 → 外网（验证移动数据）
adb -s a6520fa3 shell "ping -c 2 -W 3 8.8.8.8"

# Mac 走 Mi8 出网
curl -s --interface en8 https://ipinfo.io/json --max-time 8
# 应返回 Mi8 的 4G IP（上海移动 AS24400）
```

## IP 分配

| 端 | 接口 | IP | 说明 |
|----|------|-----|------|
| Mi8 | rndis0 | 192.168.114.141 | USB RNDIS 侧 |
| Mac en5 | RNDIS Gadget | 从 Mi8 DHCP 获取 | Mac 侧 RNDIS 虚拟网卡通 |
| Mac en8 | AX88772D USB 网卡 | 192.168.50.3 | AX88772D 直连 Mi8 以太网口 |

**注意**：Mac 可能同时看到两个 USB 以太网接口：
- `RNDIS/Ethernet Gadget` → BSD 名 en5，Mac 通过它访问 Mi8
- `AX88772D` USB 网卡 → BSD 名 en8（独立设备，AX88772D 直连 Mi8）

en5 (RNDIS Gadget) 的 MAC 地址有时显示 `(null)`，导致 macOS 无法完成 DHCP 协商。如果 `networksetup -setdhcp` 后仍无 IP，改用手动配置：
```bash
# en5 手动配置静态 IP（与 Mi8 的 192.168.114.141 同段）
sudo networksetup -setmanual "RNDIS/Ethernet Gadget" 192.168.114.142 255.255.255.0 192.168.114.141
```

## Mac 侧网络架构（重要）

Mi8 USB 网络共享场景下，Mac 侧有两层网络路径：

**路径 A**：AX88772D USB 网卡 → 以太网线 → Mi8 以太网口
- Mi8 需要开启「USB 充电」+ 以太网共享
- 物理层：AX88772D 与 Mi8 直接用网线连接
- Mi8 充当 USB 网卡的有线网关，分配 192.168.50.x DHCP

**路径 B**：Mac RNDIS Gadget 接口（en5）→ USB → Mi8 RNDIS
- Mi8 开启 RNDIS USB 网络共享
- Mac 通过 USB 数据线直接访问 Mi8
- Mi8 dnsmasq (PID dns_tether) 分配 192.168.114.x DHCP

**推荐使用路径 A（AX88772D）**，更稳定。路径 B 的 en5 接口在某些 macOS 版本存在 MAC=null DHCP 失效问题。

## 关键检查点

1. **`svc usb setFunctions rndis` 返回 exit:0 但 `ip addr show usb0` 显示 "Device does not exist"**：
   - 正常！Mi8 使用 `rndis0` 而非 `usb0`（Android 版本差异）
   - 查 `ip addr` 而非 `ip addr show usb0`

2. **`ip route show` 显示 "linkdown"**：
   - 正常现象，RNDIS 接口在某些 Android 版本显示 linkdown 但实际通信正常
   - 不要被这个骗了，直接 ping 测试

3. **MAC 地址为 `00:00:00:00:00:01`**：
   - 这是 AX88772D 的默认 MAC，接口可以正常工作（10Mbps）
   - 不要尝试"修复"MAC，这不是问题

4. **Mi8 ping 外网 "Network is unreachable"**：
   - 根因：移动数据未开启（`mobile_data=0`）
   - 解决：`svc data enable`

5. **Mac 侧 RNDIS Gadget (en5) 没有 IP，MAC 显示 (null)**：
   - 根因：CDC RNDIS 驱动的 MAC 读取失败，macOS 无法完成 DHCP
   - 解决：手动 `networksetup -setmanual` 配置静态 IP
   - 或使用 AX88772D 路径（A）代替，更稳定

6. **移动数据要花钱，用户不想走 4G**：
   - 确认 Mi8 移动数据状态：`adb shell settings get global mobile_data`
   - 若要 Mi8 完全走 Mac WiFi：在 Mac 上开启「互联网共享」并关闭 Mi8 移动数据 `svc data disable`

## Mac 侧 USB 网络接口诊断

```bash
# 列出所有 USB 网络设备（包含 Mi8）
system_profiler SPNetworkDataType 2>/dev/null | grep -B1 -A 6 "RNDIS\|AX88\|Ethernet Gadget"

# 查找 Mi8 USB gadget 驱动
ioreg -p IOService -l 2>/dev/null | grep -E "Xiaomi|RNDIS|Ethernet Gadget|USB Product Name" | head -20

# 检查 Mi8 dnsmasq DHCP 服务是否在跑
adb -s a6520fa3 shell "ps -A | grep dns_tether"
# 应显示：dnsmasq

# 检查 dnsmasq 监听的 UDP 端口（67 = DHCP）
adb -s a6520fa3 shell "netstat -lnup 2>&1 | grep :67"
# 应显示 com.android.networkstack.process 监听 0.0.0.0:67
```

## 参考命令速查

```bash
# 完整诊断（Mac 侧）
system_profiler SPUSBDataType 2>/dev/null | grep AX88772D
system_profiler SPNetworkDataType 2>/dev/null | grep -B1 -A 8 "USB\|AX88"
ifconfig en8
ifconfig en5
ipconfig getpacket en8
curl -s --interface en8 https://ipinfo.io/json --max-time 8

# 完整诊断（Mi8 侧）
adb -s a6520fa3 shell "ip addr show rndis0"
adb -s a6520fa3 shell "ip route show"
adb -s a6520fa3 shell "svc usb getFunctions"
adb -s a6520fa3 shell "ping -c 2 -W 3 8.8.8.8"
adb -s a6520fa3 shell "svc data disable"  # 关闭移动数据（省钱）
```