---
name: android-qualcomm-edl-flash
description: 高通 9008 EDL（Emergency Download）模式线刷工作流。适用于所有 locked bootloader 的 Qualcomm 设备（Smartisan/锤子、部分华为、旧款 OPPO/vivo 等）。从 EDL 刷 TWRP → 刷 GSI 第三方 ROM → 刷 Magisk 的完整流程。
---

# 高通 EDL（9008）模式线刷指南

## 适用场景

- 设备 **bootloader 被锁且官方不给解锁**（Smartisan 全系、部分华为/Kirin）
- 设备 **刷成砖**（连 fastboot 都进不去）
- 需要 **不解锁 bootloader** 直接刷 TWRP 或第三方系统

EDL 是高通芯片的底层刷机模式（类似 PC 的 BIOS 烧录模式），绕过 bootloader 安全验证，直接从底层写入分区。

## 前置条件

### 1. 硬件

| 项目 | 说明 | 价格 |
|------|------|------|
| **EDL 线（工程线/9008线）** | Type-C 接口，带开关按钮。通用所有高通设备 | 淘宝 ~10-15 元 |
| 双公头 USB 线 | 部分旧设备（Micro-USB）需自制 | 几块钱 |

### 2. 软件

| 平台 | 工具 | 说明 |
|------|------|------|
| **macOS / Linux** | **edl.py**（[bkerler/edl](https://github.com/bkerler/edl)） | Python 开源工具，不需要 Windows |
| **Windows** | QPST / QFIL（官方高通刷机工具） | 界面工具，适合不熟悉命令行的用户 |

**edl.py 安装：**
```bash
git clone --depth 1 https://github.com/bkerler/edl.git /tmp/edl
pip3 install --break-system-packages --user pyserial colorama pyusb aiohttp requests docopt progress usb
cd /tmp/edl && python3 edl.py --help
# 确认输出显示 Usage: edl.py
```

依赖完全装好后可以运行 `python3 edl.py --help` 看到完整的子命令列表。

### 3. 文件

成功 EDL 刷机需要三方文件：

| 文件 | 用途 | 来源 |
|------|------|------|
| **programmer (Firehose)** | EDL 通讯协议驱动，设备独有，对应具体 SoC（如 sm8150） | 通常从官方线刷包提取，或从售后维修渠道获取 |
| **TWRP 镜像** | 第三方 Recovery，刷入后通过它刷 ROM | 百度网盘 / XDA / 酷安 |
| **底包 (RADIO/firmware)** | 基带固件，刷第三方 ROM 前可能需要先刷 | 同上 |
| **GSI 第三方 ROM** | Generic System Image，走 Project Treble 通用镜像 | GitHub Releases / SourceForge |
| **Magisk APK** | 提权工具（locked bootloader 下注意签名兼容） | GitHub Releases |

## 资源获取

### GSI ROM（通用第三方系统）

只确定了设备支持 Project Treble（`ro.treble.enabled=true`），就可以刷 GSI。

**GSI 类型选择（arm64，A/B 分区）：**
| 后缀 | 含义 |
|------|------|
| `arm64-ab` | ARM64 架构 + A/B 分区 |
| `vndklite` | 降低 VNDK 版本要求，兼容旧 vendor 分区（VNDK 29 设备跑 Android 14/15 GSI 必选） |
| `vanilla` | 无 Google 服务 |
| `floss` | 预装 F-Droid + 开源软件（微 G 推荐） |
| `gapps` | 预装 Google 服务 |
| `secure` | 带密钥验证（部分设备需要） |

**推荐 GSI 源：**

1. **phhusson/treble_experimentations**（AOSP 原生，最稳定）
   ```bash
   # vndklite 版本兼容 VNDK 29 设备（Android 10 手机跑 Android 14 GSI）
   curl -sL -o gsi.img.xz 'https://github.com/phhusson/treble_experimentations/releases/download/v416/system-squeak-arm64-ab-vndklite-floss-secure.img.xz'
   xz -d gsi.img.xz  # 解压得到 ~2.3GB .img
   ```

2. **MisterZtr/LineageOS_gsi**（LineageOS + 安全补丁更新到最新）
   - GitHub: https://github.com/MisterZtr/LineageOS_gsi/releases
   - SourceForge: https://sourceforge.net/projects/misterztr-gsi/
   - 选 `arm64_bvN` 或 `arm64_bgN` 版本（bvN=vanilla, bgN=gapps）

3. **Andy Yan's GSI builds**（SourceForge 长期维护）
   - https://sourceforge.net/projects/andyyan-gsi/

### TWRP + Programmer（设备独有文件）

TWRP 线刷包和 Firehose programmer 文件是**设备独有**的，需要单独获取：

- 百度网盘：搜"设备型号 + TWRP 线刷包"（e.g. 坚果3 TWRP 线刷包）
- XDA Developers 对应设备板块
- 酷安评论区/资源合集

**典型文件名：**
- `prog_firehose_ddr.elf`（SM8150/SD855 时代）
- `prog_emmc_firehose_8953_ddr.mbn`（SD625 时代，实际是 8953 但不是所有设备都匹配）
- `rawprogram_unsparse.xml`（分区布局定义）
- `patch0.xml`（补丁文件）

**注意：** Programmer 文件必须精确匹配设备 SoC（如 sm8150 = SD855），不同 SoC 不通用。

### Baidu Netdisk 下载（资源常在百度网盘）

不下注册百度账号的方法：

1. **在线解析站** `https://baidu.erranium.com` — 贴分享链接，选文件，免费下小文件，大文件收费（交 Google Drive 链接）
2. **BaiduPCS-Go** — CLI 工具，需要百度账号登录
   ```bash
   # macOS 版
   curl -sL -o /tmp/baidupcs.zip 'https://github.com/qjfoidnh/BaiduPCS-Go/releases/latest/download/BaiduPCS-Go-v4.0.1-darwin-osx-amd64.zip'
   unzip /tmp/baidupcs.zip -d /tmp/baidupcs
   /tmp/baidupcs/BaiduPCS-Go-v4.0.1-darwin-osx-amd64/BaiduPCS-Go
   ```
3. **油猴脚本** `syhyz1990/baiduyun` — 浏览器获取直链，配合 Aria2 多线程下载

## EDL 刷机流程

### 第 1 步：进入 EDL 模式

```
1. 设备完全关机（长按电源键 10 秒确保断电）
2. EDL 线插电脑 USB 口
3. 按住 EDL 线上的开关，插入手机 Type-C 口
4. 等待 3 秒后松手
5. 此时电脑上应该出现新的串口或 USB 设备（Qualcomm HS-USB QDLoader 9008）
```

**确认进入 EDL：**
```bash
# Mac/Linux
ls /dev/cu.usbmodem* 2>/dev/null || ls /dev/ttyUSB* 2>/dev/null

# 或快速检查
python3 /tmp/edl/edl.py --portname=/dev/cu.usbmodem* printgpt 2>&1 | head -5

# 如果不确定端口，让 edl 自动扫描
python3 /tmp/edl/edl.py --serial printgpt
```

### 第 2 步：连接并验证

```bash
# 查看分区表（确认连接正常）
python3 /tmp/edl/edl.py --loader=prog_firehose_ddr.elf printgpt

# 如果看到分区列表说明连接成功
```

### 第 3 步：刷入 TWRP

```bash
# 先备份 boot 分区（以防万一）
python3 /tmp/edl/edl.py --loader=prog_firehose_ddr.elf r boot boot_backup.img

# 刷入 TWRP（覆写 recovery 分区或 boot 分区，取决于设备）
python3 /tmp/edl/edl.py --loader=prog_firehose_ddr.elf w recovery twrp.img

# 某些设备 recovery 和 boot 合一（如 A/B 分区）
python3 /tmp/edl/edl.py --loader=prog_firehose_ddr.elf w boot twrp.img
```

### 第 4 步：退出 EDL，进 TWRP

```bash
# 重启设备
python3 /tmp/edl/edl.py --loader=prog_firehose_ddr.elf reset
```

或拔线后手动按键操作：
```
拔掉 EDL 线 → 长按 音量上+电源 → 直到进入 TWRP
```

### 第 5 步：在 TWRP 中刷 ROM

通过 TWRP 的 MTP 或 ADB sideload 传入文件：
```bash
# 设备在 TWRP 中连接电脑
adb devices           # 应该显示设备为 recovery 状态
adb push gsi.img /sdcard/   # 将 GSI 镜像传到手机
adb push Magisk*.apk /sdcard/
```

在 TWRP 界面中：
```
Wipe → Format Data（清除 data 分区加密）
Install → 选择 GSI 镜像（刷入系统）
Install → 刷 Magisk（可选提权）
Reboot → System
```

## Smartisan（锤子）设备特殊注意事项

- **所有 Smartisan 设备 bootloader 官方不提供解锁**。`fastboot flashing unlock` 需要 unlocktoken（锤子从未开放）
- **Magisk v19.3** 兼容 locked bootloader 签名验证；**v20+ 不兼容**（刷了会卡白锤子）
- 原厂 Smartisan OS 每次启动必报 **4 个 system_server_wtf**（UsbcameraService 安全异常、perspective 空指针、SDK_VERSION 不匹配、AlarmManager UI 缺失）——这些是慢性 ROM bug，不影响正常运行
- 锤子 ROM 进程极多（699+ 进程），system_server 单进程占用 ~600MB RAM，负载在启动初期高达 8.0+。这是系统本身过于臃肿
- **坚果3 已知参数：** DT1902A / `product=msmnile` / SM8150(SD855) / A/B 分区 / `ro.treble.enabled=true` / VNDK 29

## 线刷成功后的稳定性对比

- **刷干净系统（如 GSI AOSP / LineageOS）后**，Smartisan 设备通常能获得和 Mi8 同样的稳定性（Mi8 更老但刷了 LineageOS 跑得很稳）
- 如果刷干净系统后仍频繁崩溃，才说明可能存在硬件暗病（PMIC、UFS 存储、主板虚焊）

## Pitfalls

1. **没有 EDL 线就放弃——软件手段无法进入 9008 模式。** Smartisan 设备不支持 `fastboot oem edl`。
2. **Programmer 文件必须精确匹配 SoC。** sm8150 的 programmer 不能用 sm8250 的。找文件时注意确认 SoC 型号。
3. **GSI ROM 的 vndklite 版本不是必须的**——如果设备的 vendor 分区 VNDK 版本较高（≥31），直接刷标准版即可。VNDK 29（Android 10 vendor）的设备跑 Android 14+ GSI 才需要 vndklite 版本。
4. **TWRP 退出后不要自动重启进系统。** 在第一次刷入 TWRP 后，如果设备自动重启进原厂系统，TWRP 会被 recovery-from-boot.p 覆盖。进 TWRP 后要**立即做 Wipe + 刷 ROM**，不要让原厂系统有机会启动。
5. **EDL 模式下的操作不可逆。** 写分区前确认文件正确。建议先备份 boot/recovery 分区。
6. **部分高通设备 EDL 有保护**（secure boot 阻止刷写）。如果 `edl.py` 连接后报 secure boot 错误，可能需要签名的 programmer 文件或冷补丁绕过。
7. **Magisk 版本与 locked bootloader 的兼容性**取决于设备。Smartisan 上仅有 v19.3 确认可用，v20+ 签名不兼容。其他品牌设备可能没有这个限制。
8. **从 Baidu Erranium 下载的资源**如果是免费路径，文件可能被限制在 50MB 以内。大于 50MB 需付费或找其他来源。
