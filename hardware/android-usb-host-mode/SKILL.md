---
name: android-usb-host-mode
description: 诊断和修复 Android 设备 USB 主机模式问题 — DWC3 角色切换、设备枚举、驱动绑定冲突
---

# Android USB Host Mode Troubleshooting

Trigger: 用户想在 Android 手机上使用 USB 外设（网卡/U盘/键盘/串口），设备不工作或无法枚举。

## Key Concepts

### DWC3 Dual Role Switching

Qualcomm SD845/SM8150 等平台的 USB 控制器是 DWC3 + XHCI 的组合。架构上涉及三层：

| 层 | 接口 | 说明 |
|----|------|------|
| **PD PHY 硬件** | /sys/class/extcon/extcon4/state | PMI8998 通过 CC 引脚检测，**只读**，决定谁提供 VBUS |
| **DRP 抽象** | /sys/class/dual_role_usb/otg_default/mode | 双角色管理层，system 可写但可被硬件否决 |
| **DWC3 核心** | /sys/devices/platform/soc/*.ssusb/mode | DWC3 核心模式 (peripheral/host/drp)，root 可写 |

**架构关键发现（dwc3-msm.c 源码印证）：模式切换是由 extcon notifier 回调驱动的，不是直接响应 sysfs mode 写入。**

- `dwc3-msm.c` 中，角色切换靠 `extcon_id`/`extcon_vbus` 的 notifier 回调触发 (`dwc3_otg_set_mode`)
- sysfs `mode` 接口在很多 vendor 内核中只是调试用的**软触发**，调用相同的 `dwc3_otg_set_mode`
- 真正决定角色的是 **PMI8998 通过 PD PHY 上报的 id_state**
- **如果 PMIC 层不产生 host-mode 的 extcon 事件，mode 文件写入形同虚设**

**诊断优先于行动：** 不要先写 mode 文件。先做下面"诊断"流程中的 typec class 探测 + extcon 状态检查，确认硬件检测链路是否活着。

### OTG 自动检测 vs 强制模式

- 当 USB-C 设备插入时，PD PHY（pmi8998/fusb302）通过 CC 引脚检测设备类型
- 如果电话配置为 Try.SNK（优先做设备），即使插入了 UFP-only 外设也可能不切 host
- 某些 ROM 将 DWC3 锁定在 peripheral 模式，OTG 硬件检测不会触发
- **解决方案：** 通过 DWC3 mode 文件强制写 `host`

### Driver Binding Conflicts

当 USB 设备枚举后，内核按驱动注册顺序匹配。如果多个驱动都声明支持同一 VID:PID，先注册的驱动胜出。但 **确认芯片型号优先于解决驱动冲突**——许多 ASIX 系列芯片有相同的 VID:PID 但属于不同产品线。

### 0b95:1790 芯片识别（常见陷阱）

| VID:PID | 芯片 | 类型 | 正确驱动 |
|---------|------|------|---------|
| `0b95:1790` | AX88179 | **USB 3.0 Gigabit Ethernet** | `ax88179_178a` |
| `0b95:7720` / `772a` / `772b` | AX88772A/B | USB 2.0 Fast Ethernet | `asix` |

**⚠️ 0b95:1790 = AX88179，不是 AX88772D。** `asix` 驱动只支持旧款 ASIX 芯片（0b95:772x），不支持 USB3 的 AX88179。`ax88179_178a` 是唯一正确驱动，两者均可 built-in（非模块）。

**修复方案（只在确认芯片型号后用于真正的驱动冲突）：**
```bash
# 预注册 ID 到目标驱动
echo "VID PID" > /sys/bus/usb/drivers/<正确驱动>/new_id

# 设备已枚举后，解绑并重绑定
echo "<USBIF>" > /sys/bus/usb/drivers/<错误驱动>/unbind
echo "<USBIF>" > /sys/bus/usb/drivers/<正确驱动>/bind
```

### `remove_id` sysfs 接口

所有 USB 驱动都支持 `remove_id` 写入口（`/sys/bus/usb/drivers/<name>/remove_id`），但该接口**仅移除通过 `new_id` 动态添加的记录**，**无法移除**驱动编译时静态编译的 `id_table`（USB_DEVICE 宏定义的 ID）。因此对 built-in 的重叠匹配改用 unbind+driver_override。

#### 驱动冲突诊断
```bash
for d in /sys/bus/usb/devices/*/; do
  V=$(cat "$d/idVendor" 2>/dev/null)
  P=$(cat "$d/idProduct" 2>/dev/null)
  [ "$V:$P" = "0b95:1790" ] || continue
  dev=$(basename "$d")
  driver=$(readlink "$d/driver" 2>/dev/null | xargs basename)
  echo "Device $dev: driver=$driver"
  for intf in /sys/bus/usb/devices/"$dev":*/driver; do
    drv=$(readlink "$intf" 2>/dev/null | xargs basename)
    echo "  Interface $(basename $(dirname $intf)): $drv"
  done
done
```

### 供电不足导致 probe 失败

**重要：** 即使驱动匹配正确，USB3 外设（如 AX88179 Gigabit Ethernet）可能因供电不足而 probe 失败。症状：
- dmesg 报 `Failed to read reg index 0x0002: -19`（ENODEV）或 `-32`（EPIPE）
- 接口创建后 MAC 地址全零或无效
- PHY 层无法建立链路（`NO-CARRIER`）
- ethtool 返回异常

```
# -19 (ENODEV): 设备无响应，控制传输超时
# -32 (EPIPE): 控制传输中断（USB3 设备供电/信号完整性问题）
```

**应对策略：**
1. 使用带外部供电的 USB 集线器
2. 确认 PD PHY 是否启用了 VBUS（检查 `msm-dwc3: Avail curr from USB = N` 的行，数字过小说明供电受限）
3. USB3 设备在供电受限时可能降级到 USB2（bMaxPower 仍超限）或完全无响应

## Workflow

### Phase 1: 诊断

**先判定架构可行性 > 再检查状态**

```bash
# 0. 检查 Type-C class（判断 PD 协商层是否存在）
ls /sys/class/typec/                   # 不存在=内核未编译 TYPEC
for p in /sys/class/typec/port*/; do
  cat "${p}data_role" 2>&1
  cat "${p}power_role" 2>&1
  cat "${p}preferred_role" 2>&1
done

# 1. 检查 extcon（硬件角色信号）
cat /sys/class/extcon/extcon4/state     # PD PHY: USB=1 USB_HOST=0 DP=0

# 2. 检查当前 USB 模式
cat /sys/devices/platform/soc/*.ssusb/mode
cat /sys/class/dual_role_usb/otg_default/mode

# 3. 插入瞬间抓 dmesg（物理操作时的 ADB 离线方案）
dmesg -c > /dev/null  # 清空缓冲
# 在后台启动捕获（会在 ADB 断连后继续运行）：
# nohup sh -c "sleep 15; dmesg > /data/local/tmp/dmesg_cap.txt" > /dev/null 2>&1 &
# 然后拔 ADB → 插外设 → 等 15 秒 → 插回 ADB → 读文件
dmesg | grep -iE "usb|extcon|dwc3|typec|pmi8998|cc_state|id_state"

# 4. 检查 USB 设备树（host 模式下才可见设备）
ls /sys/bus/usb/devices/*/idVendor 2>/dev/null

# 5. 检查 dmesg 看驱动绑定
dmesg | grep -iE "usb|dwc3|otg|dfp|ufp|xhci"
```

### Signal Interpretation（收敛判断）

诊断结果决定是否值得继续，以及走哪条路线：

| 诊断信号 | 判断 | 下一步 |
|----------|------|--------|
| `/sys/class/typec/` **不存在** | 内核未编译 `CONFIG_TYPEC`，PD PHY 无软件入口 | 跳过 extcon PD PHY 操作（A 方案），考虑硬件方案 |
| `/sys/class/typec/` 存在且可写 preferred_role | PD 协商层有接口 | 优先尝试写 `preferred_role=source` |
| **dmesg 插入后无任何** usb/extcon/dwc3/typec 行 | 硬件检测中断未触发，CC 线检测被固件屏蔽 | 软件方案成功率极低，转向硬件方案或放弃 |
| **dmesg 有 extcon 事件**但模式未切换 | 检测到了但角色仲裁拒绝切换 | typec class preferred_role 可写性是关键突破口 |
| extcon4 state 为 `USB=1 USB_HOST=0` 且不可变 | PD PHY 锁定 UFP 模式 | DWC3 mode 文件写入大概率无效 |
| **dmesg 有 extcon 事件** → DWC3 唤醒 → XHCI 启动 → 设备枚举 | **PD PHY 正确触发 host 模式** | 问题不在此层，跳转检查驱动绑定和供电 |
| **dmesg 有 extcon 事件** → DWC3 唤醒 → XHCI 启动 → `Error sending Source_Capabilities: -14` → **有** `usb 1-1: new device` | PD 噪音 + VBUS 到位 | 忽略 PD 错误，检查驱动绑定即可 |
| **dmesg 有 extcon 事件** → DWC3 唤醒 → XHCI 启动 → `Error sending Source_Capabilities: -14` → **无** `usb 1-1: new device` | PD 噪音 + VBUS 缺失 | 查 PMIC regulator (`smb2-vbus`/`ext_5v_boost`) 和 votable 框架 |
| dmesg 报 `Failed to read reg index 0x0002: -32` | 供电不足（EPIPE — USB 控制传输中断） | 需外部供电集线器；不是驱动问题 |
| dmesg 报 `Failed to read reg index 0x0002: -19` | 设备无响应（ENODEV — 控制传输超时） | 同上，供电不足或硬件损坏 |

**收敛路径：**
- 有 typec class + 有 extcon 事件 → 尝试 A（软件 PD PHY 操作）
- 无 typec class + 无 extcon 事件 → 走 D（硬件 OTG Y 线/供电集线器）
- 无 typec class + 无 extcon 事件 + 无硬件方案 → **此设备 USB host 模式不可行**

### Phase 2: PMIC VBUS 供电诊断

**在尝试强制 Host 模式之前，先确认 VBUS regulator 是否被 votable 框架使能。** PD 错误 (`-14`) 和 PDO=0 是噪音，不要据此判断供电状态。

```bash
# 1. regulator 状态
for r in smb2-vbus ext_5v_boost; do
  REG=$(find /sys/class/regulator -name "regulator.*" | while read d; do
    [ "$(cat $d/name 2>/dev/null)" = "$r" ] && echo $d
  done)
  [ -z "$REG" ] && echo "$r: not found" || echo "$r: state=$(cat $REG/state 2>&1) users=$(cat $REG/num_users 2>&1)"
done

# 2. USB power_supply 关键指标
for f in boost_current online present typec_mode typec_power_role pd_active current_max; do
  echo "usb/$f: $(cat /sys/class/power_supply/usb/$f 2>&1)"
done

# 3. dual_role_usb 模式能力
cat /sys/class/dual_role_usb/otg_default/supported_modes
cat /sys/class/dual_role_usb/otg_default/mode

# 4. USB HAL 服务状态
getprop | grep -E "init\\.svc\\.(vendor\\.usb-hal|vendor\\.usbgadget)"
```

**判断逻辑：** `smb2-vbus/state=disabled` + `boost_current=0` + dmesg 无 `usb 1-1: new device` = 供电层问题。此时写 PD 寄存器或 DWC3 mode 文件**无法解决**——需要查 votable 框架为什么没有使能 VBUS。

详细诊断见 `references/pd-vbus-debug.md`。

### Phase 3: 强制 Host 模式

```bash
# 方法 A: DWC3 模式文件（效果取决于 extcon 链路是否活着）
echo "host" > /sys/devices/platform/soc/*.ssusb/mode

# 方法 B: dual_role_usb（通常被 PD PHY 忽略）
echo "dfp" > /sys/class/dual_role_usb/otg_default/mode
```

**失效预期：** 如果 Signal Interpretation 阶段发现 typec class 缺失或无 extcon 事件，以下操作大概率无效。

切换 host 模式会：
- 断开 USB gadget（ADB 会断）
- 初始化 XHCI 主控制器
- 开启 VBUS 为外设供电

### Phase 4: 修复驱动绑定

```bash
# 遍历 USB 设备查找目标
for d in /sys/bus/usb/devices/*/; do
  V=$(cat "$d/idVendor" 2>/dev/null)
  P=$(cat "$d/idProduct" 2>/dev/null)
  DRV=$(readlink "$d/driver" 2>/dev/null | xargs basename)
  [ "$V:$P" = "0b95:1790" ] || continue
  echo "Found at $(basename $d), driver=$DRV"
  # 如果需要切换驱动
  if [ "$DRV" = "ax88179_178a" ]; then
    echo "$(basename $d)" > /sys/bus/usb/drivers/ax88179_178a/unbind
    sleep 1
    echo "$(basename $d)" > /sys/bus/usb/drivers/asix/bind
  fi
done
```

### Phase 5: 后台自动修复（AKA "拔线模式"）

当需要拔掉 ADB 线才能插外设时，用 nohup 启动后台脚本。

**⚠️ nohup 模式选择（Android mksh 无 disown）：**

| 模式 | 命令形式 | ADB 断开后存活 | 推荐 |
|------|---------|---------------|------|
| 内联命令 | `nohup sh -c "sleep 15; dmesg > /tmp/cap.txt" > /dev/null 2>&1 &` | ✅ 已验证存活 | 推荐 |
| 执行脚本文件 | `nohup sh /data/local/tmp/script.sh > /dev/null 2>&1 &` | ❌ 进程可能提前死亡 | 不推荐 |

**mksh 中 `&` 不会让 `adb shell` 立即退出**（adb 等待所有子进程结束），所以必须用短 timeout（5-8 秒）配合内联模式。

```bash
# 1. 注册 ID（提前）
echo "VID PID" > /sys/bus/usb/drivers/<正确驱动>/new_id

# 2. 内联模式启动后台捕获（推荐）
nohup sh -c "sleep 15; lsusb -v -d 0b95:1790 > /data/local/tmp/cap.txt; dmesg -c >> /data/local/tmp/cap.txt" > /dev/null 2>&1 &
echo PID=$!

# 3. 用户拔 ADB → 插外设 → 等 N 秒 → 插回 ADB

# 4. 读结果
cat /data/local/tmp/cap.txt
```

### Phase 6: 网络配置

```bash
# 静态 IP
ip link set <IFACE> up
ip addr add 192.168.1.X/24 dev <IFACE>
ip route add default via 192.168.1.1 dev <IFACE>
```

### Boot 持久化

Magisk `service.d` 脚本：

```bash
# /data/adb/service.d/<name>
# 在 boot 时注册 ID 并等待设备出现
```

## Common Pitfalls

1. **dual_role_usb 写入不可靠**：PD PHY 硬件状态可能覆盖软件写入。优先用 DWC3 `mode` 文件。
2. **Wrong interface name**: 在 host 模式下设备位于 `/sys/bus/usb/devices/`，不在 platform 设备树。
3. **nohup 进程存活**：必须用内联 `nohup sh -c "..."` 模式（非脚本文件），否则 ADB 断开后进程死亡。
4. **VBUS 供电**：强制 host 模式后 PD PHY 可能不提供 VBUS。如外设灯亮但无法枚举，可能是 PD 协商问题。
5. **built-in 驱动无法卸载**：不能 `rmmod`，只能用 unbind/rebind。
6. **idVendor/idProduct 文件路径**：在 host 模式下通过 `/sys/bus/usb/devices/<X-YYYY>/idVendor` 访问。
7. **extcon 架构不可绕行（关键）**：DWC3 模式切换依赖 extcon notifier 回调。如果 PD PHY 不产生 USB_HOST 事件，任何 mode 文件写入都是徒劳。必须先诊断 extcon 链路。
8. **/sys/class/typec/ 缺失即无软件入口**：内核未编译 Type-C class driver 时，PD PHY 操控没有合法软件接口。此时任何"通过软件强制 host 模式"的尝试都不可靠。
9. **PD PHY 寄存器写入风险高**：直接通过 i2c 写 PD 芯片寄存器可能破坏充电控制逻辑、损坏硬件。只在完全理解芯片寄存器手册且有备份方案时尝试。
10. **"层 1 vs 层 2" 框架**：USB 外设工作有两个独立的前提条件——① host 模式激活（涉及 DWC3/PD PHY/CC 检测），② 正确的驱动绑定。层 1 不通时，调试层 2 毫无意义。务必先解决层 1 再处理驱动冲突。
11. **PD PHY 状态机粘连**：重复的 unbind/rebind 操作或驱动程序切换可能导致 PD PHY 状态机卡住，表现为后续插入外设时 CC 检测不触发（dmesg 无 USB Type-C 事件）。此时**需要重启设备**来复位 PD PHY 状态机。
12. **Failed to read reg -32 (EPIPE) = 供电不足**：USB3 Gigabit Ethernet 设备（如 AX88179）的 `Failed to read reg index 0x0002: -32` 错误指向内核 USB 控制传输中断，`-32` = EPIPE（端点中断/STALL）。这是供电不足/信号完整性问题的典型信号，不是驱动冲突。`-19` = ENODEV（设备无响应，控制传输超时）。

13. **`Source_Capabilities: -14` 和 PDO=0 是噪音，非根因**：PD 协商失败（`Error sending Source_Capabilities: -14`）和 PDO 全零可以在 Type-C default VBUS (500mA) 正常的情况下与设备成功枚举共存。**不要把 PD 错误当作供电不足的证据**。判断 VBUS 是否到位的关键信号只有一条：查看 dmesg 中 `usb 1-1: new high-speed USB device number N` 是否出现。出现 = VBUS 在工作 (尽管 PD 同时失败)，不出现 = VBUS regulator 未使能。

14. **votable 框架 vs debugfs**：高通 PMIC 的 VBUS 使能靠 votable 框架（`OTG_VOTER`, `BOOST_BACK_VOTER` 等）投票决定。LineageOS 4.9 kernel 通常未开 `CONFIG_REGULATOR_DEBUG` 和 `CONFIG_PMIC_VOTABLE_DEBUG`，无法通过 debugfs 观察投票状态。此时检查 USB HAL 服务状态 (`vendor.usb-hal-1-3`) 作为替代。不要因为 debugfs 不存在就下结论说 "votable 框架不可用"——框架在内核中始终运行，只是调试接口未暴露。
15. **`remove_id` sysfs 不影响 built-in ID**：即便 `remove_id` 写入返回 0，它仅移除 `new_id` 添加的动态记录，无法移除 USB_DEVICE 宏静态编译的 `id_table`。

### 芯片识别先于驱动调试

切勿仅凭 VID:PID 判定驱动层问题。同一 VID:PID 可能对应不同芯片系列（如 0b95:1790 = AX88179 USB3 Gigabit 而非 AX88772D USB2 Fast），错误匹配会导致将供电问题误判为驱动冲突。接入设备前，先用 `lsusb -v -d VID:PID` 获取 iProduct 确认芯片型号。如果 ADB 与设备共用同一物理口，需提前用 nohup 模式捕获。

## References (in skill directory)

- `references/sd845-dwc3-sysfs.md` — SD845 DWC3 sysfs 接口完整映射
- `references/ax88772d-case.md` — AX88772D 驱动冲突调试实录
- `references/pd-vbus-debug.md` — PMIC VBUS 供电诊断（regulator/votable/PowerSupply 层）
