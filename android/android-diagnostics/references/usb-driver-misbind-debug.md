# Android USB 外设驱动错配诊断（ADB 途径）

## 场景

Android 设备插入 USB 外设（以太网卡、存储、串口等），但：
- 无网络接口出现，或接口出现但不工作
- `dmesg` 显示的驱动名与硬件不匹配
- 错误的内核驱动匹配了 USB VID:PID

## 快速诊断流程

### 1. 确认驱动是否为内置（=y）还是模块（=m）

```bash
adb shell "su -c 'zcat /proc/config.gz 2>/dev/null | grep -iE \"ASIX|AX8817|USB_NET\"'"
```

常见双内置场景：
- `CONFIG_USB_NET_AX8817X=y` — `asix` 驱动（AX88772/AX8817x）
- `CONFIG_USB_NET_AX88179_178A=y` — `ax88179_178a` 驱动（AX88179）
- 两者同时 `=y` 时，USB 核心按驱动注册顺序匹配，可能错配

### 2. 查看当前绑定

```bash
adb shell "su -c '
for d in /sys/bus/usb/devices/*/; do
  if [ -f \"\$d/idVendor\" ]; then
    V=\$(cat \"\$d/idVendor\")
    P=\$(cat \"\$d/idProduct\")
    DRV=\$(readlink \"\$d/driver\" | xargs basename 2>/dev/null || echo none)
    echo \"\$V:\$P → \$DRV\"
  fi
done
'"
```

### 3. 查看 dmesg 确认驱动声明

```bash
adb shell "su -c 'dmesg | grep -iE \"asix|ax88|usb.*eth|0b95\"'"
```

### 4. 通过 sysfs 纠正绑定

```bash
# 从错误驱动解绑
adb shell "su -c 'echo -n \"1-1:1.0\" > /sys/bus/usb/drivers/ax88179_178a/unbind'"

# 向正确驱动添加 USB ID（如果未匹配）
adb shell "su -c 'echo -n \"0b95 1790\" > /sys/bus/usb/drivers/asix/new_id'"

# 绑定到正确驱动
adb shell "su -c 'echo -n \"1-1:1.0\" > /sys/bus/usb/drivers/asix/bind'"
```

注意：`new_id` 在 SELinux enforcing 模式下可能被限制。

## 单口手机的调试困境

手机只有 **1 个 USB-C 口**，ADB 调试线和目标 USB 外设不能同时插。

| 调试需求 | 需要的连接 | 冲突 |
|---------|-----------|------|
| ADB 控制台 | 数据线到电脑 | 占用了唯一的口 |
| 插目标外设 | 外设到手机 | 口已被 ADB 占用 |
| RNDIS 网络 | 数据线网络 | 同 ADB 共用数据线 |

**解法优先级：**
1. **WiFi ADB** — `adb tcpip 5555`，拔数据线，插外设，`adb connect IP:5555`。WiFi 可能坏。
2. **RNDIS ADB** — 先开 RNDIS（`svc usb setFunctions rndis`），配置 Mac 端 IP，`adb tcpip 5555`，拔线插外设，通过 RNDIS IP 重连。
3. **USB OTG Hub** — 一分二，ADB + 外设同时插。最稳但需要硬件。
4. **脚本投递** — 写好修复脚本推到手机，用户本地用 Termux 执行。

## 常见错配表

| USB 设备 | VID:PID | 正确驱动 | 错配驱动 | 原因 |
|---------|---------|---------|---------|------|
| AX88772D | 0b95:1790 | `asix` | `ax88179_178a` | 驱动表 ID 重叠 |
| RTL8153 | 0bda:8153 | `r8152` | `cdc_ether` | 双协议 |
