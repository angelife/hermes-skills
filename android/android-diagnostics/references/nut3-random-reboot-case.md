# 病例：坚果3 (DT1902A) 异常重启诊断

## 症状
用户报告手机"这些天异常重启"，连接 Mac 后检查。

## 诊断过程

### Phase 1 — 基础状态
```
ADB:       8a765553 connected
OS:        Smartisan/Android 10 (SDK 29)
SOC:       Snapdragon 855 (SM8150), 8GB RAM
Battery:   2%, USB charging at ~485mA
Uptime:    4 minutes (刚重启)
Running:   699 processes, 3.3G/7.3G RAM
Temp:      29°C
Boot reason: sys.boot.reason=reboot, ro.boot.bootreason=reboot
```

### Phase 2 — 日志采集

**dmesg（当前启动周期，仅 4 分钟）：** 无 kernel panic、无 OOM、无 watchdog 超时。仅有 WiFi 外设错误和 SELinux 拒绝（非致命）。

**logcat（events/main）：** `system_boot_reason,801,4`（通用重启码）。`VideoCall_LowBattery` 反复出现（低电量切断视频通话）。IMS/SingoConfig FATAL 错误（VoLTE 栈失败，每轮启动都出现，非重启原因）。

**Dropbox（关键！）：**
```
2026-06-28 10:30:11 SYSTEM_BOOT
2026-06-28 10:31:47 SYSTEM_BOOT + SYSTEM_FSCK ← 非正常关机！
2026-06-28 15:07:51 system_server_wtf ×4     ← 慢性 ROM bug，每轮相同
2026-06-28 15:07:56 system_app_wtf (keyguard)
2026-06-28 15:26:46 SYSTEM_BOOT + SYSTEM_FSCK ← 再次非正常关机
```
- **无** SYSTEM_CRASH / SYSTEM_TOMBSTONE
- **2 次** FSCK（persist 分区 journal 恢复）— 确认关机不干净

**电池历史：** 多次深度放电到 6%~18%，当前放电量 78.6 mAh。

**ANR 文件：** 6月25-26日共 6 个，无 root 或 Shizuku 读不了内容。

### Phase 3 — 归因

| 信号 | 发现 | 权重 |
|------|------|------|
| Battery level | 2%，即使插电也只充到 485mA | ⬆️ |
| SYSTEM_FSCK | 两次 persist journal 恢复 | ⬆️ |
| 无 crash 日志 | 无 SYSTEM_CRASH/TOMBSTONE/pstore | ⬆️ |
| Boot reason | 通用 reboot | ➡️ 中性 |
| 温度 | 29°C，正常 | ⬇️ 排除 |
| ROM WTF | 每轮相同，慢性 Bug | ⬇️ 排除 |

**结论：电池严重老化** — 设计容量 4016mAh 但实际可用已远低于标称值。USB 485mA 充电不够维持正常使用，电压跌到 PMIC 阈值时瞬间断电。

### 对电池检测 App 的尝试
- Battery-Info（GitHub release, target SDK 34）在 Smartisan Android 10 上启动后闪退（SplashScreen 显示了但后续 Activity 不存在）
- 该 App 的 launcher Activity 为 `com.mrapps.batteryinfo/.activity.SplashScreen`，splash 完成后主 Activity 缺失
- APK 下载站（APKMirror/Uptodown）均有 Cloudflare 反爬，无法用 curl 直接下载
- AccuBattery 等成熟 App 需用户自行从 Google Play 安装

## 关键教训
- Dropbox 是无 root 诊断重启原因的最可靠工具（重启后不丢失）
- battery l=2 + 3.71V + SYSTEM_FSCK + 无 crash = 典型电池老化模式
- 不要被 system_server_wtf 误导——如果每轮一样，是 ROM 慢性 Bug 不是重启原因

### Phase 4 — 后续发展：多轮重启循环

诊断过程中手机连续发生多次崩溃重启：

| 轮次 | Uptime | Load (1min) | 电池 | 温度 |
|------|--------|-------------|------|------|
| 1 | 4min | 0.70 (基本空载) | l=1→2, v=3.62→3.71V | 29°C |
| 2 | 1min | **8.67** | pulled from ADB | — |
| 3 | 1min | 4.01 | l=3, v=3.71V | 33.5°C |
| 4 | 2min | 1.45 (稳定) | l=3, v=3.72V | 32.7°C→42°C |

第 2 轮负载 8.67 极不正常（8 核骁龙 855），随后系统崩溃。第 3-4 轮逐渐稳定，但温度从 29°C 升到 42°C。整体趋势：系统在 Smartisan OS 重载下越来越吃力，但最终能稳定下来。

**与 Mi8 的对比：** Mi8（骁龙 845）比 Nut3（骁龙 855）还老一年，但刷了 LineageOS 22.2 后运行稳定。说明问题不在硬件年龄，而在 Smartisan OS 本身的系统质量。

### 手术方案：EDL 9008 模式刷机（备选）

由于 Smartisan 从未开放 bootloader 解锁通道，刷机必须走 EDL 9008 模式：

1. 工具：**edl.py**（bkerler/edl, Python 跨平台）替代 Windows 版 QFIL
2. 硬件：**EDL 线**（工程线/9008线），淘宝十几元
3. ROM：**GSI 通用镜像**（phhusson treble_experimentations vndklite 版兼容 VNDK 29 设备）
4. 关键限制：需要 Nut3 专属的 **programmer 文件**（prog_firehose_ddr.elf for sm8150/msmnile），在百度网盘上
5. Magisk 兼容性：locked bootloader 验证签名，v19.3 可用，v20+ 会卡白锤子
