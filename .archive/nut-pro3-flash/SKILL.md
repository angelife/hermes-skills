---
name: nut-pro3-flash
description: 坚果 Pro3（delta）EDL 线刷 GSI 完整流程 — 从诊断到刷机
category: hardware
---

# 坚果 Pro3（DT1902A / delta）刷机指南

## 设备关键参数

- **芯片**：骁龙 855（SM8150 / msmnile）
- **系统**：Smartisan OS Android 10（VNDK 29）
- **Treble**：✅ 支持
- **分区**：A/B 双槽
- **Bootloader**：locked（锤子官方不解锁）
- **唯一刷机路径**：EDL 9008 模式

## 核心问题

Smartisan ROM 非常臃肿（每次启动报 4 个 WTF 错误、699 进程），加上电池老化，导致频繁异常重启。
没有第三方 ROM 社区（无 TWRP、无 LineageOS），只能走 GSI 路线。

## 材料清单

### Mac 端已备好

| 材料 | 位置 |
|------|------|
| edl.py（Python 3.14） | `/tmp/edl/` |
| phhusson squeak GSI（vndklite floss，Android 14） | `/tmp/gsi_vndklite_floss.img`（2.3GB） |
| LineageOS 23.2 GAPPS EXT4（Android 16） | `~/Downloads/LineageOS-23.2-20260524-GAPPS-EXT4-GSI.7z`（1.1GB） |
| Magisk v19.3 | `/tmp/nut3_flash/Magisk-v19.3(19300).zip` |
| 手机备份 | `/Users/macos/nut3_backup/`（2.4GB） |

### 还缺

- **EDL 线**（工程线/9008线）— 淘宝或自制（短接 USB 绿+白线）
- **Pro3 的 programmer 文件**（`prog_firehose_ddr.elf` for SM8150）— 需插线后试

## 下载资源

- LineageOS 23.2 GSI：`https://sourceforge.net/projects/misterztr-gsi/files/LineageOS/Android%2016/LineageOS-23.2-20260524-GAPPS-EXT4-GSI.7z/download`
- edl.py：`https://github.com/bkerler/edl`
- GSI 项目：`https://github.com/phhusson/treble_experimentations`

## 刷机流程

1. 解压 GSI：`brew install sevenzip && 7z x ~/Downloads/LineageOS-23.2-*.7z -o/tmp/los23/`
2. 手机彻底关机 → EDL 线插入（按住开关 3 秒松手）
3. 确认 9008 模式：`python3 /tmp/edl/edl.py --loader=prog_firehose_ddr.elf printgpt`
4. 刷写：`python3 edl.py flash system /tmp/los23/system.img`
5. 重启：`python3 edl.py reboot`
6. 刷 Magisk

## 注意事项

- 坚果 Pro 3（delta）≠ 坚果 3（U3/oscar），资源不通
- 需要正确的 SM8150 programmer，否则 EDL 认不了
- 刷机前确认已备份 `~/nut3_backup/`
