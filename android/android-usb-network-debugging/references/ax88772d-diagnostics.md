# AX88772D 验证与调试记录

## 硬件验证（Mac端）

```bash
# 1. 检查USB是否检测到设备
system_profiler SPUSBDataType 2>/dev/null | grep -A 5 "AX88772\|ASIX"
# 期望输出: Product ID: 0x1790, Vendor ID: 0x0b95 (ASIX Electronics Corporation)

# 2. 检查网络服务
networksetup -listallnetworkservices 2>/dev/null | grep -i "ax88\|usb.*10"
# 期望: 看到 "AX88772D" 字样

# 3. 检查en接口（正常应该有新的enX出现）
ifconfig -a 2>/dev/null | grep -E "^en[0-9]"
# 如果没有新的en接口，说明驱动接上了USB但没有创建网络接口

# 4. 检查MAC地址（null=失败）
networksetup -getinfo "AX88772D" 2>/dev/null | grep "Ethernet Address"
# null = macOS CDC-ECM驱动无法创建接口
```

## Mi8端诊断

```bash
# 检查网卡接口
adb -s a6520fa3 shell "ls /sys/class/net/"

# 检查USB设备
adb -s a6520fa3 shell "ls /sys/bus/usb/devices/"

# 检查内核驱动模块
adb -s a6520fa3 shell "ls /sys/bus/usb/drivers/ | grep -i asix"
# 期望: asix 和 ax88179_178a

# 检查dmesg（需要root）
adb -s a6520fa3 shell "dmesg 2>&1 | grep -iE 'usb.*ether|asix|eth[0-9]' | tail -10"
```

## 已知问题：macOS CDC-ECM 不创建en接口

**现象**: system_profiler 能看到设备，networksetup 有 AX88772D，但 `ifconfig` 没有新的 en 接口，Ethernet Address 是 null。

**确认设备硬件正常（最关键的一步）**：
```bash
system_profiler SPUSBDataType 2>/dev/null | grep -A 8 "AX88772D"
# 期望输出:
#   Product ID: 0x1790
#   Vendor ID: 0x0b95  (ASIX Electronics Corporation)
#   Version: 2.00
#   Serial Number: 00000001
#   Manufacturer: ASIX
```

**有 Product/Vendor ID 输出** → **网卡硬件是好的**，问题在 macOS 驱动或 USB 连接稳定性。

**ioreg 确认**：
```bash
ioreg -p IOService -l 2>/dev/null | grep -i "0b95\|1790"
```

**结论**:
- `system_profiler` 有 ASIX 0x1790/0x0b95 输出 → 硬件正常 ✅
- `ifconfig` 没有 en 接口 → macOS CDC-ECM 驱动接上 USB 但未创建网络接口
- `networksetup` 里 Ethernet Address 是 `(null)` → 驱动未完成绑定

**Mi8 端**: 如果网卡插上后 `ls /sys/class/net/` 没有 eth0，先排除：
- USB线接触不良（换一根线，使用高质量 OTG 线）
- OTG供电不足（AX88772D 功耗较大，部分 OTG 方案供电不够）
- 物理连接不稳定（设备间歇性出现/消失）
- Mi8 的 USB-C 必须是 **Host 模式**，不能是连 Mac 时的 Gadget 模式（需要 USB-C OTG Hub）

## Mi8 rmnet_data 接口说明

Mi8 有多个 `rmnet_data` 虚拟接口，通常 `rmnet_data3` 是主移动数据（而非 rmnet_data0）：
```
rmnet_data0: 有 inet6 但没有 IPv4
rmnet_data3: 有 IPv4 地址（10.128.164.15/27） ← 主移动数据
rmnet_data4-10: 状态 DOWN
```
检查哪个有 IPv4：
```bash
adb -s a6520fa3 shell "ip addr show | grep 'inet ' | grep -v '127\|::'"
```