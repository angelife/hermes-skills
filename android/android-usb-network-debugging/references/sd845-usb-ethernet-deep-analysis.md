# SD845 (Xiaomi Mi8) USB Ethernet — Deep Analysis

> 2026-07-01 会话积累：覆盖 RTL8152/RTL8153/AX88772D/AX88179 四种芯片在 Mi8
> (dipper, LineageOS 22.2, kernel 4.9.337) 上的完整诊断。

---

## 1. 硬件前提：Mi8 USB-C 是 USB 2.0 的

**关键事实**：Xiaomi Mi 8 的 USB-C 口**只走了 USB 2.0 信号线**（D+/D-），没有焊接
SuperSpeed（SSTX/SSRX）差分对。

- SD845 的 DWC3 控制器本身支持 USB 3.1 Gen 1（5 Gbps）
- 小米为了节省 PCB 布线和屏蔽成本，省略了 USB 3.0 信号线
- 这是 2018 年前后多数厂商的常规操作（同期的 OnePlus 6、小米 8 都是 USB 2.0-only）

**影响**：
- 以太网卡不论千兆还是百兆芯片，都只能走 **USB 2.0 High-Speed（480 Mbps 理论）**
- 实际 USB 2.0 有效吞吐上限约 **280–330 Mbps**（受协议开销限制）

**验证方法**：

```bash
# 检查是否检测到 SuperSpeed 能力
adb shell "cat /sys/bus/usb/devices/usb1/speed"
# 480 = USB 2.0 High-Speed，5000 = USB 3.0 SuperSpeed
```

---

## 2. 瓶颈分析：280 Mbps 上限的真正原因

**不是 USB 2.0 带宽不够**——480 Mbps 理论带宽给 ~350 Mbps 实际以太网绰绰有余。
**真正的瓶颈是两层叠加**：

### 2.1 软件层：软中断钉死在 Core 0（小核）

- 网络收发产生大量硬件中断（IRQ）
- Android 4.9 内核的调度策略默认将网络软中断（softirq）绑定在 Core 0
- Core 0 是 SD845 的小核（Cortex-A55 @ 1.8 GHz），算力有限
- 千兆大流量下，`%si`（softirq CPU 占用）瞬间吃满 Core 0
- CPU 在中断上下文和进程上下文之间频繁切换，有效吞吐骤降

**验证**：

```bash
# 观察 CPU 软中断是否占满
top -b -n 1 | head -10
# 关注 %si（softirq）列，如果 Core 0 接近 100% → 瓶颈实锤

# 查看中断分布
cat /proc/interrupts | grep eth0
# 观察中断次数是否全堆在某个核心上
```

### 2.2 物理层：USB 2.0 的终结

即使绕过软中断，USB 2.0 的 480 Mbps 带宽减去协议开销后，对千兆芯片来说始终是个盖子。

**结论**：在 Mi8（kernel 4.9）上，任何千兆 USB 网卡在纯测速时都会卡在
**200–400 Mbps**。这不是网卡问题，是手机平台的天花板。

---

## 3. 芯片组兼容性矩阵（实测 + 社区验证）

| 芯片组 | 驱动 | 内核 4.9 兼容 | 实际速度 | 主要问题 |
|---|---|---|---|---|
| **RTL8152** | `r8152`（内置旧版） | ✅ 识别 | ~700 KB/s (5.6 Mbps) | Rx status -71 USB 协议错误 |
| **RTL8152B** | `r8152`（百兆新版） | ✅ PID 完整 | ~95 Mbps | ✅ 最稳定百兆选项 |
| **RTL8153** | `r8152`（缺 PID） | ❌ 不识别 | — | 4.9 内核的 r8152 不含 8153 USB ID |
| **RTL8153B** | `r8152`（缺 PID） | ❌ 不识别 | — | 同 RTL8153 |
| **AX88772D** | `asix`（缺 PID） | ❌ 不工作 | — | 4.9 内核的 asix 不含 88772D PID |
| **AX88772A/B** | `asix` | ✅ PID 完整 | ~95 Mbps | 另一个稳定的百兆选项 |
| **AX88179/A** | `ax88179_178a` | ✅ 免驱 | ~280 Mbps | ⚠️ Linux 圈黑历史：高负载断连 |

### 3.1 RTL8152 Rx status -71 根因

```
dmesg | grep "Rx status"
# r8152 ...: Rx status -71
```

- `-71` = `-EPROTO`（Linux USB 协议错误）
- 旧版 `r8152` 驱动对 USB 批量传输处理有 bug，在接收端报 EPROTO
- **过 Hub 后放大**：直插 ~700 KB/s → 过 Hub ~5–13 KB/s（几乎断流）
- Mac 上不受影响（macOS 用不同驱动栈）

### 3.2 AX88179 高负载断连（ax88179_178a 驱动黑历史）

- Linux kernel.org Bugzilla 和 Arch/Ubuntu 社区有多起 "disconnect under heavy load" 报告
- 根因：大流量下 FIFO 缓冲区溢出或 tx_fixup/rx_fixup 边界漏洞 → 网卡固件死锁
- 4.9 内核的 ASIX 驱动很旧，没吃到 5.x/6.x 的重构修复
- 断连后需要**物理拔插**才能恢复

### 3.3 Hub 倍增效应

USB 2.0 Hub（Genesys 0608）插入 RTL8152 和 Mi8 之间时，性能会**数量级地恶化**：

| 链路 | 速度 |
|---|---|
| RTL8152 直插 Mac | 6.97 MB/s (55.8 Mbps) ✅ |
| Hub → Mac | 5.44 MB/s (43.5 Mbps) ✅ |
| RTL8152 直插 Mi8 | 702 KB/s (5.6 Mbps) ❌ |
| Hub → Mi8 | 5–13 KB/s ❌ |

根因：4.9 内核的 USB 驱动对 split transaction 处理差 + Hub 增加延迟 → 旧驱动暴露
更多协议错误。

**规则**：在 Mi8 上，测试 USB 网卡时永远先**跳过 Hub 直插手机**，排除 Hub 因素。

---

## 4. 推荐方案

### 方案 A：百兆 RTL8152B 或 AX88772A/B（最稳）

```
适用场景：挂机、远程控制、串流、车机、老设备共享
投入：几十块
速度：~95 Mbps
优势：
  - 100 Mbps 的中断吞吐不高，Core 0 小核能轻松处理
  - 功耗极低，手机不发热
  - PID 在 4.9 内核中完整，免驱率高
  - 旧内核的`r8152`驱动虽然旧，但 RTL8152B (带 B 后缀) 固件层面有改进
```

### 方案 B：USB Tethering（零成本满速）

```
适用场景：Mi8 连电脑或带 USB 口的路由器
速度：~400+ Mbps
原理：
  - 走的不是第三方网卡驱动，而是高通调优过的 RNDIS/CDC-NCM
  - 直接走高通硬件 DMA，绕过 CPU 软中断瓶颈
  - 手机端是虚拟网卡，不受 USB 兼容性问题影响
配置：
  手机设置 → 移动网络/连接与共享 → 开启"USB共享网络"
```

### 方案 C：AX88179（上限最高但稳定存疑）

```
只在需要 >100 Mbps 且不能走 USB Tethering 时考虑
预期 ~280 Mbps（受 USB 2.0 + softirq 双重限制）
注意避免高负载持续传输（掉线风险）
```

---

## 5. 系统化诊断流程

当遇到 Android USB 网卡问题时：

```
1️⃣ 确认物理连接
   - USB 设备树（lsusb / sys/bus/usb/devices）
   - 是否是直插还是过 Hub（路径 1-1 vs 1-1.x）
   - USB 口版本（cat /sys/bus/usb/devices/usb1/speed → 480 还是 5000）

2️⃣ 检查链路层
   - ethtool eth0 / cat /sys/class/net/eth0/* (speed, duplex, carrier)
   - 网卡统计：tx_errors, rx_errors, collisions

3️⃣ 扫描 dmesg 错误
   - "Rx status"（EPROTO）
   - "carrier off/on"（链路闪断）
   - "reset"（驱动复位）

4️⃣ 测吞吐（对比基线）
   - 直插 Mac 测 → 网卡硬件本身是否正常
   - 直插手机测 → 排除 Hub 因素
   - 逐层对比确定问题层

5️⃣ 检查系统瓶颈
   - top 看 %si（softirq）是否打满 Core 0
   - cat /proc/interrupts 看中断分布
   - USB 电源状态（power/control, usbin-uv 欠压中断）
```
