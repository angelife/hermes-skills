# AX88179 USB-C Gigabit Ethernet 调试实录

## 案例背景

设备：Mi8 (dipper, SD845, LineageOS 22 / Android 15 / kernel 4.9.337-perf)
外设：AX88179 USB 3.0 Gigabit Ethernet 网卡（VID:PID `0b95:1790`）

用户目标：让 Mi8 通过 Type-C 直插 AX88179 网卡实现有线网络。

## 重要结论

### 芯片识别

| 项目 | 值 |
|------|-----|
| VID:PID | `0b95:1790` |
| 实际芯片 | **AX88179**（USB 3.0 Gigabit Ethernet） |
| 非 AX88772D | 旧款 ASIX 芯片（AX88772A/B）为 `0b95:7720/b`，是 USB 2.0 Fast Ethernet |
| 正确驱动 | `ax88179_178a`（**并非** `asix`） |

**0b95:1790 被错误归因为 AX88772D 是常见的互联网资料陷阱。**

### 驱动绑定验证

经过 `nohup` 后台捕获验证，PD PHY 正确触发 host 模式后，`ax88179_178a` 驱动自动绑定了 AX88179：

```
dmesg:
  ax88179_178a 1-1:2.0 eth0: unregister ... ASIX AX88179 USB 3.0 Gigabit Ethernet
```

驱动自身的 log 确认了芯片型号。**不存在驱动冲突**——`ax88179_178a` 是唯一正確驅動。

### 根因：供电不足

设备被枚举并绑定正确驱动后 **仍无法工作**：

| 症状 | 解释 |
|------|------|
| `Failed to read reg index 0x0002: -19` | ENODEV — 设备无响应 |
| `Failed to read reg index 0x0002: -32` | EPIPE — 控制传输中断，USB3 供电/信号完整性失败 |
| ethtool 返回 `driver: ax88179_178a` 但 PHY 状态异常 | 驱动已绑定但硬件初始化失败 |
| MAC 地址全零 `00:00:00:00:00:01` | EEPROM 读取中断，使用 fallback 地址 |
| `NO-CARRIER` | PHY 层链路未建立 |

**原因：** USB3 Gigabit Ethernet（AX88179）的 bMaxPower 需求超过 Mi8 Type-C 口在 OTG/Sink 模式下能提供的电流。PD PHY 报告的 `Avail curr from USB = N`（N 过小）时为设备供电受限的确凿证据。

### 诊断方法

在 Mi8 只有一个 Type-C 口（ADB 与网卡互斥）的情况下，用 `nohup sh -c "..."` 内联模式实现拔线捕获：

```bash
dmesg -c > /dev/null
nohup sh -c "sleep 25; dmesg -c > /data/local/tmp/cap.txt" > /dev/null 2>&1 &
# 用户拔 ADB → 插网卡 → 等 25 秒 → 拔网卡 → 插回 ADB
cat /data/local/tmp/cap.txt
```

关键 dmesg 时间线（成功触发 host 模式的完整序列）：

```
t=0    USB Type-C disconnect          ← 用户拔 ADB 线
t=4s   Type-C Sink connected           ← 用户插 AX88179
       DWC3 exited low power mode       ← DWC3 唤醒
       xHCI Host Controller 启动        ← XHCI 初始化
       USB bus 1 & 2 注册
       hub 1-0:1.0: 1 port detected
t=~8s  usb 1-1: 设备枚举              ← AX88179 被检测
       ax88179_178a 绑定 → eth0/eth1
       Failed to read reg index: -19   ← 供电不足，probe 失败
t=37s  usb 1-1: USB disconnect          ← 用户拔网卡
       ax88179_178a eth0/eth1 unregister
```

### 可复现性

- **PD PHY host 模式可触发但不是 100%**：在测试中约 1/4 的插拔能触发 DWC3 host 模式激活，另 3/4 次 PD PHY 无响应（dmesg 零 USB 事件）。
- **状态机粘连**：连续的 unbind/rebind 或驱动试验后 PD PHY 可能进入一致性故障状态，需要 **重启设备** 复位 PD PHY。
- **即使 host 模式触发成功**，供电不足导致 probe 失败的缺陷固定存在。

## 无效方案（已验证）

| 方案 | 原因 |
|------|------|
| 写 `asix` 驱动 new_id 并强制 bind | 芯片是 AX88179，`asix` 驱动不兼容 USB3，绑后 MAC 全零 + NO-CARRIER |
| `ax88179_178a` remove_id 移除 0b95:1790 | `remove_id` 不影响 built-in `id_table` |
| watchdog unbind+driver_override+rebind | 即使成功绑定到正确驱动，供电不足仍存在 |
| 写 DWC3 mode = host | PD PHY 硬件状态覆盖软件写入 |
| 各种模式文件写入（dual_role_usb 等） | 同上一—extcon notifier 回调才是唯一有效的角色切换机制 |

## 可行方向

- **使用带外部供电的 USB Type-C 集线器**（供电集线器 → HUB 给 AX88179 供电 → Mi8 仅承担数据角色）
- **换用 USB 2.0 Fast Ethernet 网卡**（如 AX88772A/B `0b95:7720/b`，功耗低，无需 PD 供电协商）
- **USB 2.0 USB-A 转 Type-C OTG 转接线**（可能绕过 PD 协商直接提供 500mA）