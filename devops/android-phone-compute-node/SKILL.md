---
name: android-phone-compute-node
description: Root and configure an Android phone as a remote compute node — Magisk via ADB (no TWRP), USB networking, ADB proxy for internet, Termux, post-root caveats
category: devops
---

# Android Phone as Compute Node

Turn a spare Android phone into a network-accessible compute node reachable via ADB, running Termux with proot-distro, for local ML inference or background jobs.

**Hermes Agent deployment on phones**: see `android-phone-hermes-setup` — model filtering, config updates via ADB, gateway restart. Do NOT leave dead models in the model list — they cause 503 errors.

**ADB Reverse + New API**: see `references/adb-reverse-newapi-proxy.md` — 让 Android 设备通过 ADB reverse 使用 Mac 的 New API，含 token 创建、config 写入（debian chroot / Termux 两种环境）、gateway 重启。

**更多参考**:
- `references/termux-network-no-wifi-solutions.md` — 手机无 WiFi 时 Termux 网络方案(含 gnirehtet macOS segfault 记录 + Python HTTP CONNECT proxy 方案 + 离线装包)
- `references/android-setup-recent-findings.md` — Session-logged learnings from Mi8/Mi6 setup
- `references/android-abnormal-reboot-diagnostics.md` — Android 设备异常重启诊断：电池检查、boot reason 分析、放电历史排查

## User Interaction Pattern

When running this workflow, the user prefers:
- **Concise, action-oriented responses** — stop diagnostics immediately when user says "打住" or gives a definitive answer
- **Execute, don't explore** — when user says an adapter is hardware-broken (e.g. "WiFi 是硬件坏了"), accept that as final; do not retry software workarounds
- **Short questions get short answers** — prefer chip name + yes/no
- **Be precise with hardware operation instructions at all times**. 用户明确指出过不够严谨的问题。**DO NOT** say "按电源键→长按重启→选择 Fastboot" or "重启到 Fastboot"—the correct wording is **"关机 → 同时按住电源键+音量键向下"** from powered-off state. 对 recovery 也一样：**"关机 → 同时按住电源键+音量键向上"**。Always state the exact button combination and from-what-state.
- **Use ADB-driven flows over touch** on devices known to have touch issues. Push scripts/commands via ADB shell rather than asking the user to tap things.
- **Report changes when done** — when making multiple modifications on the device (config files, proxy, services), apply them all first, then present a clear summary of what was done, how, and why. Do NOT narrate each step as it happens — user finds that verbose.

## Pitfall: Magisk 首次 root 后 ADB shell su 被阻止

**问题**：刷入 patched boot 并重启后，`adb shell "su -c id"` 返回 `Permission denied`。Magisk daemon (magiskd) 在运行，但 ADB shell (UID 2000) 默认不允许 su。

**根因**：Magisk 默认**只允许应用**调用 su，ADB shell 需要额外授权。

**解决方案**（任选其一）：
1. **手机上操作**：打开 Magisk app → 设置（齿轮图标）→ **超级用户访问权限** → 改为 **"应用和ADB"** 或 **"所有应用"**
2. **先授权 Termux**：在手机上打开 Termux → 输入 `su` → 授权弹窗点允许。这会触发 magiskd 记录允许策略，有时能让 ADB shell 的 su 也通过

**验证**：`adb shell "su -c id"` → 返回 `uid=0(root) gid=0(root)`

## Pitfall: Magisk 首次 root 后 ADB shell su 被阻止

**问题**：刷入 patched boot 并重启后，`adb shell "su -c id"` 返回 `Permission denied`。Magisk daemon (magiskd) 在运行，但 ADB shell (UID 2000) 默认不允许 su。

**根因**：Magisk 默认只允许应用调用 su，ADB shell 需要额外授权。在 Magisk app → 设置 → 超级用户访问权限中需改为"应用和ADB"或"所有应用"。

**验证**：`adb shell "su -c id"` → 返回 `uid=0(root)`

## Pitfall: 设备无任何网络时无法配 Termux

**问题**：Termux 的 `apt-get`/`pkg` 要求网络连接。如果手机 WiFi 硬件坏了且没插 SIM 卡/无移动数据，Termux 装包会卡在 DNS 解析失败。

**根因**：Android 15 的 SELinux/seccomp 沙箱策略阻止了 Termux 应用创建网络 socket。`adb shell su -c curl`（系统 shell）可以上网，但 Termux app（非 root 进程）即使通过 `run-as com.termux` 调用也会报 `socket: Permission denied`。尝试过的方案：

| 方案 | 结果 | 原因 |
|------|------|------|
| gnirehtet reverse tethering | ❌ relay segfault | macOS Rust 版不稳定(exit 139) |
| HTTP CONNECT proxy + ADB reverse | ❌ Termux 内 socket 被拒 | Android 15 沙箱阻止 app 进程建连 |
| mitmproxy + ADB reverse | ✅ 系统 shell 可用，❌ Termux 仍不行 | mitmproxy 本身稳定，但 app 沙箱限制无解 |
| RNDIS 网络共享 | ❌ linkdown | macOS 不支持 RNDIS host 驱动 |
| USB 有线网卡(OTG) | ✅ 预期可行 | 内核已编译驱动，即插即用 |

**方案 A — 先让设备上网**（优先级高）：
- 插 SIM 卡开移动数据：adb shell "svc data enable"
- 或者 USB 网卡（AX88772D）→ OTG 接网线联网

**方案 B — 离线装包**：
- 在另一台上网的设备上提前 pip download / apt-get download 拉好依赖
- 或直接 ADB 推 Python 二进制，跳过 Termux 包管理器

**不要做的事**：
- 不要试图通过 ADB reverse proxy 给 Termux 内联网（如 socks5/HTTP CONNECT 代理）—— Termux 用户空间被 SELinux 阻止创建 socket，这和 DNS 无关
- 不要试图在没有网络的情况下 run-as com.termux apt-get install — 必失败
- 不要在 Termux 里设 resolv.conf 后以为问题解决 — DNS 只是网络链路的最后一环，底层路由不通也没用
- **Plain Chinese reports** — root causes in 人话, not data dumps
- **ABSOLUTELY NO FORMATTING** — This user cannot see any formatted text in Telegram. Pure text only, no markdown, no tables, no headings, no bold/italic.
- **Honest reporting** — Say "没解决" or "失败了" instead of fabricating success. User has zero tolerance for hallucinated results.

## Requirements

- Unlocked bootloader (check: `fastboot getvar unlocked`)
- ADB + fastboot on Mac
- Phone with USB data cable
- Linux kernel with needed drivers (ASIX, RTL815x, etc.) compiled **statically** — `lsmod` will be empty even when drivers exist

## Bootloader & Recovery

**精度要求**：
- Fastboot：关机 → 同时按住电源键+音量键向下（从关机状态开始，不是从开机状态"重启到"）
- Recovery：关机 → 同时按住电源键+音量键向上（从关机状态开始）
- 也可以用 `adb reboot bootloader` / `adb reboot recovery`（如果 ADB 在线时）

**严禁使用的表述**：
- ❌ "按电源键→长按重启→选择 Fastboot"（不够精确，无法执行）
- ❌ "重启到 Fastboot"（用户不知道按什么键）
- 始终写明从什么状态开始、哪几个键同时按

- **Check bootloader unlock**: `fastboot getvar unlocked` (returns `yes` or `no`)
- **ROM flashing**: `fastboot flash boot boot.img` / `fastboot flash recovery recovery.img` / `fastboot flash vendor vendor.img`
- **Check bootloader unlock**: `fastboot getvar unlocked` (returns `yes` or `no`)
- **ROM flashing**: `fastboot flash boot boot.img` / `fastboot flash recovery recovery.img` / `fastboot flash vendor vendor.img`

### Flash Order

1. `fastboot flash recovery <recovery.img>` (TWRP or LOS recovery)
2. Manually boot recovery via **Volume Up + Power** (`fastboot boot recovery.img` for temporary boot; `fastboot reboot recovery` may loop back to fastboot on some devices)
3. Then sideload ROM from recovery UI
4. OR: `fastboot flash boot <boot.img>` (direct, no recovery needed)

## Magisk Root — ADB Method (No TWRP Needed)

Works for LineageOS 22.x (Android 15) with Magisk v30.x.

### Boot Image

```bash
# Extract boot.img from ROM zip
unzip lineage-{CODENAME}.zip boot.img -d /tmp/

# Push to phone
adb push /tmp/boot.img /sdcard/Download/

# Install Magisk Manager APK
adb install magisk.apk
```

**On phone**: Open Magisk → Install → Select and Patch a File → pick `/sdcard/Download/boot.img` → wait for patching

```bash
# Pull patched image
adb pull /sdcard/Download/magisk_patched-*.img /tmp/magisk_boot.img

# Flash via fastboot
adb reboot bootloader
fastboot flash boot /tmp/magisk_boot.img
fastboot reboot
```

### Verify Root

```bash
adb shell su -c id
# → uid=0(root) if authorized
```

**Magisk Superuser policy for ADB shell (UID 2000)**: Magisk v30+ on LineageOS may deny `su` from ADB shell by default, even though `magiskd` is running. The phone's Magisk app → Settings → Superuser Access must be set to **"ADB"** or **"Apps and ADB"** for `adb shell su -c` to work. Alternatively, open Magisk app → Superuser tab → find `shell` entry and allow it.

⚠️ If `su -c` returns `Permission denied` but `magisk -c` shows the version, it is a **policy issue, not a broken install**. The Magisk binary, daemon, and su are all working — just not authorized for the shell user.

## Magisk Diagnosis & Manager Recovery

When user says "I deleted Magisk" but phone still has root-like binary paths:

| Signal | Check Command | What It Shows |
|--------|---------------|---------------|
| Magisk su binary | `ls -la /sbin/su` | `su -> ./magisk` symlink |
| Magisk daemon | `ps -ef | grep magiskd` | PID running as root |
| ADB su context | `ps -ef | grep adbd` | `u:r:su:s0` SELinux context on adbd |
| Magisk version | `/debug_ramdisk/magisk -c` | v30.7 shows `30.7:MAGISK:R (30700)` |

### Restore Manager Without Device Access

See `references/magisk-manager-recovery.md` for the full `adb push + grant` workflow.

## Termux Bootstrap

```bash
# 1. Install Termux APK (GitHub arm64 build — NOT F-Droid version, to match signing)
adb install termux-app_v0.118.3+github-debug_arm64-v8a.apk
adb install termux-api-app_v0.53.0+github.debug.apk

# 2. Initialize
adb shell "run-as com.termux /data/data/com.termux/files/usr/bin/apt-get update -y"
adb shell "run-as com.termux /data/data/com.termux/files/usr/bin/apt-get upgrade -y"

# 3. Install Python + git
adb shell "run-as com.termux /data/data/com.termux/files/usr/bin/apt-get install -y python git"
```

### Termux on Root Caveats

- **`apt` / `pkg` refuses to run as root**: Termux v0.118+ permanently blocks package management commands when executed via `su`. Must use `run-as com.termux` or run commands from the Termux UI directly.
- **DNS resolution failure**: If `apt-get update` returns "Something wicked happened resolving... (7 - No address associated with hostname)", the phone lacks networking (WiFi broken, no data active). See WiFi alternatives below.
- **Storage permission**: `termux-setup-storage` can be triggered via broadcast: `adb shell am broadcast -n com.termux/.app.RunCommandService -a com.termux.app.RUN_COMMAND --es com.termux.app.RUN_COMMAND_PATH '/data/data/com.termux/files/usr/bin/termux-setup-storage'`. Phone will pop a permission dialog.

## USB Networking (Phone Internet)

### When WiFi Is Hardware-Broken

If the phone's WiFi radio is dead, three alternative network paths exist:

#### Option A: USB RNDIS (Mac shares internet to phone)

Enable Internet Sharing on Mac (System Settings → Sharing → Internet Sharing: share from WiFi to "USB 10/100/1000 LAN" or the RNDIS interface). The phone gets an IP like `192.168.128.x`. Requires Mac admin password for the initial setup.

#### Option B: OTG + USB Ethernet Adapter

Plug a USB-to-Ethernet adapter (ASIX AX88772, RTL8153, etc.) into the phone via OTG. The kernel must have the driver compiled in (check `zcat /proc/config.gz | grep USB_NET_DRIVER`). The interface shows as `eth0` or `usb0`. Connect a network cable from the adapter to an active router.

#### Option C: USB Tethering from Another Android

Connect both phones (Mi8 and e.g. Mi6) via USB cable. On the source phone: Settings → Hotspot & Tethering → USB tethering. Mi8 gets a `rndis0` interface with a local IP and DNS via the source phone's data connection.

### Kernel Driver Check

```bash
# Check statically-compiled drivers (NOT via lsmod — they won't show)
zcat /proc/config.gz | grep -E "CONFIG_USB_(NET|RTL8152|ASIX)"
cat /proc/config.gz 2>/dev/null | gunzip | grep -E "(AX8817X|CDC_ETHER|RNDIS)" /dev/null
```

Known working: Mi8 (dipper) kernel has `asix` and `ax88179_178a` drivers built-in.

## Proot Distro Setup

```bash
# Install proot-distro
adb shell "run-as com.termux /data/data/com.termux/files/usr/bin/apt-get install proot-distro"

# Install Ubuntu 22.04
adb shell "run-as com.termux /data/data/com.termux/files/usr/bin/proot-distro install ubuntu-22.04"

# Enter distro
adb shell "run-as com.termux /data/data/com.termux/files/usr/bin/proot-distro login ubuntu-22.04"

# Inside distro: install python3, pip, git
apt update && apt install python3 python3-pip git
```

## Pitfalls

- **Magisk policy blocks ADB shell su**: If `su -c id` returns Permission denied after flashing, open Magisk app and enable ADB superuser access. Do NOT reflash — the install is fine.
- **Termux apt refuses root**: Always use `run-as com.termux` for package operations, not `su -c`.
- **Termux 无网络时**: 不要尝试通过 proxy/gnirehtet 给 Termux 内部联网——Termux 用户空间被 SELinux 阻止创建 socket。必须先解决手机系统网络再 apt-get。
- **`fastboot reboot recovery` loops back to fastboot** on some devices (Mi8 dipper). Use physical Volume Up + Power instead.
- **TWRP incompatible with Android 15 EROFS**: TWRP 3.7.0 does not support Android 15's EROFS filesystem. Use LineageOS recovery or a newer TWRP build.
- **MindTheGapps fails on Android 15 dynamic partitions**: Installer script `get_block_for_mount_point()` can't find `/system`'s block device. Use NikGapps instead.
- **USB adapter MAC address may appear as null** on macOS: check `system_profiler SPUSBDataType` and try reconnecting after sleep wake cycle.
- **APK install from /sdcard/ may fail**: Use `/data/local/tmp/` instead — `adb push` there, then `adb shell pm install /data/local/tmp/file.apk`.
- **Wireless ADB push fails for large files (>10 MB)**: TCP ADB over WiFi/4G/RNDIS cross-subnet topologies cannot sustain multi-MB transfers. See `references/adb-wireless-file-transfer.md` for diagnostic sequence and workarounds (USB ADB, HTTP server pull, chunked base64).

更多网络方案详见 `references/termux-network-no-wifi-solutions.md`。

## ADB Shell & SELinux 文件访问约束

从 ADB shell（Mac）往 Android 设备上 Termux 的数据目录写文件时，受 SELinux 约束，不同操作需要不同方式：

- **读取任意文件**: `su 0 sh -c 'cat <path>'` ✅
- **写 root-owned 文件**: `su 0 sh -c 'cat > <path>'` ✅
- **写 app-owned (u0_a192) 文件**: 先写到 `/data/local/tmp/`，再用 `run-as com.termux cp /tmp/src <app-path>` ✅
- **执行 Termux 二进制**: `su 0 sh -c 'env HOME=... PATH=... python3 ...'` ✅（`run-as com.termux` 不能执行 Termux bin）
- **后台进程**: `su 0 sh -c 'env ... nohup python3 ... &'` ✅

详见 `references/adb-selinux-file-access.md`。

## 安卓系统级代理配置

当 Android 手机（如 Mi8）需要通过 Mac 代理上网（浏览器、系统 app），需设置**系统级代理**而非仅 Termux 环境变量：

```bash
# 设置系统代理
adb shell settings put global http_proxy 192.168.1.8:10808
# 或分步：
adb shell settings put global global_http_proxy_host 192.168.1.8
adb shell settings put global global_http_proxy_port 10808

# 验证
adb shell settings get global http_proxy
# → 192.168.1.8:10808
```

**注意**：`settings put global http_proxy` 影响所有遵守系统代理的 App（浏览器、Java 应用等），但不影响 Termux 内部（需环境变量 `http_proxy`/`https_proxy`）和一些使用自有网络栈的浏览器（Chrome 有自己代理设置）。

## Pitfall: Termux .bashrc 每次启动跑 termux-setup-storage

**问题**：`.bashrc` 里写了 `termux-setup-storage && echo STORAGE_OK > /data/local/tmp/termux_init_done` 但没有前置守卫条件。每次打开 Termux 终端都重新触发存储权限请求，bash 会卡住等待用户点"允许" → 终端看似无响应。

**修复**：

```bash
# 必须加守卫，仅首次执行
[ ! -f /data/local/tmp/termux_init_done ] && termux-setup-storage && echo STORAGE_OK > /data/local/tmp/termux_init_done
```

同时可提前创建标记文件跳过对话框：`adb shell su 0 sh -c 'echo STORAGE_OK > /data/local/tmp/termux_init_done'`。