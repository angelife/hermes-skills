---
name: macos-usb-hardware-debug
description: macOS USB 硬件调试 — 网卡、声卡、串口等外设的四层诊断法
triggers:
  - "检查 USB"
  - "USB 网卡"
  - "USB 硬件"
  - "USB 设备识别"
  - "check usb"
---

# macOS USB 硬件调试

macOS 系统上 USB 设备诊断的标准流程，覆盖网卡、声卡、串口等外设。

## 触发条件

用户问"检查 USB 硬件"、"USB 网卡好的坏的"、"USB 声卡能用吗"、"USB 设备识别了吗"时加载。

## 诊断流程（四层）

### 第一层：USB 总线层

```bash
# 列出 USB 设备树，找设备名/VendorID
ioreg -p IOUSB -l | grep -A 10 "USB Product Name\|idVendor\|idProduct"

# 或者用 system_profiler（更简洁）
system_profiler SPUSBDataType 2>/dev/null | grep -A 8 "USB "
```

### 第二层：网络/设备服务层

找到 USB 设备后，查询 macOS 网络服务注册：

```bash
# 列出所有网络服务，找到 USB 相关项
networksetup -listallnetworkservices

# 查网络服务顺序（含 BSD 设备名）
networksetup -listnetworkserviceorder | grep -A 2 "USB"

# 验证服务状态
networksetup -getnetworkserviceenabled "USB 10/100/1000 LAN"
```

### 第三层：内核驱动层

检查驱动是否加载：

```bash
kextstat | grep -i "cdc\|realtek\|asix\|axe\|ax88\|cdc.ecm\|cdc.ncm"
```

常见驱动：  
- `com.apple.driver.usb.cdc.ecm` — 通用 CDC-ECM 驱动，**RTL8152** (USB 10/100 LAN)、ASIX AX88772 等芯片用  
- `com.apple.driver.usb.realtek8153patcher` — **RTL8153** (USB 3.0 Gigabit) 专用补丁  
- `com.apple.driver.usb.cdc.ncm` — NCM 协议

**RTL8152 vs RTL8153 说明**：RTL8153 有 Apple 官方驱动补丁（`realtek8153patcher`），但 RTL8152（0bda:8152，百兆）没有专用 ktext — macOS 通过内置 `usb.cdc.ecm` 驱动识别。所以 `kextstat` 里看不到 RTL8152 的独立条目是正常的。

### 第四层：网络接口层

找到 BSD 设备名后检查接口状态：

```bash
# 从 networkserviceorder 输出知道 BSD 名后：
ifconfig en7   # 或 en3/en4 等

# 检查 MAC 地址（关键！null = 驱动/固件问题）
networksetup -getinfo "USB 10/100/1000 LAN" | grep "Ethernet Address"
# 或者：
networksetup -listallhardwareports | grep -A 1 "USB 10/100"
```

### 第四层半（关键！）：检查 IP 配置模式

在查接口状态前先看 IP 配置模式——**这是 USB 网卡插上后 `status=inactive` 的最常见陷阱**：

```bash
# 查 IP 配置模式（Manual vs DHCP）
networksetup -getinfo "USB 10/100 LAN"

# 如果返回 "Manual Configuration" + 旧 IP，说明上一个设备（如 Android RNDIS/USB 共享）
# 留下的静态 IP 写死了，必须改为 DHCP！
networksetup -setdhcp "USB 10/100 LAN"
```

**典型场景**：之前用 Android 手机的 RNDIS USB 网络共享，系统自动创建了一个手动 IP 配置（常见 192.168.45.x 网段）。下次插上普通 USB 以太网适配器时，macOS 复用这个老配置 → 接口 `status=inactive`。改 DHCP 后立即恢复。

**注意**：服务名不一定是固定的 `"USB 10/100 LAN"` — 先用 `networksetup -listallhardwareports` 确认准确的名字。

## 常见故障判断

| 症状 | 根因 | 处理 |
|------|------|------|
| USB 口识别到，MAC=null | 固件/驱动问题，MAC 没读到 | 换适配器、断电重插 |
| enX 接口存在但 status=inactive + media=none | 网线没插或协商失败 | 检查物理连接 |
| enX 接口存在但 status=inactive + media=100baseTX | **IP 配置模式是 Manual**（遗留静态 IP） | `networksetup -setdhcp "USB 10/100 LAN"` |
| networksetup 显示 (null) MAC | 驱动未正确初始化 | kextload 或重插 |
| USB 设备完全不出现 | 硬件/供电/线材问题 | 换 USB 口/线/设备 |

## 关键检查点

1. USB 设备是否在 IOUSB 树中（第一层）
2. macOS 网络服务名是否存在（第二层）
3. 驱动 kext 是否加载（第三层）
4. MAC 地址是否为空（第四层）— **这是网卡不能用的最常见根因**

## 参考实例

- `references/asix-ax88772d-diagnostic.md` — ASIX AX88772D 完整诊断记录（含 MAC=null、en7/en8 双接口、log show configd 追踪）
- `references/usb-ethernet-intermittent.md` — USB 网卡间歇性消失/重连的诊断技巧
- `references/stale-manual-ip-config.md` — 遗留手动 IP 配置导致 USB 网卡 `status=inactive` 的完整排查流程\n- `references/usb-wifi-kext-install.md` — USB WiFi 网卡第三方驱动安装与 macOS kext 审批流程（Realtek 芯片）

## 陷阱

- 不要只看 `ifconfig` — enX 可能存在但 MAC 为空（`ifconfig en7` 不报错但网络不通）
- `networksetup -getinfo "USB 10/100/1000 LAN"` 返回的 Ethernet Address 为 `(null)` 就是 MAC 丢失
- 驱动 kext 存在 ≠ 工作正常，需要同时验证 MAC 地址
- 同一物理 USB 网卡可能注册**两个**网络服务（如 en7 + en8），两者 MAC 可能都为 null，分别对应不同服务名
- `system_profiler SPNetworkDataType` 看到服务名 ≠ 接口真的起来了，macOS 可能只是缓存了服务注册信息
- 当 USB 网卡间歇性消失时，用 `log show --predicate 'eventMessage CONTAINS[c] "en7"' --last 5m` 追踪 configd 的 EAPOLController 日志，可以看见 en7 何时被移除