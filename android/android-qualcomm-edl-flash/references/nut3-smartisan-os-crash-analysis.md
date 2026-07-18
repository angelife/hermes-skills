# 坚果3 (DT1902A) 异常重启诊断与 EDL 刷机规划

## 设备信息

| 项目 | 值 |
|------|-----|
| 型号 | DT1902A (delta) |
| SoC | Qualcomm SM8150 (Snapdragon 855), msmnile |
| 系统 | Smartisan OS Aries, Android 10 (SDK 29) |
| 分区 | A/B (slot a 当前活跃) |
| RAM | 7.3 GB |
| 存储 | UFS |
| Kernel | 4.14.117-perf+ |
| Treble | `ro.treble.enabled=true`, VNDK 29 |
| Bootloader | locked (`unlocked:no`, `secure:yes`) |

## 症状

- 日常异常重启（用户描述：\"这些天老异常重启\"）
- 插 Mac USB 使用时系统负载飙升→卡死→自动重启
- 重启后 1-2 分钟负载高达 8.67 然后崩溃
- 逐步恶化：从\"偶尔重启\"到\"频繁崩→冷启动→再崩\"循环

## 诊断结论

### 已排除的原因

- ❌ Kernel panic — dmesg 无记录，pstore 不存在
- ❌ 系统软件崩溃 — dropbox 无 SYSTEM_CRASH / SYSTEM_TOMBSTONE
- ❌ 内存不足 — 3.3G/7.3G 已用，swap 未使用
- ❌ 过热关机 — 温度 29-33°C，正常
- ❌ App ANR 导致重启 — ANR 文件有 6 个（6月25-26日），但与重启无关

### 确认的异常

- **电池亏电严重**（2-3%，充电电流仅 485mA USB 口）
- **FSB 文件系统检查**（SYSTEM_FSCK + persist 分区 journal 恢复）— 确认每次关机都是突然断电
- **系统负载极端异常**（启动 1 分钟负载 8.67，远超正常的 <2.0）
- **系统进程泛滥**（699 个进程，system_server 独占 ~600MB RAM）
- **每轮启动必报 4 个 system_server_wtf**（锤子 ROM 通病）
- **IMS 栈 FATAL 错误**（SingoConfig init failed——不影响系统稳定性的 Qualcomm VoLTE 故障）

### 根因评估

**第一嫌疑：Smartisan OS（锤子系统）本身过于臃肿。** 699 个进程 + system_server 600MB 在低电量和 USB 慢充条件下极易触发 PMIC 保护断电。对比：同属老旧设备的 Mi8（845）刷了 LineageOS 跑得非常稳定，说明问题不在硬件寿命而在系统软件。

**第二嫌疑：电池实际容量严重衰减。** 设计容量 4016mAh，但 3.71V 时 battery level 仅显示 2%（正常 Li-po 在 3.7V 应有 15-30% 存余）。老化电池在大负载下电压瞬间跌到 PMIC 保护阈值导致断电。

**待验证：** 刷入干净系统（如 GSI AOSP）后是否仍然崩溃。如果不崩了 → 纯 ROM 问题。如果还崩 → 硬件暗病（PMIC/UFS/主板）。

## EDL 刷机规划

### 需要的硬件

- EDL 工程线（Type-C，淘宝 ~10-15 元）
- 充电头（5V/2A，刷完机用）

### 需要的文件

| 阶段 | 文件 | 来源 |
|------|------|------|
| 1-EDL 连接 | `prog_firehose_ddr.elf` (SM8150 用) | 百度网盘 TWRP 线刷包 |
| 2-刷 TWRP | `twrp.img` (oscar/U3 用) | 百度网盘 `pan.baidu.com/s/1rclOXtZ7SgMfO3xV25MSLA` |
| 3-刷 ROM | GSI 镜像 `system-squeak-arm64-ab-vndklite-floss-secure.img` | 已下载到 Mac: `/tmp/gsi_vndklite_floss.img` (2.3GB) |
| 4-提权 | Magisk v19.3（locked bootloader 兼容版） | 百度网盘或其他渠道 |

### 本地准备工作（已完成）

| 工具 | 路径 | 状态 |
|------|------|:----:|
| edl.py | `/tmp/edl/` | ✅ 已克隆，依赖已装 |
| phhusson GSI (vndklite floss) | `/tmp/gsi_vndklite_floss.img` | ✅ 已解压，2.3GB |
| BaiduPCS-Go | `/tmp/baidupcs/` | ✅ 已解压，13MB 二进制 |

### 待办

- [ ] EDL 线到货
- [ ] 从百度网盘下载 TWRP 线刷包（含 programmer + 底包）
- [ ] 执行 EDL 刷机
