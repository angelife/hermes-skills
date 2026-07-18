# USB 网卡间歇性消失诊断

## 问题描述

USB 网卡在 macOS 中间歇性出现/消失：system_profiler 能看到设备，但 `ifconfig` 无对应接口；networksetup 能看到服务名，但 MAC 为 null。

## 典型症状

1. `system_profiler SPNetworkDataType` 显示 "USB 10/100/1000 LAN"（en7）存在
2. 但 `ifconfig` 输出中没有 en7/en8
3. `networksetup -getinfo "USB 10/100/1000 LAN"` 显示 `Ethernet Address: (null)`
4. `log show` 可见 configd 的 EAPOLController 在不断移除 en7

## 诊断命令

```bash
# 检查 USB 总线是否有设备
system_profiler SPUSBDataType 2>/dev/null | grep -i "asix\|ax88\|ethernet\|cdc"

# 检查网络服务注册（两套名字都可能）
system_profiler SPNetworkDataType 2>/dev/null | grep -B1 -A 8 "USB 10/100/1000\|AX88772D"

# 查 MAC 地址（关键检查）
networksetup -getinfo "USB 10/100/1000 LAN" 2>/dev/null | grep "Ethernet Address"
networksetup -getinfo "AX88772D" 2>/dev/null | grep "Ethernet Address"

# 用 log 追踪 en7 消失过程
log show --predicate 'eventMessage CONTAINS[c] "en7" OR eventMessage CONTAINS[c] "EAPOLController"' --last 5m

# 查驱动是否加载
kextstat | grep -i "cdc.ecm\|cdc.ncm\|realtek"
```

## 两种失败模式

### 模式 A：服务缓存残留
`system_profiler SPNetworkDataType` 显示服务名，但接口从未真正初始化。
- 原因：macOS 缓存了 USB 设备的网络服务注册，但设备固件 MAC 读取失败，导致接口创建失败
- 特征：服务名存在，`ifconfig` 无对应接口，MAC 显示 (null)

### 模式 B：设备间歇性掉线
设备能正常初始化，随后消失。
- 原因：USB 供电不足、线材不良、接触不良、设备固件 bug
- 特征：设备短暂出现后消失，重复"再试试看"（重新插拔）可复现
- 日志表现：configd 的 EAPOLController 持续报告 "en7 is no longer configured, stopping to monitor"

## 根因

MAC 地址读取失败（显示 null）是绝大多数 USB 网卡无法工作的根因。即使 `com.apple.driver.usb.cdc.ecm` 已加载、即使 ioreg 能看到设备，MAC 读不到就意味着无法创建网络接口。

MAC 为 null 的常见原因：
1. 适配器固件损坏或 Flash 损坏
2. USB 供电不足（FS 而不是 HS）
3. 线材质量差
4. 设备本身硬件故障

## 处理

```
1. 换 USB 口（优先靠后的口，供电更足）
2. 换一根 USB 线（网卡的线最容易坏）
3. 断电重插（拔掉等 10 秒再插）
4. 换电源（有些 Hub 供电不足）
5. 换适配器（以上都无效 = 硬件故障）
```

## 重要例外：非 null MAC 也能工作

本技能假设"设备存在但 MAC=null → 接口失败"是主要故障模式。但有一种例外：

**即使 MAC 是伪造地址（如 `00:00:00:00:00:01`），接口仍然可以 UP 并正常工作。**

本次会话实际案例（2026-06-26）：
- 设备重新插上后，MAC 变为 `00:00:00:00:00:01`
- `ifconfig en8` → `status: active`，协商 10baseT/UTP full-duplex
- `ping 8.8.8.8` 成功，curl 通过该接口出网正常
- `ipconfig getpacket en8` 显示：IP=`192.168.50.3`，网关=`192.168.50.1`（Mi8 的以太网共享）
- 注意：接口状态显示 `linkdown` 但物理上 ping 仍通（USB RNDIS 特性）

**判断标准**：MAC 为 (null) → 一定失败；MAC 为任意值（包括伪造）→ 尝试启用，可能成功。

## 本次会话诊断结果（2026-06-26）

- ASIX AX88772D：设备重新出现，MAC=`00:00:00:00:00:01`
- 注册两个服务："USB 10/100/1000 LAN"(en7) 和 "AX88772D"(en8)
- en8 拿到 DHCP IP 192.168.50.3，网关 192.168.50.1
- en8 出网 IP：223.167.62.2（上海联通，走 Mi8 4G 共享）
- 物理速率：10Mbps 半/全双工（USB 2.0 FS 限制）
- Mi8 型号：dipper（a6520fa3），LineageOS，已开启 RNDIS USB 网络共享