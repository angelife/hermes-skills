# SD845 (sdm845) DWC3 USB sysfs 接口映射

适用于 Xiaomi Mi 8 (dipper) / Mi 6 (sagit) 等 sdm845 设备 (kernel 4.9)。

## DWC3 Core

| 路径 | 说明 | 示例值 |
|------|------|--------|
| `/sys/devices/platform/soc/a600000.ssusb/mode` | DWC3 核心模式 (root:root, rw) | `peripheral` / `host` / `drp` |
| `/sys/devices/platform/soc/a600000.ssusb/usb_compliance_mode` | USB 合规模式 | `N` |
| `/sys/devices/platform/soc/a600000.ssusb/a600000.dwc3/udc/a600000.dwc3/is_otg` | OTG 状态 (0/1) | `0` |
| `/sys/devices/platform/soc/a600000.ssusb/a600000.dwc3/udc/a600000.dwc3/state` | DWC3 gadget 状态 | `configured` / `attached` |

## dual_role_usb

| 路径 | 说明 | 示例值 |
|------|------|--------|
| `/sys/class/dual_role_usb/otg_default/mode` | USB 双角色模式 (system:system, rw) | `ufp` / `dfp` |
| `/sys/class/dual_role_usb/otg_default/power_role` | 电源角色 | `sink` / `source` |
| `/sys/class/dual_role_usb/otg_default/data_role` | 数据角色 | `device` / `host` |
| `/sys/class/dual_role_usb/otg_default/supported_modes` | 支持的模式 | `ufp dfp` |

**注意：** dual_role_usb 的 `mode` 文件**可能被底层 PD PHY 硬件否决**。写入 `dfp` 返回 0 但模式未实际变更的情况已验证。

## extcon (External Connector)

| 路径 | 功能 | 状态字段 |
|------|------|----------|
| `/sys/class/extcon/extcon0/state` | DisplayPort 扩展分发 | `DP=0 HDMI=0` |
| `/sys/class/extcon/extcon1/state` | EUD (Embedded USB Debugger) | `USB=0 SDP=0` |
| `/sys/class/extcon/extcon2/state` | PMI8998 充电器检测 | `USB=0 USB_HOST=0` |
| `/sys/class/extcon/extcon3/state` | USB 开关 (vendor) | `USB=0 USB_HOST=0` |
| `/sys/class/extcon/extcon4/state` | **USB PD PHY (关键)** | `USB=1 USB_HOST=0 DP=0` |

**extcon4 (关键)：** 对应 `qcom,usb-pdphy@1700`，是 USB Type-C PD PHY。它的状态决定：
- `USB=1, USB_HOST=0` — 连接的是主机（电话是 device）
- `USB=0, USB_HOST=1` — 连接的是设备（电话是 host）

该接口**只读**，由硬件 CC 引脚检测自动设置。

## 角色切换的实际经验 (Mi8)

1. 写入 dual_role_usb/mode → 返回 0 但可能无效
2. 写入 DWC3 mode → 可能改变模式但 VBUS 供电可能未被 PD PHY 启用
3. 强制写 `host` 或 `dfp` 后，ADB gadget 立即断开
4. 即使模式切换成功，外设也可能因 PD 协商问题不枚举（灯亮但无设备节点）
