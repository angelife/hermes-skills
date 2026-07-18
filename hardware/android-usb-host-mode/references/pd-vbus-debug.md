# PMIC VBUS 供电诊断 — Android USB Type-C Host 供电层

## 问题模型

Android 手机通过 Type-C 口向外设（USB 网卡/U盘/键盘）供电时，需要三步：

```
Type-C CC 检测 Sink → PD PHY 触发 Role Switch → PMIC VBUS regulator 使能 → DWC3 切 Host → XHCI 枚举
```

**关键区分：** `Source_Capabilities: -14` + PDO=0 不一定阻止枚举。只要 VBUS regulator 使能默认 Type-C 500mA，设备可在 USB 2.0 HS 下枚举无误。PD 协商失败是**恒存噪音**而非根因。

## PMIC 供电链（SD845/PMI8998 为例）

```
qpnp-smb2 (主充电器, SPMI 0-02)
  ├─ regulator.84: smb2-vbus       ← OTG VBUS 输出 (关键)
  └─ regulator.85: ...
ext_5v_boost (reg-fixed-voltage)   ← 外部 5V boost (通常 disabled, 非主因)
```

### 关键 syfs 节点

| 路径 | 含义 | 可写性 |
|------|------|--------|
| `/sys/class/regulator/regulator.84/state` | smb2-vbus 状态 | ro |
| `/sys/class/regulator/regulator.84/num_users` | 投票者数 | ro |
| `/sys/class/power_supply/usb/boost_current` | OTG boost 电流值, 0=disabled | ro |
| `/sys/class/power_supply/usb/typec_power_role` | 当前角色 (sink/source) | ro |
| `/sys/class/dual_role_usb/otg_default/mode` | 双角色模式 (ufp/dfp) | **w** |
| `/sys/devices/platform/vendor/vendor:ext_5v_boost/regulator/regulator.86/state` | ext_5v_boost 状态 | ro |

### votable 框架（QTI 标准电源投票机制）

高通 PMIC 的 VBUS 使能通过 votable 框架实现。多个投票者（`OTG_VOTER`, `BOOST_BACK_VOTER`, `WEAK_CHARGER_VOTER`, `USB_PSY_VOTER`）各自投票，框架取最大值/叠加值。

**调试接口（需 kernel config）：**

| 接口 | 依赖 |
|------|------|
| `/sys/kernel/debug/pmic-votable/OTG_VOTER` | `CONFIG_PMIC_VOTABLE_DEBUG` |
| `/sys/kernel/debug/regulator/smb2-vbus/consumers` | `CONFIG_REGULATOR_DEBUG` |
| `/sys/kernel/debug/regulator/summary` | `CONFIG_REGULATOR_DEBUG` |

**LineageOS 4.9 kernel 上通常全关** — 无法直接查看投票状态。

## 诊断流程

### Phase 0: 区分 PD 噪音 vs VBUS 缺失

```dmesg
# 设备枚举了但 PD 失败（VBUS 在）——设备可工作
[ 2198.621] usbpd usbpd0: Error sending Source_Capabilities: -14   ← 噪音
[ 2198.760] usb 1-1: new high-speed USB device number 2            ← 枚举成功

# 设备未枚举 + PD 失败（VBUS 缺失）——需要修供电层
[ 816.022] usbpd usbpd0: Error sending Source_Capabilities: -14    ← 噪音
[ 831.439] msm-dwc3: DWC3 in low power mode                        ← 无枚举，放弃
```

**判断信号：** `usb 1-1: new high-speed USB device number N` 出现 = VBUS 到位。不出现 = regulator 没被 vote 打开。

### Phase 1: 诊断（只读优先）

```bash
# 1. regulator 状态
for r in smb2-vbus ext_5v_boost; do
  NAME=$(cat /sys/class/regulator/*/name 2>/dev/null | grep $r)
  [ -z "$NAME" ] && continue
  REG=$(find /sys/class/regulator -name "regulator.*" | while read d; do
    [ "$(cat $d/name 2>/dev/null)" = "$r" ] && echo $d
  done)
  echo "$r: state=$(cat $REG/state 2>&1) users=$(cat $REG/num_users 2>&1)"
done

# 2. power_supply 关键状态
for f in boost_current online present typec_mode typec_power_role pd_active current_max; do
  echo "usb/$f: $(cat /sys/class/power_supply/usb/$f 2>&1)"
done

# 3. dual_role_usb 能力（是否支持 dfp）
cat /sys/class/dual_role_usb/otg_default/supported_modes
cat /sys/class/dual_role_usb/otg_default/mode

# 4. 尝试读 votable/regulator debug（不存在也正常）
find /sys/kernel/debug/regulator /sys/kernel/debug/pmic-votable -name "*vbus*" -o -name "*boost*" -o -name "*OTG*" 2>/dev/null

# 5. USB HAL 检查
getprop | grep -E "init\\.svc\\.(vendor\\.usb-hal|vendor\\.usbgadget)"
```

### Phase 2: 系统服务检查

```bash
# USB HAL 状态
for svc in vendor.usb-hal-1-3 vendor.usbgadget-hal; do
  echo "$svc: $(getprop init.svc.$svc)"
done
```

### Phase 3: 强制切换（谨慎 — 会影响充电/ADB）

```bash
# 方法 A: dual_role_usb（最安全的用户态入口）
echo dfp > /sys/class/dual_role_usb/otg_default/mode

# 方法 B: DWC3 mode（效果取决于 extcon 链路是否活着）
echo host > /sys/devices/platform/soc/*.ssusb/mode
```

### Phase 4: 如果上述都失败

- USB3 外设（如 AX88179 Gigabit Ethernet）可能需要 900mA 供电
- Type-C default USB 2.0 仅提供 500mA — 可能只够枚举不够稳定运行
- 考虑硬件方案：带外部供电的 USB OTG Y 线

## 常见模式匹配

| dmesg 模式 | 含义 | 行动 |
|------------|------|------|
| `Error sending Source_Capabilities: -14` + `usb 1-1: new device` | PD 噪音，VBUS 正常 | 忽略 PD，问题不在供电层 |
| `Error sending Source_Capabilities: -14` + 无 `usb 1-1: new device` | PD 噪音 + VBUS 缺失 | 查 regulator/votable |
| `Avail curr from USB = N` (N < 500) | USB 控制器感知的供电电流受限 | 供电不足，需外部供电 |
| `Failed to read reg index 0x0040: -32` | VBUS 存在但 USB3 信号不稳定(EPIPE) | 供电不足或信号完整性 |
| `Failed to read reg index 0x0002: -19` | 设备完全无响应(ENODEV) | 供电严重不足或硬件损坏 |
| `Reverse boost detected: voting 0mA` | PMIC 检测到反向电流，暂停输入 | 可能 latch 住输入侧，需排查充电器状态 |

## 已知限制

- LineageOS 4.9 kernel 通常 `CONFIG_REGULATOR_DEBUG` 和 `CONFIG_PMIC_VOTABLE_DEBUG` 未开启，debugfs 不可用
- `usb/boost_current` 是只读指标，不是控制入口
- `otg_enable` / `boost_enable` 标准节点在 PMI8998 qpnp-smb2 驱动中不存在（由 votable 框架替代）
- `usbpd0/pd_vbus` 和 `hard_reset` 节点存在但读写行为不可预测，非正规入口
