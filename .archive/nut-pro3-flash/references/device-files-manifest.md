# 坚果 Pro3 刷机文件清单（2026-06-29 会话状态）

此文件记录了 2026-06-29 会话结束时所有文件、凭证和状态，
供后续接手的 AI 直接使用。

## 设备身份（关键！不得混淆）

- **正确型号**：坚果 Pro 3（DT1902A，代号 delta）
- **芯片**：骁龙 855（SM8150 / msmnile）
- **错误型号（不要搞混）**：坚果 3（U3 / oscar，骁龙 625）——资源不通用
- **系统**：Smartisan OS Android 10（VNDK 29）
- **Treble 支持**：是
- **Bootloader**：locked（官方不解锁）
- **刷机路线**：EDL 9008 → GSI

## 文件位置

| 文件 | 路径 | 用途 |
|------|------|------|
| edl.py | `/tmp/edl/` | Mac 版高通 EDL 刷机工具 |
| phhusson squeak GSI | `/tmp/gsi_vndklite_floss.img`（2.3GB） | 备用系统（AOSP Android 14） |
| LineageOS 23.2 GAPPS | `~/Downloads/LineageOS-23.2-20260524-GAPPS-EXT4-GSI.7z`（1.1GB） | 主选系统（用户 Safari 手动下载） |
| Magisk v19.3 | `/tmp/nut3_flash/Magisk-v19.3(19300).zip` | Root |
| 手机备份 | `/Users/macos/nut3_backup/`（2.4GB） | 联系人/短信/照片/下载 |
| BaiduPCS-Go | `/tmp/baidupcs/BaiduPCS-Go-v4.0.1-darwin-osx-amd64/BaiduPCS-Go` | 百度网盘 CLI |

## 用户凭证（仅供刷机流程使用）

- 百度账号：`angelifetse / q1w2e3r4`
- BDUSS：`DQ0S3dNWnVOMUV0SlhwV2xPQVhsenlvZGpOQmJQLVh1aE1TRjluUWNsQkdwbWxxSVFBQUFBJCQAAAAAAAAAAAEAAAAR~Lz5YW5nZWxpZmV0c2UAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAEYZQmpGGUJqZ`
- STOKEN：`b7da1ac097a2bb10b4090ff916b49ea514ceed1b24aab4b30a406ce67c8f644a`

## 百度网盘分享链接

| 资源 | 链接 | 提取码 |
|------|------|--------|
| TWRP 线刷包 + 底包（U3，不通用） | `pan.baidu.com/s/1rclOXtZ7SgMfO3xV25MSLA` | `6b33` |
| Magisk v19.3 | `pan.baidu.com/s/1UgLGnM5AdpUgv4wQwBp5Wg` | `prmf` |
| 线刷工具 | `pan.baidu.com/s/11H3ZDzJZhruOFxxNY4ZmmA` | `o5j7` |

## 刷机命令（EDL 线到后执行）

```bash
# 1. 解压 GSI
brew install sevenzip
7z x ~/Downloads/LineageOS-23.2-20260524-GAPPS-EXT4-GSI.7z -o/tmp/los23/

# 2. 插 EDL 线（关机 → 按住开关插入 → 3 秒松手）

# 3. 刷写（需 programmer 文件）
cd /tmp/edl
python3.14 edl.py --loader=prog_firehose_ddr.elf flash system /tmp/los23/system.img

# 4. 重启
python3.14 edl.py reboot
```

## 已创建的文档

- 刷机指南：`hugo-site/content/posts/2026-06-29-nut-pro3-flashing-guide/index.md`
- 工作日志：`hugo-site/content/posts/2026-06-29-tu-work-log-nut-pro3/index.md`
- 本技能：`nut-pro3-flash`
