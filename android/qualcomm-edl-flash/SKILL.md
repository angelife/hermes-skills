---
name: qualcomm-edl-flash
description: 高通设备 EDL (Emergency Download / 9008) 模式刷机 — 通过 edl.py (bkerler/edl) 在 macOS 上绕过 locked bootloader 刷写 recovery/分区
category: android
---

# Qualcomm EDL / 9008 刷机（Mac 版）

## 适用场景

- 设备 bootloader locked 且无法通过 fastboot 解锁
- 刷成砖，连 fastboot 都进不去
- 需要从底层刷写分区（recovery、boot、system 等）
- 典型设备：Smartisan（锤子）、部分华为/OPPO、锁 BL 的旧高通机型

## 原理

高通设备在 EDL 模式下，通过 Firehose/Sahara 协议与 PC 通信，可以不经 bootloader 验证直接读写存储分区。这需要在物理上让设备进入 9008 模式（通常需要工程线/EDL 线或短接主板测试点）。

## 前置条件

1. **EDL 线（工程线/9008 线）** — 淘宝十几块一根，Type-C 或 Micro-B 视设备而定

### 自制 EDL 线

找一根废旧 USB 数据线（不要用充电线），剥开后短接绿线和黑线：

1. 剥开 USB 线外皮，除去屏蔽网和锡纸
2. 露出黑、白、红、绿四色线
3. **将绿色线（D-）和黑色线（GND）的外皮剥掉，裸露铜线拧在一起**
4. 绝缘胶布包好
5. 插手机时绿黑短接信号会触发电芯的 PBL 检测，进入 9008 模式

注意：部分 Type-C 线颜色不同，需用万用表确认 D+/D-/GND 定义。
2. **设备对应的 Firehose/Programmer ELF 文件** — 高通芯片特定版本，通常包含在线刷包中
3. **目标镜像**（TWRP、boot.img、GSI ROM 等）

## macOS 环境准备

### 安装 edl.py

```bash
# 克隆
cd /tmp && git clone --depth 1 https://github.com/bkerler/edl.git

# 安装依赖
pip3 install --break-system-packages --user docopt pyserial colorama pyusb aiohttp requests progress usb

# 验证
cd /tmp/edl && python3 edl.py --help
```

## 进入 EDL 模式的方法

### 方法 1：EDL 线（推荐，最稳定）

**有开关/按钮的线：**
1. 手机**完全关机**（长按电源键确认关机，不是锁屏），拔掉所有线
2. 按住 EDL 线上的开关/按钮，不松
3. 插进已关机的手机
4. 再插电脑 USB
5. 等 2-3 秒后松开按钮
6. 检查设备：`ls /dev/cu.usbmodem*` 或 `python3 edl.py printgpt`

**没有开关/按钮的线：**
- 直接插进已关机的手机 → 再插电脑 USB
- 如果插上后手机**正常开机显示充电**：说明线没有触发 EDL，可能原因：
  - 线不是真正的工程线（商家发了普通数据线）
  - 手机未完全关机（还在睡眠状态）
  - 尝试：先拔掉，按住音量键+电源键强制关机 → 再插线

> EDL 线触发原理：短接 USB 的 D+（绿线）和 GND（黑线），让 SoC 的 PBL 检测到异常信号后进入 9008 模式。拆开插头可验证绿线和黑线是否拧在一起。

### 方法 2：短接测试点
需要拆机，用镊子短接主板上标有 `EDL`、`9008`、`GND+DM` 的测试点，同时插入 USB。

### 方法 3：fastboot 命令（需 bootloader 支持）
```bash
fastboot oem edl
# 但很多手机不支持此命令
```

### 方法 4：adb 重启到 EDL
```bash
adb reboot edl
# 或
adb reboot emergency
# 需要 root 或 OEM 支持
```

## 核心 edl.py 命令

### 验证连接
```bash
cd /tmp/edl && python3 edl.py printgpt
```

### 读取分区表
```bash
cd /tmp/edl && python3 edl.py printgpt --loader=prog_firehose_ddr.elf
```

### 刷写单个分区
```bash
# 刷 recovery 分区
python3 edl.py w recovery twrp-xxx.img --loader=prog_firehose_ddr.elf

# 刷 boot 分区
python3 edl.py w boot patched_boot.img --loader=prog_firehose_ddr.elf

### 刷写 system 分区（GSI ROM，无需 TWRP）

对于不支持第三方 ROM 的设备，可通过 EDL 直接刷入 Project Treble GSI 通用系统镜像：

```bash
# 确认设备支持 Treble
adb shell getprop ro.treble.enabled  # 应返回 true

# 查看分区类型
adb shell getprop ro.build.ab_update  # true = A/B 分区

# 刷入 GSI 镜像
python3 edl.py w system_a system-android14-gsi.img --loader=prog_firehose_ddr.elf

# 同时禁用 vbmeta 验证（部分设备需要）
python3 edl.py w vbmeta vbmeta_disabled.img --loader=prog_firehose_ddr.elf
```

**GSI 来源推荐（下载难度：SourceForge > GitHub > 直接链接）：**

| 来源 | 优势 | 下载注意 |
|------|------|----------|
| phhusson/treble_experimentations | 有 vndklite 版兼容旧 vendor | GitHub releases 直链可下 |
| MisterZtr/LineageOS_gsi | LineageOS 22/23 (A15/A16) | SourceForge 需浏览器手动下载 |
| Andy Yan's GSI | 多版本可选 | SourceForge 同上 |

**vndklite 说明：** 如果设备的 vendor 是 Android 10（VNDK 29）而目标 GSI 是 Android 14+，需选 **vndklite** 版本。它移除了 VNDK 版本检查，兼容老 vendor。
### 下载陷阱：SourceForge 的 curl 兼容性问题

- `https://sourceforge.net/.../download` 链接，curl 经常返回 403 或 HTML 错误页
- `https://downloads.sourceforge.net/project/.../文件名.7z` 同样被挡
- **可靠方式：让用户用浏览器打开 SourceForge 链接，它会自动选镜像下载**
- 推荐 GSI 来源（实测可下性）：
  - phhusson/treble_experimentations GitHub releases: curl 可直接下载 ✅
  - MisterZtr/LineageOS_gsi SourceForge: 需浏览器手动下载 ❌（curl 全被挡）

### 设备混淆陷阱：同品牌不同型号代号天差地别

Smartisan 设备较多，型号容易混淆，但代号完全不同：

| 型号 | 代号 | SoC | 线下资源 |
|------|:----:|:---:|:---------|
| 坚果3 / U3 | oscar | SD625 | ✅ 有 TWRP 和第三方 ROM |
| 坚果 Pro3 | delta | SD855 | ❌ 无社区支持，仅 GSI |
| 坚果 R1 | trident | SD845 | ✅ LineageOS 官方支持 |

- **坚果3 (U3/oscar) 和 坚果 Pro3 (delta) 不是同一个设备**，TWRP / programmer 文件不通用
- 下载资源前务必先确认设备代号：`adb shell getprop ro.build.fingerprint`
- 代号确认方法也适用于任何高通设备：`adb shell getprop ro.product.board`
### 读取分区
```bash
# 备份 recovery 分区到文件
python3 edl.py r recovery recovery_backup.img --loader=prog_firehose_ddr.elf

# 备份 boot 分区
python3 edl.py r boot boot_backup.img --loader=prog_firehose_ddr.elf
```

### 从 EDL 模式退出
刷完后，长按电源键 10 秒强制关机，然后正常开机或进 recovery。

## 常用设备 Programmer 文件说明

不同的高通芯片需要对应的 Firehose 程序：
- SD835 (MSM8998): `prog_ufs_firehose_8998_ddr.elf`
- SD845 (SDM845): `prog_firehose_ddr.elf`
- SD855 (SM8150): `prog_firehose_ddr.elf`
   - **Public source 1:** OnePlus 7 Pro (`o0xmuhe/play_with_oneplus7pro` GitHub) — 709KB, ELF64, been verified to pass Sahara handshake on Nut 3 Pro (delta/SM8150). Whether full write access works depends on the OEM's Secure Boot configuration.
   - **Public source 2:** `hoplik/Firehose-Finder` on GitHub — `fh_collection/6AD73382/1/prog_firehose_ddr.elf` contains another SM8150 loader
   - **Backup source:** `bkerler/Loaders` — Smartisan-specific `fhprg_peek.bin` (read-only, no write support) under `smartisan/000460e100110022_*`
   - **Cross-device compatibility:** PBL stage checks ELF signature against SoC key. If the device has Secure Boot locked (common on Huawei/OPPO), cross-OEM programmers will be rejected. OnePlus and Xiaomi SM8150 programmers are most likely to work on other OEMs. The only way to know is to try: `python3 edl.py printgpt --loader=prog_firehose_ddr.elf`
- SD625 (MSM8953): `prog_emmc_firehose_8953_ddr.elf`

Programmer 文件通常包含在设备的 EDL 线刷包中（与 rawprogram_unsparse.xml 一起发布）。

### Cross-device programmer 使用技巧

当设备的专属 programmer 未公开时，可尝试同 SoC 其他设备的 programmer：

- **原理：** 高通 Sahara/Firehose 协议第一阶段（PBL 加载）只验证 ELF 签名是否匹配 SoC 的 SecBoot 密钥。如果两个设备使用同一 SoC（如 SM8150），有时其他 OEM 签名的 programmer 也能被加载（取决于 OEM 是否锁了 Secure Boot）
- **来源：**
  - OnePlus、小米等社区活跃品牌的 SM8150/SDM845 programmer 通常公开可用
  - `hoplik/Firehose-Finder` GitHub — 收集了大量 firehose loader，按 MSM_ID 分类
  - `bkerler/Loaders` GitHub — 包含 Smartisan 在内的多品牌 loader
- **验证方法：** 插 EDL 线后 `python3 edl.py printgpt --loader=prog_firehose_ddr.elf`，不报 Sahara/Protocol 错误即可用
- **已知可行案例：** OnePlus 7 Pro (SM8150) 的 `prog_firehose_ddr.elf`（709KB）在坚果 Pro3 (同 SM8150) 上可通过 Sahara 握手（需真机验证刷写权限）

**注意：** 如果设备有 Secure Boot 锁死（如部分 Huawei/OPPO 机型），cross-device programmer 会被拒绝。能连接不等同能刷写。

## 常见 Pitfall

| 问题 | 原因 | 解决 |
|------|------|------|
| `Not in EDL mode` | 设备未进入 9008 | 重新插拔 EDL 线，或检查驱动 |
| `Sahara protocol error` | Programmer 不匹配 或 Secure Boot 锁死 | 确认下载的是对应芯片的正确版本；尝试同 SoC 其他品牌的 programmer（如 OnePlus 7 Pro SM8150）；如果都失败，考虑设备有 Secure Boot 锁定 |
| `Partition not found` | 分区名写错 | 先 `printgpt` 查看正确名称 |
| `Firehose not available` | 设备不支持 Firehose | 少数旧设备只用 Sahara |
| 插线后手机只是充电不进 9008 | 不是真正的 EDL 线，或手机未完全关机，或插拔时序不对 | ① 确认手机已**长按电源键完全关机**（不是锁屏待机）；② 有按钮的线：按住按钮 → 插手机 → 插电脑 → 2-3 秒后松手；③ 无按钮的线：可能有开关需拨到 EDL 档；④ 拆开插头检查绿黑线是否拧在一起（EDA 线原理：短接 D+ 和 GND）；⑤ 以上都试过仍不行 → 线可能是普通数据线，需换一家买 |
| Mac 不识别设备 | 缺少驱动 | 无需额外驱动，`ls /dev/cu.usbmodem*` 能看到即可 |

## 参考案例

参见 `baidu-pan-download` 技能的 `references/nut3-flash-case-2026-06-29.md` 获取具体操作记录。

## 设备混淆注意

Smartisan 设备较多，型号容易混淆：

| 型号 | 代号 | SoC | 社区支持 |
|------|:----:|:---:|:--------:|
| 坚果3 / U3 | oscar | SD625 | ✅ 有 TWRP 和 MoKee |
| 坚果 Pro3 | delta | SD855 | ❌ 无 TWRP/无第三方 ROM |
| 坚果 R1 | trident | SD845 | ✅ LineageOS 官方支持 |

- **坚果3 (U3)** 和 **坚果 Pro3** 不是同一个设备，TWRP 和 programmer 文件不通用
- 确认设备型号的方法：`adb shell getprop ro.build.fingerprint`
  - 含 `delta` 的是 Pro3，含 `oscar` 的是 坚果3

## 安全提醒

- EDL 模式直接从底层操作存储，误刷可能导致设备彻底变砖
- 操作前务必备份当前分区（`edl.py r`）
- 非高通设备不适用（如 MTK、Exynos、Amlogic）
