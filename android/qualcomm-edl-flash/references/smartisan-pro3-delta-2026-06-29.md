# Smartisan 坚果 Pro3 (delta) 刷机实操记录

完整诊疗日志：`hugo-site/content/posts/2026-06-29-tu-work-log-nut-pro3/index.md`
刷机指南：`hugo-site/content/posts/2026-06-29-nut-pro3-flashing-guide/index.md`

## 设备识别

| 字段 | 值 |
|------|-----|
| 产品型号 | DT1902A |
| 设备代号 | delta |
| SoC | SM8150 (骁龙 855 / msmnile) |
| 系统 | Smartisan OS (Android 10, QKQ1.191222.002) |
| 内核 | Linux 4.14.117-perf+ |
| 存储 | 224G UFS（已用 42G） |
| RAM | 7.3GB |
| Treble | ✅ `ro.treble.enabled=true` |
| 分区 | A/B (`ro.build.ab_update=true`) |
| VNDK | 29 |
| Bootloader | locked (unlocked:no, secure:yes) |
| Boot 原因 | `reboot` (通用) |

## 社区支持

坚果 Pro3 的第三方开发几乎为零：
- ❌ 无 TWRP
- ❌ 无第三方 ROM（LineageOS、crDroid 等均不支持）
- ✅ Programmer 文件 — SM8150 同芯（OnePlus 7 Pro）的 `prog_firehose_ddr.elf` 公开可用，`bkerler/Loaders` 中也有 Smartisan peek-only loader
- ❌ 官方不解锁 bootloader

### Programmer 状态更新

| 来源 | 文件 | 协议 | 可刷写？ | 基于 |
|------|------|------|---------|------|
| OnePlus 7 Pro | `prog_firehose_ddr.elf` | Sahara + Firehose | ⏳ 待验证 | 同 SM8150 芯，已验证 Sahara 握手 |
| bkerler/Loaders smartisan | `fhprg_peek.bin` (x2) | Sahara only (peek) | ❌ 只能读不能写 | MSM_ID `000460e100110022` |

注意：OnePlus 7 Pro 的 programmer 虽然同芯，但 Smartisan 是否锁了 Secure Boot 需要真机验证。

## 唯一可行路线

EDL 线进入 9008 模式 → 使用 OnePlus 7 Pro 的 SM8150 `prog_firehose_ddr.elf` → 刷入 GSI 通用镜像

⚠️ 该 programmer 非 Smartisan 官方 signed，能否通过 Secure Boot 验证需真机实测。

## 设备混淆警告

| 型号 | 代号 | SoC | 误区 |
|------|:----:|:---:|------|
| 坚果3 / U3 | oscar | SD625 | 和 Pro3 **不是同款**，TWRP/programmer 不通用 |
| 坚果 Pro3 | **delta** | SD855 | 本机 |
| 坚果 R1 | trident | SD845 | LineageOS 官方支持 |

初始错误地以为是坚果3，下载了 oscar 的 TWRP 包（`twrp-3.3.1-20190731.23-oscar.img`），该包不适用于 delta 设备。

## 已下载的资源（Mac 端）

| 文件 | 路径 | 大小 | 来源 |
|------|------|:----:|------|
| edl.py 工具 | `/tmp/edl/` | — | GitHub git clone |
| phhusson squeak GSI (A14) | `/tmp/gsi_vndklite_floss.img` | **2.3GB** | GitHub releases 直接下载 |
| **LineageOS 23.2 GAPPS (A16)** | `~/Downloads/LineageOS-23.2-20260524-GAPPS-EXT4-GSI.7z` | **1.1GB** | **用户 Safari 手动下载**（curl 被 SourceForge 挡） |
| Magisk v19.3 | `/tmp/nut3_flash/Magisk-v19.3(19300).zip` | 5.1MB | BaiduPCS-Go |
| 手机全量备份 | `/Users/macos/nut3_backup/` | **2.4GB** | ADB pull |
| 备用 squeak GSI | `/tmp/gsi_vndklite_floss.img` | 2.3GB | GitHub |

### 从百度网盘（BaiduPCS-Go）下载但发现是 U3（oscar）的废文件

- `Smartisan U3 刷机工具 (9.0 专用)/` — 含 TWRP、QPST 工具、底包，全都不适用于 Pro3
- 但 QPST_Toolkit.7z 是通用 Windows 版线刷工具（Mac 上用 edl.py 代替）

### 下载失败记录

- LineageOS 23.2 GSI：GitHub 和 SourceForge 均返回 403/Not Found（curl 被反爬阻挡）
- 用户用 **Safari 浏览器**打开 SourceForge 链接后成功下载
- 经验：大文件 (>500MB) 的 SourceForge/GitHub 下载，curl 经常被挡，优先让用户用浏览器下

## Shizuku 使用

这台 Pro3 装了 Shizuku，启动命令：
```bash
adb shell sh /sdcard/Android/data/moe.shizuku.privileged.api/start.sh
```
成功后可用 Shizuku 权限读被 SELinux 挡住的系统日志。

## 备份内容

通过 ADB 拉取到 `/Users/macos/nut3_backup/`（2.4GB 总）：
- DCIM（相册）：29MB（23 张照片）
- Pictures（图片）：588MB（1608 张）
- Download（下载文件）：1.9GB（63 个文件）
- 联系人、短信、通话记录：已导出为 txt

## 诊断要点

### 症状
- 电池 2%~3%，USB 485mA 慢充
- 多次非正常断电（SYSTEM_FSCK 日志证实）
- 每次启动报 4 个 system_server_wtf（锤子 ROM 通病）
- 无 kernel panic、无 app crash 痕迹

### 关键日志证据
- pstore/ramoops 不存在（排除 kernel panic）
- dropbox 显示 3 次 SYSTEM_BOOT + 2 次 SYSTEM_FSCK
- boot reason = reboot（通用重启）
- dmesg 无 OOM/panic/thermal 记录

## 参考资料

- [edl.py](https://github.com/bkerler/edl)
- [phhusson treble_experimentations](https://github.com/phhusson/treble_experimentations)
- [MisterZtr LineageOS GSI](https://sourceforge.net/projects/misterztr-gsi/)
- [BaiduPCS-Go](https://github.com/qjfoidnh/BaiduPCS-Go)
- 刷机指南：`hugo-site/content/posts/2026-06-29-nut-pro3-flashing-guide/index.md`
- 工作日志：`hugo-site/content/posts/2026-06-29-tu-work-log-nut-pro3/index.md`
- Hindsight 记忆 key：`hindsight_recall(query="nut pro3 flash summary")`
