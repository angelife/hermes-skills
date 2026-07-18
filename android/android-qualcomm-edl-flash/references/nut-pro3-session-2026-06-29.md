# Nut Pro 3 (DT1902A / delta) 刷机准备工作日志

## 重要：设备身份纠正

**这是坚果 Pro 3（delta/SM8150/SD855），不是坚果 3（U3/oscar/SD625）。**
最初误当做坚果3，下载了一批错误的 TWRP 和线刷包（oscar），全部不能用。

正确识别方式：
```
fastboot getvar all | grep product
→ msmnile (SM8150 = 骁龙 855 = 坚果 Pro 3/delta)
→ msm8953 (SD625 = 坚果 3/oscar)
```

所有针对坚果3（U3）的刷机资源（TWRP、底包、programmer）在 Pro3 上不通用。

## 当前文件状态（2026-06-29）

### Mac 上已备好的文件

| 材料 | 路径 | 大小 | 说明 |
|------|------|:----:|------|
| edl.py（刷机工具） | `/tmp/edl/` | — | Python3.14 运行，依赖已装 |
| phhusson GSI（AOSP Android 14） | `/tmp/gsi_vndklite_floss.img` | 2.3GB | vndklite 兼容 VNDK 29 |
| LineageOS 23.2 GAPPS（Android 16） | `~/Downloads/LineageOS-23.2-20260524-GAPPS-EXT4-GSI.7z` | 1.1GB | 用户用 Safari 手动下载 |
| Magisk v19.3 | `/tmp/nut3_flash/Magisk-v19.3(19300).zip` | 5.1MB | locked bootloader 兼容版 |
| 手机全量备份 | `/Users/macos/nut3_backup/` | 2.4GB | DCIM/Pictures/Download/联系人/短信/通话记录 |

### 下载失败的文件

LineageOS 23.2 GSI 多次从 GitHub/SourceForge 用 curl 下载均失败（403/Not Found），
最终由用户用 **Safari 浏览器** 手动下载成功。SourceForge 和 GitHub 都反爬虫。

### 待办

- [ ] EDL 线（用户搞定，淘宝或自制）
- [ ] Pro3 的 programmer 文件（`prog_firehose_ddr.elf` for SM8150，插线后试通用 loader）

## 手机诊断概况

完整的诊断流程见 `android-device-diagnostics` 技能。

核心发现：
- 电池 2%~3%，USB 485mA 慢充
- 无 kernel panic、无 tombstones、无 SYSTEM_CRASH
- SYSTEM_FSCK 确认 2 次非正常断电（persist journal 恢复）
- boot reason = `reboot`（通用，非 panic/watchdog 专用）
- Smartisan ROM 每次启动报 4 个 system_server_wtf（通病）
- 699 个进程，启动时负载飙到 8.67

## 文档已发布

- 刷机指南：`hugo-site/content/posts/2026-06-29-nut-pro3-flashing-guide/index.md`
- 工作日志：`hugo-site/content/posts/2026-06-29-tu-work-log-nut-pro3/index.md`
- 技能：`nut-pro3-flash`（已删除，内容归入 class-level skill）

## 下次接手的 AI 须知

1. 设备是 **坚果 Pro 3（delta）**，不是坚果 3（U3）
2. 所有关键文件在 Mac 上路径见上表
3. LineageOS 23.2 GSI 在 `~/Downloads/`，是 7z 压缩包，刷前需解压
4. EDL 线和 programmer 文件还没到手
5. 刷机命令：
   ```bash
   # 解压 GSI
   7z x ~/Downloads/LineageOS-23.2-*-GAPPS-EXT4-GSI.7z -o/tmp/los23/
   # 连接 EDL
   python3.14 /tmp/edl/edl.py --loader=prog_firehose_ddr.elf printgpt
   # 刷 system
   python3.14 /tmp/edl/edl.py flash system /tmp/los23/system.img
   ```
