# ASIX AX88772D 实际诊断记录

## 设备信息
- USB Product Name: AX88772D
- USB Vendor: ASIX (idVendor=2965)
- idProduct: 6032
- USB 地址: 13，端口 2
- USB 版本: 2.0 Full Speed

## 诊断过程与结果

### ioreg 输出
```
+-o AX88772D@14200000  <class AppleUSBDevice, id 0x1000027d0>
    "USB Product Name" = "AX88772D"
    "USB Vendor Name" = "ASIX"
    "iSerialNumber" = 3
    "kUSBSerialNumberString" = "00000001"
```

### 网络服务注册（双接口现象）
macOS 可能为同一物理设备注册两个服务名：
- 服务名 A: "USB 10/100/1000 LAN" → BSD 设备 en7
- 服务名 B: "AX88772D" → BSD 设备 en8

两个服务都存在，但**两者 MAC 都为 (null)**，意味着接口创建全部失败。

验证命令：
```bash
system_profiler SPNetworkDataType 2>/dev/null | grep -B1 -A 10 "USB 10/100/1000\|AX88772D"
# 两个 Block 分别对应两个服务
```

### kextstat 驱动
- `com.apple.driver.usb.cdc.ecm` ✅ 加载（驱动正常）
- `com.apple.driver.usb.cdc.ncm` ✅ 加载

### MAC 地址问题（根因）
```
networksetup -getinfo "USB 10/100/1000 LAN"
→ Ethernet Address: (null)  ← 驱动读到的是空 MAC

networksetup -getinfo "AX88772D"
→ Ethernet Address: (null)  ← 同上
```

### ifconfig
- `en7 not present` — macOS 无法初始化接口，因为 MAC 为空
- 注意：设备间歇性出现时，en7 可能短暂存在然后被 configd 移除

### log show 追踪（configd EAPOLController）
```
2026-06-26 21:56:06 configd: EAPOLController: en7 is no longer configured, stopping to monitor
2026-06-26 21:56:07 configd: EAPOLController: en7 is no longer configured, stopping to monitor
```
持续出现说明 en7 曾短暂存在随后被移除，或设备消失后 configd 仍在清理缓存。

## 结论

- 早期（固件损坏）：MAC=null → 接口无法创建，设备完全消失
- 本次（固件部分恢复）：MAC=`00:00:00:00:00:01` → 接口创建成功，10Mbps 速率

最可能原因（针对 AX88772D）：
1. 固件 MAC 数据区间歇性损坏 → 表现为 MAC=null 时完全失效
2. 固件部分恢复后使用默认 MAC → 接口可工作但速率受限（USB 2.0 FS = 12Mbps 实际 ~10Mbps）
3. 适配器本身硬件问题（Flash/EEPROM 损坏）

**处理：设备能工作后持续观察，如果 MAC 再次变 null → 换适配器。**