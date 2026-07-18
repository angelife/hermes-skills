---
name: android-usb-network-debugging
description: Android USB 网络调试 - 从 USB tethering 到 OTG 网卡上网的完整调试路径
triggers:
  - Android 手机通过 USB 上网
  - USB tethering 不工作
  - Android 连接外部 USB 网卡 (AX88772D, ASIX 芯片等)
  - 禁用移动数据强制走 USB/以太网
linked_files:
  - references/ax88772d-diagnostics.md  # AX88772D 硬件验证 + Mi8/Mac 诊断步骤
  - references/ax88772d-driver-fix.md  # AX88772D 驱动绑定修复脚本 (v1/v3 + Magisk service.d)
  - references/gnirehtet-reverse-tether.md  # gnirehtet 反向 USB 共享网络（WiFi损坏替代方案）
  - references/mi8-wired-ethernet-setup.md  # Mi8 RTL8153 USB 有线网卡上网 + ADB 局域网直连完整记录
  - references/sd845-usb-ethernet-deep-analysis.md  # SD845 芯片组兼容性矩阵 + 瓶颈分析 + Hub倍增效应 + 系统化诊断流程
  - references/usb-host-mode-deep-diagnostics.md  # DWC3/PD PHY 驱动层诊断 + Layer 1 vs Layer 2 问题分离方法论
  - references/adb-tcp-watchdog.md  # 单 USB-C 口设备 ADB 保活 watchdog 脚本
  - references/apple-silicon-phone-tether-limits.md  # Apple Silicon + Mi8：手机给 Mac 供网硬限制（RNDIS/热点不可用）
---

# Android USB 网络调试

## 物理拓扑

### 拓扑A: Mi8 当前状态（Mac → Mi8 USB连接）
```
Mac(en0 WiFi) ← USB-C → Mi8(usb0/rndis0)
```

| 端 | 接口 | IP | 状态 |
|---|---|---|---|
| Mac 侧 | `en5` (RNDIS Gadget) | 无 IP | ❌ networksetup 配不上 |
| Mi8 侧 | `rndis0` | 192.168.114.141/24 | ✅ ping 通 Mac |

### 拓扑B: 目标状态（Mi8 → AX88772D USB网卡 → 路由器 → WiFi）
```
Mi8(OTG) → AX88772D → 路由器LAN → Mac WiFi
```

## 关键调试发现

1. **Mi8 连接 Mac 时是 USB 设备模式 (peripheral)** — USB-C 口不是 host，不能同时接外部 USB 设备
2. **需要 OTG 线** 才能把 AX88772D 接到 Mi8
3. **Mi8 内置 asix 驱动** — 无需安装，kernel 4.9.337 已内置

## Mi8 内核模块确认 (kernel 4.9.337)
- `/sys/bus/usb/drivers/asix` ✅ — 支持 AX88772D
- `/sys/bus/usb/drivers/ax88179_178a` ✅ — 同系列芯片
- `/sys/bus/usb/drivers/cdc_ether` ✅
- `/sys/bus/usb/drivers/r8152` ✅

## 物理约束：Mi8 单 USB-C 口的冲突

Mi8 只有一个 USB-C 口，通过 USB 连 Mac 时处于 **USB 设备模式 (peripheral)**，该口是 device 端而非 host 端，无法同时接外部 USB 设备。

**解决方案：需要 USB-C OTG Hub**，例如：
- USB-C 母头分出多个口：一个接 Mac（ADB调试），一个接 AX88772D
- 或：使用充电分离线，同时提供 PD 供电和 USB-A 接口

**确认 Mi8 是否识别到 AX88772D：**
```bash
# 插上网卡后检查
adb -s a6520fa3 shell "ls /sys/class/net/"
# 有 eth0 或 usb0 说明识别成功
adb -s a6520fa3 shell "cat /sys/class/net/eth0/address 2>/dev/null"
```

## Termux 输入问题：Fcitx5 拦截按键

**现象**：Termux 无法输入任何命令，连 ls 都打不出来。

**根因**：默认输入法是 Fcitx5（中文输入框架），在终端里拦截了按键事件，无法传到 bash。

**修复**：
```bash
# 切换回标准 Latin 输入法
adb shell "ime set com.android.inputmethod.latin/.LatinIME"
```

**重装 Termux**（如果修复无效）：
```bash
# 1. 卸载旧版
adb -s a6520fa3 shell "pm uninstall com.termux"

# 2. 下载（当前最新版 0.119.0-beta.3，114MB）
# F-Droid URL 格式：https://f-droid.org/repo/com.termux_<versionCode>.apk
# 版本 1022 = https://f-droid.org/repo/com.termux_1022.apk

# 3. 安装
adb -s a6520fa3 install -r /path/to/termux.apk

# 4. 重设输入法
adb shell "ime set com.android.inputmethod.latin/.LatinIME"
```

**注意**：Termux 首次启动需要联网下载基础包（约 200MB），如果 Mi8 无网络则 Termux 无法正常使用。必须先解决网络连通性。

## AX88772D 在 Mac 上的验证结果

**网卡本身是好的**。插到 Mac USB 口后：
- `system_profiler SPUSBDataType` 检测到：`Product ID 0x1790, Vendor ID 0x0b95 (ASIX Electronics Corporation)`
- `networksetup` 里出现 "AX88772D" 服务
- 但 `Ethernet Address: (null)` — macOS 的 CDC-ECM 驱动接上了 USB 但没有创建 en 网络接口
- `ifconfig` 里没有对应的 en 接口

这是 macOS 驱动层的问题，不是网卡硬件问题。Mi8 端同理：插上后 Mi8 如果没有识别到 `eth0`，先确认 USB 连接稳定（线缆是否松动）。

**如果 Mi8 插上网卡后 `ls /sys/class/net/` 里没有 eth0：**
1. 检查网卡是否完全插入Mi8的USB-C口
2. 换一根质量更好的USB-C OTG线
3. 检查Mi8的OTG供电是否足够（有些网卡需要更大电流）
4. 查看dmesg是否有USB设备插入的日志

## 重装 Termux 标准流程（完整版）

```bash
# 1. 卸载旧版
adb -s a6520fa3 shell "pm uninstall com.termux"

# 2. 确认设备连接正常
adb devices
# 应该看到: a6520fa3    device

# 3. 下载 Termux APK
# 当前稳定版: https://f-droid.org/repo/com.termux_1022.apk (0.119.0-beta.3, 114MB)
# 版本号 = F-Droid 页面上看到的四位数字
# F-Droid URL 格式: https://f-droid.org/repo/com.termux_<versionCode>.apk

# 4. 安装到设备
adb -s a6520fa3 install -r /tmp/termux.apk

# 5. 安装完成后立刻切换输入法（Termux 依赖标准键盘）
adb -s a6520fa3 shell "ime set com.android.inputmethod.latin/.LatinIME"
```

**下载版本号查询方法**：
```bash
curl -sL "https://f-droid.org/en/packages/com.termux/" | grep "Version [0-9]" | head -1
# 输出格式: <b>Version 0.119.0-beta.3</b> (1022)
# 版本号 = 1022 → APK URL = https://f-droid.org/repo/com.termux_1022.apk
```

## 命令速查

```bash
# 检查 Mi8 是否检测到 USB 设备
adb -s a6520fa3 shell "ls /sys/bus/usb/devices/"

# 查看 Mi8 所有网卡
adb -s a6520fa3 shell "cat /sys/class/net/*/address"

# 禁用移动数据
adb -s a6520fa3 shell "svc data disable"

# 启用移动数据
adb -s a6520fa3 shell "svc data enable"

# 查看 USB gadget 模式
adb -s a6520fa3 shell "svc usb getFunctions"

# 设置 USB 为 RNDIS 模式
adb -s a6520fa3 shell "su -c 'svc usb setFunctions rndis'"
```

## 常见问题

- **RNDIS 接口没有 IP**: Mac 侧 `en5` 没有 inet，networksetup 无法配置，需 sudo 权限开启 IP forwarding
- **移动数据默认关闭**: `settings get global mobile_data` 返回 0，需 `svc data enable`
- **ping 不通**: 检查防火墙、安全设置、路由表

## gnirehtet 反向网络（WiFi/移动数据皆不可用时）

当 Android 手机 WiFi 硬件损坏且无移动数据时，用 **gnirehtet** 通过 ADB 反向共享电脑网络。

详见 [references/gnirehtet-reverse-tether.md](references/gnirehtet-reverse-tether.md)

### gnirehtet 在 macOS 上的已知问题

- **Rust 版 relay 不稳定**：`gnirehtet run` 或 `gnirehtet relay` 启动后，relay 进程在 ~1 分钟内 segfault（exit code 139），日志显示大量 `Dropping invalid packet` 后崩溃
- **Java 版需要 JRE**：Mac 上可能未安装 Java Runtime，需先 `brew install --cask temurin` 或等效方案
- 虽然 `adb reverse localabstract:gnirehtet tcp:31416` 和 VPN 隧道 `tun0` 建立成功，但 **数据不通**（ping 8.8.8.8 0% 回复）

### RNDIS 在 macOS 上的限制

- **macOS 原生不支持 RNDIS 主机端驱动**（不包含在 OS 中）
- **HoRNDIS** 是第三方 kext 驱动，但仅适用于 Intel Mac（Apple Silicon M 系列不支持传统 kext）
- Mi8 的 RNDIS 接口 `rndis0` 状态为 `NO-CARRIER`，因为 Mac 侧没有对应接口响应
- 如果需要 RNDIS 反向共享网络，只能在 Mac 上通过 **系统设置 → 共享 → 互联网共享** 手动配置（需要管理员密码）
- **用户说「用手机流量继续」时**：先读 `references/apple-silicon-phone-tether-limits.md`。Apple Silicon + 无 wlan0 的 Mi8 = USB 供网与热点都不可用；优先确认家宽是否已通，否则降级离线任务，禁止反复试 RNDIS/softap。

## 操作规范提醒
- 描述 fastboot/recovery 进入方式时必须精确：`关机 + 音量下键` 而非 `按电源键选重启`
- 进入 fastboot 的正确描述：**关机状态 → 同时按住电源键 + 音量下键**，而不是"按电源键→长按重启→选择 fastboot"
- 不要使用模糊描述如"重启到 fastboot"——用户需要的是精确的物理按键操作

## ⚠️ Pitfall: Android 代理设置阻止浏览器

**现象**：浏览器打不开任何网站，但 `curl` 和 `ping` 网络完全正常。

**根因**：设备被设置了 HTTP 代理 `localhost:8080`，但该端口没有代理服务运行，所有流量被静默拦截。浏览器完全无法访问，curl/ping 因为不走系统代理所以正常。

**诊断**：
```bash
# 检查代理设置
adb -s a6520fa3 shell "settings get global http_proxy"
# 输出 localhost:8080 或类似 → 代理在拦截流量
```

**修复**：
```bash
# 清除所有代理设置（立即生效，无需重启）
adb -s a6520fa3 shell "settings put global http_proxy :0"
adb -s a6520fa3 shell "settings put global global_http_proxy_host ''"
adb -s a6520fa3 shell "settings put global global_http_proxy_port 0"
adb -s -a6520fa3 shell "settings put global https_proxy :0"
```

**验证**：
```bash
# 代理清空后，浏览器应立刻能访问网站
adb -s a6520fa3 shell "curl -s http://baidu.com | head -3"
```

**提示**：即使代理设置为 `localhost:8080`，浏览器也会完全挂掉（白屏/转圈），而 `curl` 和 `ping` 正常——这是判断代理问题的关键特征。关掉浏览器再重新打开以清除缓存。

## ⚠️ Pitfall: DNS 解析失败但 ping IP 正常

**现象**：`ping baidu.com` 显示 `unknown host`，但 `ping 8.8.8.8` 和 `curl http://<IP>` 正常。

**可能原因**：
- `ro.com.android.mobiledata=false`（字符串 "false"，非布尔值）导致系统 DNS 解析服务异常
- `/etc/resolv.conf` 不存在（Android 15+ 使用 netd 服务）

**诊断**：
```bash
adb -s a6520fa3 shell "getprop ro.com.android.mobiledata"
# 如果输出 "false"（带引号）→ 字符串类型的 false，不是布尔值
```

**修复**：
```bash
# 先清除代理（见上方 pitfall）
adb -s a6520fa3 shell "settings put global http_proxy :0"
# 然后用 IP 直接测试
adb -s a6520fa3 shell "ping -c 2 8.8.8.8"
# 如果 ping IP 正常但域名失败 → DNS 问题，清除代理后重启浏览器通常解决
```

- **macOS `nc` 端口检测**：macOS 版 `nc` 不支持 `-W timeout` 参数（这是 Linux/BSD 语法），正确的是 `-w timeout`。使用前先 `nc -h 2>&1 | grep -q '\\-w' && echo 支持 || echo 不支持` 确认语法。

## ⚠️ Pitfall: nohup 脚本文件在 Android mksh 上可能被 SIGHUP 杀

**现象**：通过 `adb shell "su -c 'nohup script.sh &'"` 启动的捕获/watchdog 脚本，在 ADB USB 断开后未产生预期输出。

**根因**：Android 的 `/system/bin/sh` 是 mksh，信号传播行为与 bash 不同。当 ADB shell 终止时，`nohup` 可能无法保护通过脚本文件（而非内联命令）启动的进程树——执行 `.sh` 文件会创建额外的进程层，SIGHUP 沿进程树传播时可能绕开 nohup 的保护。

**已验证的存活模式**（两次独立 dmesg 捕获证实存活）：

```bash
# ✅ 存活 — 内联命令直接写在 nohup sh -c 字符串中
adb shell "su -c 'nohup sh -c \"sleep 25; dmesg > /data/local/tmp/capture.txt\" > /dev/null 2>&1 &'"

# ❌ 可能不存活 — 脚本文件方式
nohup sh /data/local/tmp/script.sh > /dev/null 2>&1 &
```

**推荐做法**：对于需要跨 ADB 断连存活的后台任务（dmesg 捕获、watchdog），始终将命令内联在 `nohup sh -c "..." &` 中。如果命令太长，写成 `sh -c "..."` 的单行模式，而非引用外部 `.sh` 文件。

## 网络发现：已知设备 IP 地址

| 设备 | 有线网段 | RNDIS网段 | 备注 |
|---|---|---|---|
| Mi8 (dipper) | 192.168.1.21 (eth0) | 192.168.45.184 (rndis0) | 有线网卡上网 ✅ |
| Mi6 (sagit) | 192.168.1.15 | — | ADB TCP 5555 正常 |

## ⚠️ Pitfall: Mi8 有多张网卡 — ping 通不等于 ADB 能通

**现象**：`ping 192.168.50.3`（Mi8 移动数据 IP）完全正常，但 `adb connect 192.168.50.3` 显示 `device offline`。

**根因**：Mi8 有多张网络接口（移动数据、WiFi、RNDIS 等），ping 使用 ICMP 是单向的（Mac → Mi8 物理链路到达，回程走默认路由出口即移动数据，不需要知道 Mac 的地址），但 ADB TCP 握手需要 Mi8 从 5555 端口向 Mac 建立反向 TCP 连接。Mi8 的移动数据出口不知道怎么路由回 Mac，导致握手失败。

**关键判断**：ping 通 + adb offline = Mi8 多接口路由不对称，不是"网络层不通"。真正的问题在 ADB 协议层。

**正确做法**：
- 确认 Mi8 用哪张网卡上网（执行 `ip addr show` 或 `ip route show`）
- 让 Mac 和 Mi8 在**同一广播域**（同一网段），ADB 走以太网直连
- 如果 Mi8 通过 USB 有线网卡（RTL8153/RTL8152）连路由器，Mi8 会拿到 192.168.1.x DHCP IP，此时 Mac WiFi 也在同一路由器下，直接 `adb connect <Mi8的局域网IP>` 即可

## ⚠️ Pitfall: RTL8192 和 RTL8192LE 是不同芯片

| 型号 | 类型 | macOS 驱动 | 用途 |
|---|---|---|---|
| RTL8192 (non-LE) | USB 以太网 (RTL8152/8153 芯片组) | ✅ 原生支持，en9 拿 IP | ADB 有线上网方案 |
| RTL8192LE | 802.11n WiFi USB 网卡 | ❌ 无驱动 | 与 ADB 调试无关 |

**鉴别方法**：插上 Mac 后 `system_profiler SPNetworkDataType` 如果显示 "USB 10/100 LAN" 并有 en 接口 = RTL8152/8153 以太网芯片，可以用。如果显示 802.11 或无线相关 = RTL8192LE WiFi 网卡，macOS 无驱动，不要用。

**RTL8152/8153 在 Mac 上的识别特征**：
```
system_profiler SPNetworkDataType | grep "USB 10/100"
# 输出：BSD Device Name: en9, IPv4: 192.168.45.2（拿了 IP 说明驱动正常）
```

## Mi8 USB-C 有线网卡上网方案（推荐）

**物理拓扑**：Mi8 → USB-C Hub → RTL8153 USB 以太网适配器 → 网线 → 路由器LAN口 → Mac WiFi 也在同一路由器

**效果**：Mi8 通过 DHCP 从路由器拿到 192.168.1.x IP，与 Mac 同局域网，ADB 直接 `adb connect 192.168.1.x` 即可。

**操作步骤**：
1. Mi8 用 USB-C OTG Hub（需带 USB-A 口）接 RTL8153 网卡，网卡插网线连路由器
2. Mi8 上查看 `ip addr show eth0` 确认拿到 IP（通常 192.168.1.x）
3. Mac 侧 `adb connect <Mi8的IP>` — 同一广播域，ADB 直连

**注意**：Mi8 单 USB-C 口不能同时接 Mac 调试和 OTG 设备（除非用带额外 USB-A 口的 USB-C Hub）。调试时需要 Hub 分出多个口。

**⚠️ Mi8 USB-C 是 USB 2.0 的**：确认命令 `cat /sys/bus/usb/devices/usb1/speed`，
显示 `480` 而非 `5000`。因此无论什么千兆网卡都被限在 USB 2.0 物理层。

## ⚠️ Pitfall: Mi8 wlan0 不存在 — WiFi 硬件损坏

**现象**：`svc wifi enable` 执行成功但 `ip link show wlan0` 显示 `No such device`，`dumpsys wifi` 显示 `Wifi is disabled`。

**根因**：Mi8 的 WiFi 硬件（firmware/基带）损坏或被 LineageOS 精简版移除了 WiFi 驱动，`wlan0` 网络接口根本不存在。

**诊断**：
```bash
adb -s <设备> shell "ls /sys/class/net/" | grep wlan0
# 无输出 → wlan0 不存在，WiFi 物理接口没有
adb -s <device> shell "dumpsys wifi | grep -i interface"
# 无 wlan0 → WiFi 接口不存在
```

**解决方案**：只能依赖有线网卡（USB Ethernet Adapter）上网，不要尝试用命令"开启"不存在的硬件。

## HoRNDIS RNDIS 方案（不适用于 Apple Silicon Mac）

- **HoRNDIS** 是 macOS 的第三方 RNDIS 主机端驱动（kext），但仅支持 Intel Mac
- Apple Silicon Mac 不支持传统 kext 驱动，HoRNDIS 无法使用
- 因此 RNDIS 模式在 Apple Silicon Mac 上**永远无法**让 Mac 创建网络接口
- 不要在 Apple Silicon Mac 上尝试用 RNDIS 做网络共享

## adb forward 隧道方案（备选）

当 Mac 和 Mi8 无法直接路由时（不在同网段），用 `adb forward` 建 TCP 隧道：

```bash
# 1. USB 连接状态下启用 ADB TCP 监听
adb -s <USB设备> tcpip 5555

# 2. 建立端口转发（Mac 端）
adb -s <设备> forward tcp:15555 tcp:5555

# 3. 通过 localhost 连接（不走网络，走 USB 隧道）
adb connect localhost:15555

# 验证
adb -s localhost:15555 shell "getprop ro.build.version.release"
```

**注意**：`adb connect <IP>` 走网络层，需要 Mac 和 Mi8 在同一广播域。隧道方案走 USB 转发，不受路由限制但需要 USB 持续连接。

## ⚠️ Pitfall: Android 代理设置阻止浏览器
```bash
# 1. 先确认 IP 是否真的 ping 得通
ping -c 1 -W 2 192.168.50.3

# 2. 用 nc 测端口（macOS 用 -w，不是 -W）
nc -z -w 2 192.168.50.3 5555 && echo "ADB开放" || echo "ADB未监听"

# 3. 如果 ping 通但端口不通 = ADB TCP 网络监听没开
#    需要在设备上手动开启：
#    adb tcpip 5555
#    或设备重启后检查 adb 网络配置

# 4. 检查设备是否真的在线
adb devices              # 列出已连接设备
adb connect 192.168.50.3  # 尝试网络连接
```

**常见原因**：设备 ping 得通说明网络层活着，但 `adb tcpip 5555` 从未执行过，或者设备重启后 ADB 网络监听没有自动启动（需要在设备端执行一次 `adb tcpip` 或者保持 USB 连接时的网络 ADB session 不中断）。

## ⚠️ Pitfall: SD845 芯片组兼容性矩阵（kernel 4.9）

详见 `references/sd845-usb-ethernet-deep-analysis.md` 完整分析。

| 芯片组 | 驱动 | 内核 4.9 兼容 | 实际速度 | 主要问题 |
|---|---|---|---|---|
| **RTL8152** | `r8152` | ✅ 识别 | ~700 KB/s | Rx status -71 USB 协议错误 |
| **RTL8152B** | `r8152` | ✅ PID 完整 | ~95 Mbps | ✅ 最稳定百兆选项 |
| **RTL8153/B** | `r8152` | ❌ 缺 PID | — | 4.9 不识别 |
| **AX88772D** | `asix` | ❌ 缺 PID | — | 4.9 不工作 |
| **AX88772A/B** | `asix` | ✅ PID 完整 | ~95 Mbps | 另一稳定百兆选项 |
| **AX88179/A** | `ax88179_178a` | ✅ 免驱 | ~280 Mbps | ⚠️ 高负载断连风险 |

**诊断流程**：直插手机测试 → 跳过 Hub → 对比 Mac 速度 → 确认 USB 2.0 口。
**推荐零成本方案**：USB Tethering（走高通硬件 DMA，绕过 CPU 软中断瓶颈）。
详见 `references/sd845-usb-ethernet-deep-analysis.md`。

## ⚠️ Pitfall: ASIX AX88772D 被 ax88179_178a 驱动错误匹配

**现象**：插入 AX88772D（0b95:1790）后 `dmesg` 显示 `register 'ax88179_178a'` 而不是正确的 `asix` 驱动。设备注册为 `AX88179 USB 3.0 Gigabit Ethernet`（名称错误），无法正常工作。

**根因**：`ax88179_178a` 驱动的内置 USB ID 表也包含部分 ASIX 设备的 PID（包括 0b95:1790），而内核驱动匹配顺序中 `ax88179_178a` 在 `asix` 之前被 probe，导致 AX88772D 被匹配到寄存器布局不同的错误驱动。

**诊断**：
```bash
# 检查设备被哪个驱动绑定
find /sys/devices/platform/soc/a600000.ssusb -name "idVendor" -exec grep -l 0b95 {} \;
# 返回路径 → 检查 driver link
readlink <路径>/driver | xargs basename
```

**修复方法（预注册 + 重绑定）：**

### 方法 A：预注册 USB ID（在插网卡前执行）
```bash
# 将 0b95:1790 添加到 asix 驱动的动态 ID 表
echo "0b95 1790" > /sys/bus/usb/drivers/asix/new_id
```

> **注意**：`ax88179_178a` 内置了 0b95:1790 的匹配项（编译到内核时硬编码），即使方法 A 执行了，新插入设备仍会被 ax88179_178a 抢走。`new_id` 注册不会改变内置驱动的优先级——USB core 按注册顺序匹配，先注册的先得。

> **尝试 `remove_id`**：`/sys/bus/usb/drivers/ax88179_178a/remove_id` 接口存在，`echo "0b95 1790" > .../remove_id` 返回 exit 0。但不确定是否真能移除内置 ID（`remove_id` 仅保证移除通过 `new_id` 添加的动态条目）。如果 `remove_id` 确实工作，设备插入后会直接匹配 asix，无需 unbind/rebind。验证方法：执行 remove_id → 插入设备 → 检查 driver。如果仍被 ax88179_178a 绑定，说明内置 ID 不可移除，用方法 C（unbind+override+bind）+ watchdog。
### 方法 B：设备已插入，切换到正确驱动

```bash
# 1. 找到 ax88179_178a 绑定的设备路径
USBIF=$(find /sys/bus/usb/drivers/ax88179_178a -mindepth 1 -maxdepth 1 -type d ! -name "*:*" 2>/dev/null | head -1)
IFNAME=$(basename "$USBIF")

# 2. 从错误驱动解绑
echo "$IFNAME" > /sys/bus/usb/drivers/ax88179_178a/unbind

# 3. ⚠️ 关键：设置 driver_override，防止 re-probe 再次匹配 ax88179_178a
#    不加这一句，下一步 bind 时 USB core 会重新遍历驱动列表，
#    而 ax88179_178a 仍然匹配 0b95:1790（内置 ID 表），再次抢回
echo asix > /sys/bus/usb/devices/"$IFNAME"/driver_override

# 4. 绑定到 asix 驱动
echo "$IFNAME" > /sys/bus/usb/drivers/asix/bind

# 5. 验证
dmesg | tail -10
ethtool -i eth0 2>/dev/null | grep driver
```

**为什么不直接 bind 就行？** ax88179_178a 和 asix 都匹配 0b95:1790。unbind 后 re-probe 时 USB core 以注册顺序匹配，先注册的 ax88179_178a 会再次抢到设备。`driver_override` 告诉 USB core：**只尝试这个驱动**，从而跳过 ax88179_178a。

### 方法 C：拔掉重新插入（如果方法 A 已执行过）
如果在插入前已将 ID 写入 asix 的 `new_id`，拔插后 by default `ax88179_178a` 仍会先匹配。但重绑定后可验证。

**注意**：`remove_id` 无法移除编译时内置的 USB ID（只对通过 `new_id` 动态添加的 ID 有效），因此不能直接从 `ax88179_178a` 的表中移除 0b95:1790。

### 完整修复脚本
参见 `references/ax88772d-driver-fix.md`。

## 无值守自动修复模式（nohup + OTG + Magisk service.d）

当 Mi8 单 USB-C 口无法同时插 ADB 和 AX88772D 时，可以用脚本在后台等待，拔 ADB 插网卡后自动修复。

> ⚠️ **前置条件警告：该方案依赖硬件 OTG 自动检测**。如果你的设备（如 Mi8/dipper kernel 4.9.337）USB host 模式被固件/内核锁死，即使拔 ADB 插网卡，DWC3 也不会切到 host 模式，设备不供电不枚举，脚本毫无用处。**必须先执行下方「USB Host Mode Deep Diagnostics」确认 layer 1（host 模式）可用**，再尝试此方案。

### 原理

```
Phase 1 (ADB 在线):
  adb tcpip 5555                   → adbd 切 TCP 模式
  注册 0b95:1790 → asix/new_id     → 预注册 ID
  nohup 启动 fix 脚本              → 脚本在后台等待，不受 ADB 断连影响
  cp 到 /data/adb/service.d/       → 开机自动运行

Phase 2 (用户拔 ADB，插 AX88772D，前提: 硬件会自动切 host):
  ⚠️ 硬件自动切 host 不是在所有设备上都工作 — 先诊断确认
  脚本用 for d in /sys/bus/usb/devices/*/ 轮询检测设备
  检测到 0b95:1790 后检查 driver → 如果是 ax88179_178a 则 unbind/rebind
  设 192.168.1.217/24 静态 IP

Phase 3 (Mac 侧):
  adb connect 192.168.1.217:5555
```

### 关键代码模式

**设备扫描**（不用 `find -exec`，用 for 循环更可靠）：
```bash
for d in /sys/bus/usb/devices/*/; do
  [ -d "$d" ] || continue
  V=$(cat "$d/idVendor" 2>/dev/null)
  [ "$V" = "0b95" ] || continue
  P=$(cat "$d/idProduct" 2>/dev/null)
  DRV=$(readlink "$d/driver" 2>/dev/null | xargs basename 2>/dev/null)
  IFACE=$(find "$d" -name "net" -type d 2>/dev/null)
  [ -n "$IFACE" ] && ETH=$(ls "$IFACE/" 2>/dev/null)
  # ... fix driver ...
done
```

**nohup 存活**（ADB 断连后继续跑）：
```bash
adb shell "su -c 'nohup /system/bin/sh /tmp/fix.sh > /dev/null 2>&1 &'"
```

**日志到文件**（nohup 断开 stdout，`tee` 不可用，必须直接重定向）：
```bash
LOG=/tmp/fix.log
echo "[$(date)] message" >> $LOG
```

**开机持久化**（Magisk service.d）：
```bash
adb shell "su -c 'cp /tmp/fix.sh /data/adb/service.d/fix_ax88772d && chmod 755 /data/adb/service.d/fix_ax88772d && chown root:shell /data/adb/service.d/fix_ax88772d'"
```

### 已验证的约束

- **手动写 DFP 不可靠**：`echo dfp > dual_role_usb/mode` 在 USB 线插着 Mac 时几乎永远不生效。应依赖硬件 OTG 自动切换
- **静态 IP 需要路由可达**：必须与 Mac 在同一网段（192.168.1.x），且网线插在同一个路由器 LAN 口
- **错误驱动未必能通 DHCP**：即使链路灯亮，ax88179_178a 对 AX88772D 的寄存器布局兼容不完整。作为脚本内的 fallback，优先用 static IP 而非 DHCP
- **ADB TCP 模式需预先配置**：`adb tcpip 5555` 必须在 ADB USB 在线时执行一次，否则 adbd 不监听 5555 端口
- **开机后 ADB TCP 不会自动启动**：每次重启后 ADB TCP 监听丢失，需要 USB 连接时再次 `adb tcpip 5555` 或开机脚本中 `setprop service.adb.tcp.port 5555`

### 完整脚本示例

参见 `references/ax88772d-driver-fix.md` 中的 v3 自动修复脚本。

## ⚠️ Pitfall: 单 USB-C 口设备无法同时保持 ADB 和外接 USB 设备

**问题**：Mi8 只有一个 USB-C 口。当通过 USB 连接 Mac 做 ADB 调试时，该口处于 **peripheral（设备)）模式**，不能同时外接 AX88772D 等 USB 设备。

**绕过策略：ADB over TCP + 预准备**

```
Phase 1 (ADB USB 在线时)：
  adb tcpip 5555                        → adbd 重启监听 0.0.0.0:5555
  echo "0b95 1790" > asix/new_id        → 预注册驱动 ID
  
Phase 2 (用户拔 USB，插网卡)：
  用户断开 USB 线
  插入 AX88772D（DWC3 硬件自动切到 host 模式）
  通过 Ethernet 获得 IP → adb connect <IP>:5555

Phase 3 (通过 Ethernet ADB 连回)：
  执行方法 B 修复驱动绑定
```

**依赖**：AX88772D 即使在错误驱动下也需要能部分工作以完成 DHCP→获得 IP→ADB over TCP 连回。如果错误驱动完全不可用，需用户通过手机本地终端（Termux）手动执行修复脚本。

### 有 WiFi 但无屏幕设备的 ADB-over-WiFi 方案

当目标设备（如 Mi6）有可用 WiFi 但屏幕损坏时，通过临时 USB 连接启用 ADB over TCP，然后切换到 WiFi 调试。详见 `android-troubleshooting` SKILL.md 的「无屏 Android 设备的 ADB-over-WiFi 调试」章节，包含 `cmd wifi` 命令树和 Python TCP 端口扫描器。

### SD845 USB controller 关键 sysfs 节点

| 路径 | 用途 | 当前值 (peripheral) |
|---|---|---|
| `/sys/devices/platform/soc/a600000.ssusb/mode` | 控制器模式 | `peripheral` (host 模式为 `host`) |
| `/sys/class/dual_role_usb/otg_default/mode` | 角色切换 | `ufp` (device) → `dfp` (host) |
| `/sys/class/dual_role_usb/otg_default/data_role` | 数据角色 | — |
| `/sys/class/dual_role_usb/otg_default/power_role` | 供电角色 | — |
| `/sys/class/android_usb/android0/state` | gadget 状态 | `CONFIGURED` |

**🟡 可靠路径 vs 不可靠路径**

实际的 SD845 角色切换有两个路径，可靠性差异很大：

| 路径 | 机制 | 可靠性 | 说明 |
|---|---|---|---|
| **硬件 OTG 自动检测** (推荐) | USB-C CC 引脚或 ID 引脚检测 | ✅ 高 | 物理插入 USB 设备后自动切换，无需写 sysfs。Mi8 等手机设计为：无设备时 peripheral，插入 OTG 设备后自动 host |
| **手动写 dual_role_usb** | `echo dfp > /sys/class/dual_role_usb/otg_default/mode` | ⚠️ 中等 | 写入后 exit 0 不代表切换成功。USB-C CC 逻辑可能拒绝模式变更（如 Mac 仍连接时）。**在 Mac USB 线仍插入时几乎永远不生效**，因为硬件层面的 CC 引脚协商认为对方是 host |

**推荐做法**：不要手动写 mode 文件。让用户**断开所有 USB 连接**，再插入 AX88772D（带 OTG 线），硬件自动完成 host 模式切换。

**切换到 host 模式**（通常在插入 OTG 设备时硬件自动完成，但也可手动）：
```bash
# 方法1：通过 dwc3 mode 节点
echo host > /sys/devices/platform/soc/a600000.ssusb/mode

# 方法2：通过 dual_role_usb（需 system 权限）
echo dfp > /sys/class/dual_role_usb/otg_default/mode
```

**注意**：切换为 host 模式后会断开 ADB USB 连接（因为控制器不再扮演 USB 设备角色），必须先切换到 ADB TCP 模式或另备调试通道。

## USB Host Mode Deep Diagnostics

当 USB host 模式（OTG）彻底不工作时——设备不检测、不给电、不枚举——根因通常在驱动绑定层（layer 2）之下的 USB 控制器角色协商层（layer 1）。按下述方法诊断。

### Phase 1: typec class 探测（成本最低，信号最强）

```bash
ls -la /sys/class/typec/ 2>&1
for p in /sys/class/typec/port*/; do
  echo "== $p =="
  cat "${p}data_role" 2>&1
  cat "${p}power_role" 2>&1
  cat "${p}preferred_role" 2>&1
done
```

| 结果 | 含义 |
|------|------|
| 目录存在且有 port0 | 内核编译了 `CONFIG_TYPEC`，PD PHY 有软件接口可用 → A 方案（写 PD PHY）可行 |
| 不存在 | 无 Type-C class → A 方案无合法软件入口 |

### Phase 2: 插入瞬间抓 dmesg（成本为零，判断硬件检测是否活）

```bash
# 1. 清空 dmesg 缓冲
dmesg -c > /dev/null

# 2. ⚠️ 启动后台捕获 — 必须使用此精确的 nohup sh -c 模式
#    不要用: nohup script_file.sh &
#    不要用: nohup sh script_file.sh &
#    这些都会因 ADB shell 断连时的 SIGHUP 传播而被杀
adb shell "su -c 'dmesg -c > /dev/null; nohup sh -c \"sleep 25; dmesg > /data/local/tmp/dmesg_capture.txt\" > /dev/null 2>&1 &'"

# 2b. ✅ 关键：在断开 ADB 前验证进程存活
adb shell "su -c 'pidof sh | head -3'"
# 必须看到 PID 输出

# 3. 拔 ADB 线，插入目标 USB 设备
# 4. 等 25+ 秒，换回 ADB 线
# 5. 读捕获结果（扩展关键词集）
cat /data/local/tmp/dmesg_capture.txt | grep -iE "usb|extcon|dwc3|typec|pmi8998|cc_state|id_state|hub|connect|disconnect|role|host|peripheral|new device|xhci|sink|source|pdphy|usbpd|eth0|eth1|carrier|register|low power|ax88179|asix|-71"
```

**⚠️ 关键陷阱**：dmesg 捕获文件存在 ≠ 捕获进程在关键窗口存活。已验证的存活模式：
```
nohup sh -c "sleep N; dmesg > /data/local/tmp/file" > /dev/null 2>&1 &
```
用脚本文件（nohup sh /path/to/script.sh &）在 mksh 上可能被杀。必须先用 `pidof` 验证再断开 ADB。

**判读逻辑：**

| dmesg 出现 | 含义 |
|---|---|
| 完全零条（**仅当捕获存活已验证**） | 硬件检测中断没触发 → 问题在 CC 检测电路或 bootloader 固件层 |
| 完全零条（捕获存活**未验证**） | ⚠️ 无效结果——捕获进程可能已死，不能下任何结论 |
| 有 Type-C Sink/Source 事件 + DWC3 退出 low power + XHCI 启动 + 设备枚举 | **Layer 1 通了！** 问题纯在 layer 2（驱动绑定）。ASIX 芯片被 ax88179_178a 错误匹配 |
| 有 Type-C 事件但 XHCI 没启动 / DWC3 没唤 | 角色仲裁逻辑拒绝切换 → 需硬件的 OTG Y 线或独立供电 hub |

### Phase 3: extcon 状态快照

```bash
for e in /sys/class/extcon/extcon*/; do
  echo "== $(cat ${e}name) =="
  cat "${e}state"
done
```

SD845 关键 extcon 条目：

| 条目 | 名称 | 意义 |
|------|------|------|
| extcon0 | ms-ext-disp | DisplayPort/HDMI alt mode — 无关 |
| extcon1 | 88e0000.qcom,msm-eud | Embedded USB Debug — `USB=0` 正常 |
| extcon2 | c440000.qcom,spmi:qcom,pmi8998@2:qcom,qpnp-smb2 | charger VBUS 检测 — 纯数据线时 `USB=0` |
| extcon3 | vendor:extcon_usb1 | 辅助 USB 控制器 |
| extcon4 | c440000.qcom,spmi:qcom,pmi8998@2:qcom,usb-pdphy@1700 | **PD PHY — 最关键！** `USB=1 USB_HOST=0` = 有连接但不是 host；`USB_HOST=1` = host 模式激活 |

### Phase 4: dual_role_usb 状态

```bash
cat /sys/class/dual_role_usb/otg_default/mode        # ufp (device) or dfp (host)
cat /sys/class/dual_role_usb/otg_default/data_role    # device or host
cat /sys/class/dual_role_usb/otg_default/power_role   # sink or source
cat /sys/class/dual_role_usb/otg_default/supported_modes  # 支持的协商模式
```

### 决策树

```
/sys/class/typec/ 存在?
├── YES → preferred_role 可写? → A 方案可行 (写 PD PHY 寄存器)
│               └── 不可写 → 需 i2c 直接操作 PD 芯片 (高风险)
└── NO  → 无 Type-C class → A 方案无合法入口
          ↓
dmesg 存活捕获有 USB 事件?
├── YES → DWC3 退出 low power + XHCI 启动 + 设备枚举
│   → Layer 1 通了! → 专心修 layer 2 驱动绑定
│   → 用 Method C (unbind+driver_override+bind) + watchdog
│
├── YES → 只有 Type-C 事件但 DWC3 没唤醒/XHCI 没启动
│   → 角色仲裁拒绝 → 试 OTG Y 线 / 独立供电 hub
│
└── NO (零事件 — 仅限存活捕获已验证后)
    → 硬件检测中断真没触发
    → 问题在 CC 检测电路或固件层
    → D 方案 (OTG Y 线) 大概率无效
    → 建议: 使用独立供电的 USB-C dock/hub
```

### 各方案优先级 (E/A/C/B/D 框架)

| 方案 | 做法 | 可行性 | 风险 | 优先级 |
|------|------|--------|------|--------|
| **A: extcon/PD PHY** | 操作 PD PHY 芯片让硬件发出 USB_HOST 信号 | 低 — 依赖 CONFIG_TYPEC 或 i2c 访问 | 高 — i2c 写寄存器可能损坏充电电路 | 仅在 typec class 存在时尝试 |
| **C: configfs/setprop** | 改 USB gadget 配置 (`persist.sys.usb.config`) | 低 — 只影响描述符，不改角色 | 无 | 顺手试 |
| **D: OTG Y 线** | 硬件旁路，硬拉 CC/ID 引脚 | 中 — 取决于固件是否允许 UFP-only 端口切换 | 低成本 | 试错选项 |
| **B: 内核模块 hook** | 编译可加载模块覆盖 USB 设备匹配 | 最低 — 只解决 layer 2，layer 1 不通时无用 | 高 — ABI 匹配噩梦 | 最后 |
| **❌ E: 换网卡芯片** | 从 AX88772D 换 RTL8152/8153 | 在 layer 1 不通时完全无效 | 伪选项 | **已废弃** — layer 1（host 模式）不解决前，换任何 USB 设备都没用 |

### ⚠️ Pitfall: 硬件 OTG 自动检测可能被固件锁死 — 先排除捕获失败

**典型症状**（Mi8/dipper kernel 4.9.337）：
- 插入 USB 设备后 extcon4 始终 `USB=1 USB_HOST=0`
- DWC3 mode 写入 `host` 不生效
- `/sys/class/typec/` 不存在
- dmesg 在插入瞬间显示**零 USB/extcon/dwc3 事件**

**⚠️ 关键纠正**：上述症状中的「零 dmesg 事件」在 Mi8 上被证明是 **false negative**——第一次捕获使用 `adb shell "su -c 'nohup ... &'"` 模式，nohup 进程在 ADB shell 断连时被 SIGHUP 杀死，实际上 PD PHY 正常检测到了设备并触发了完整的 host 模式切换。

**只有用已验证的 `nohup sh -c "...""` 模式存活捕获后，如果仍然零事件，才能下"硬件锁死"的结论。**

**实际结果（经存活验证的捕获）**：
- PD PHY 产生了 `Type-C Sink connected` 事件
- DWC3 退出了 low power 模式
- XHCI 控制器启动
- USB 设备被枚举（被错误驱动 ax88179_178a 绑定）

→ **Layer 1 工作正常。问题纯在 Layer 2（驱动绑定）。**

**根因**：DWC3 控制器和 PD PHY（pmi8998）之间的角色协商链路状态需要**真实的物理插入事件**来触发 extcon notifier 回调。在 ADB USB 线插入时，PD PHY 已经协商为 UFP 角色，此时手动写 `host` 到 mode 文件是软触发——DWC3 的 `dwc3_otg_set_mode()` 被调用但 PD PHY 没有产生 host 事件的 extcon 通知，所以切换不生效。

**但关键在于：当 ADB USB 线拔掉、AX88772D 插入时，PD PHY 能正常检测到 Type-C Sink → 发出 `USB_HOST=1` 事件 → DWC3 退出 low power → XHCI 启动。** 这是硬件自动完成的，不是靠写 sysfs。

**处理**：
1. 先运行 Phase 1-4 诊断（**使用已验证的 nohup sh -c 捕获模式**）
2. 如果宿主模式确实不通（即使存活捕获也零事件）：考虑外接独立供电的 USB-C dock/hub
3. 如果宿主模式通了但驱动绑定错（最常见）：用 unbind + driver_override + rebind 修复

详见 `references/usb-host-mode-deep-diagnostics.md`。

## ⚠️ Pitfall: MagiskSU 与标准 su 语法差异

MagiskSU 的 `-c` 参数要求把整条命令紧跟在 `-c` 后面，**不支持多行字符串**。复杂脚本应推送到设备执行，而不是尝试用内联命令。

```bash
# ✅ 正确：推送脚本文件后执行
adb push script.sh /tmp/ && adb shell "su -c 'chmod 755 /tmp/script.sh && /system/bin/sh /tmp/script.sh'"

# ❌ 错误：多行内联命令会导致语法错误
adb shell "su -c '
  echo line1
  echo line2
'"
```

## ⚠️ Pitfall: Mi8 USB-C 物理上是 USB 2.0 的

**关键事实**：Mi8 (dipper) 的 USB-C 口**只走了 USB 2.0 信号线**（D+/D-），没有焊接
SuperSpeed 差分对。SD845 的 DWC3 虽支持 USB 3.1，但小米没把线连出来。

**验证**：
```bash
adb shell "cat /sys/bus/usb/devices/usb1/speed"
# 480 = USB 2.0 High-Speed
# 如果显示 5000 才是 USB 3.0 SuperSpeed
```

**影响**：任何千兆 USB 网卡在 Mi8 上都被限制在 USB 2.0（480 Mbps 理论），
去掉协议开销后实际约 280–330 Mbps 上限。这是物理层天花板，不是网卡问题。

## ⚠️ Pitfall: RTL8152 USB 2.0 百兆网卡 Rx status -71 协议错误

**现象**：RTL8152 能协商 100/full，但实测吞吐只有 ~700 KB/s（理论 ~12.5 MB/s）。`dmesg` 出现大量 `r8152: Rx status -71`。

**根因**：`-71` = `-EPROTO`（Linux USB 协议错误）。Android 手机 USB 驱动和 RTL8152 芯片的兼容性问题，导致接收端 USB 数据传输层报错，吞吐受限。

**诊断**：
```bash
# 查 dmesg 有无 Rx status -71
adb -s <设备> shell "dmesg | grep 'Rx status -71'"
# 如果有大量记录 → USB 协议层报错

# 检查 USB 设备路径（确定网卡是否直接连手机还是过 Hub）
adb -s <设备> shell "dmesg | grep 'r8152' | tail -5"
# 路径 1-1 = 直连 root hub（直接插手机）
# 路径 1-1.3 = 过 Hub（1-1 是 Hub, 1-1.3 是 Hub 端口 3）
```

**影响**：
- 直插手机：约 700 KB/s（~5.6 Mbps）
- 经过 Hub：进一步恶化到 ~2.8 KB/s（几乎断流）
- **Mac 上不受影响**（macOS 用不同驱动栈，不会报此错误）— 可插 Mac 验证网卡本身好坏

**处理**：这是 Mi8 USB 驱动对 RTL8152 的兼容问题，非网卡硬件故障。

## ⚠️ Pitfall: RTL8152 carrier 闪断导致上行吞吐塌缩

**现象**：`dmesg` 频繁出现 `r8152 eth0: carrier off` → 数秒后 `carrier on`，上行吞吐极低（42 KB/s），但 `speed/duplex=100/full` 不变。

**根因**：
- carrier off/on = 链路层重协商，TCP 发送窗口反复塌缩
- 可能原因：USB 供电不足、Hub 级联信号衰减、网线接触不良、路由器端口策略
- 注意 carrier off/on 不等同于网卡坏了（能自动恢复且协商 100/full）

**诊断**：
```bash
# 查看 carrier 闪断频率
adb -s <设备> shell "dmesg | grep 'carrier' | tail -20"

# 验证链路层状态（即使 carrier 闪断，speed/duplex 也可能正常）
adb -s <设备> shell "cat /sys/class/net/eth0/speed; cat /sys/class/net/eth0/duplex; cat /sys/class/net/eth0/carrier"
```

**处理**：
- 如果过 Hub 出现，先跳过 Hub 直插手机测试
- 如果直插也闪断，检查网线和路由器端口
- 如果直插不闪断但过 Hub 闪断 → Hub 问题（供电不足或芯片不稳）

## 系统化对比测试方法论（Hub vs 直插 vs 跨设备）

当怀疑 USB 网卡或 Hub 有问题时，系统性对比测试定位故障点：

**测试矩阵**：

| 测试 | 下载速度 | 链路状态 | 内核错误 |
|---|---|---|---|
| 直插 Android | | | |
| Hub → Android | | | |
| 直插 Mac | | | |
| Hub → Mac | | | |

**执行步骤**：
1. **拓扑确认**：先查 USB 设备树确认当前连接方式
   ```bash
   # Android 侧
   adb shell "for d in /sys/bus/usb/devices/*/product; do echo \"\$(basename \$(dirname \$d)): \$(cat \$d 2>/dev/null)\"; done"
   # Mac 侧
   system_profiler SPUSBDataType 2>/dev/null | grep -A3 "Product"
   ```
   路径格式 `1-1` = 直连 root hub；`1-1.3` = 过 Hub

2. **链路检查**：speed, duplex, carrier, errors
3. **dmesg 错误扫描**：搜 `Rx status`、`carrier off/on`、`reset` 关键词
4. **吞吐测试**：
   - 用 HTTP server + curl 测下载（如 Python http.server）
   - 用 `curl --interface <iface>` 强制指定出口
   - 记录 speed_download（B/s）
5. **Mac 端交叉验证**：同一套硬件插 Mac，如果速度正常 → 问题在 Android USB 驱动侧

## ⚠️ Pitfall: AX88772D 在 Mac 上间歇性检测

**现象**：插上后 `system_profiler` 一会儿能看到设备，一会儿又没了。`ifconfig` 没有 en 接口。

**原因**：USB 连接不稳定（线缆质量、接触不良、供电不足）。

**排查步骤**：
```bash
# 1. 确认设备本身是好的（插到另一台电脑验证）
system_profiler SPUSBDataType 2>/dev/null | grep "0x1790"
# 有输出 → 硬件正常，是连接问题

# 2. 换一根高质量 USB-C 线
# 3. 确保供电足够（某些 OTG 方案供电不足）
# 4. 检查 ioreg 看设备是否在 IOService 树里
ioreg -p IOService -l 2>/dev/null | grep -i "0b95\|1790"
```

**结论**：
- `system_profiler` 能看到设备（Product ID 0x1790 / Vendor ID 0x0b95）→ **网卡硬件是好的**
- `ifconfig` 没有 en 接口 → macOS 的 CDC-ECM 驱动接上了 USB 但没有创建网络接口（macOS 侧驱动问题，不是网卡问题）
- Mi8 同理：插上后没有 `eth0` → 先检查物理连接稳定性