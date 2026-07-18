# 病例：坚果3 Smartisan OS 异常重启 + 启动循环

## 设备信息
- 型号：DT1902A (delta)
- SoC：Qualcomm SM8150 (Snapdragon 855)
- 系统：Smartisan OS (Android 10)
- ADB ID：8a765553

## 症状
- "这几天老异常重启"
- 插 Mac USB 诊断时，短暂连上 ADB 后卡死，随后自动重启
- 反复出现：启动 1-2 分钟 → 负载飙升（8.67）→ 卡死 → 重启 → 循环
- 有一次彻底黑屏（ADB/fastboot 都无），约 30 秒后自行恢复

## 诊断发现

### 系统日志（Dropbox）
- **3 次 SYSTEM_BOOT**（同一日），**2 次 SYSTEM_FSCK + journal recovery**
- **无 SYSTEM_CRASH / SYSTEM_TOMBSTONE / SYSTEM_RESTART**
- 每次启动相同的 system_server_wtf（AlarmManager / UsbcameraService / ActivityManager / perspective client）
- 结论：每次停机都是**突然断电**（非正常关机），不是 kernel panic 或 app crash

### 电池
- `dumpsys battery`: level=2-3%, voltage=3.68-3.72V, charging at ~485mA (USB)
- 健康：温度 29→42°C（逐轮升高），设计满充 4016mAh
- 低电量 + 慢充，可能 PMIC 保护触发断电

### Bootloader
- `unlocked:no`, `secure:yes`, `bootmode:unknown`
- `fastboot flashing unlock` → 需要 unlocktoken（Smartisan 从未提供）
- `fastboot oem edl` → 不支持
- 唯一刷机路径：EDL 线（9008 模式）

### 负载模式（跨启动周期监测）
| 启动轮次 | 1 min | 状态 |
|---------|-------|------|
| 第 1 次 | 负载 8.67 | 随后卡死 |
| 第 2 次 | 负载 4.01 | 短暂连上后掉线 |
| 第 3 次 | 负载 2.58→1.45 | 稳定 |

负载逐渐降低表明系统在逐轮启动中从崩溃→恢复平衡。温度从 29→33→42°C 但未触发热保护。

## 根因判断

硬件层面找不出确定的单一故障点。最合理的推断：

1. **Smartisan OS ROM 本身不稳定** — 每次启动报 4 个 WTF，跑 699 个进程，system_server 独占 590MB
2. **电池严重亏电（2-3%）** — 电压在 PMIC 保护阈值边缘，加上 USB 慢充入不敷出，负载一高就触发断电
3. **两者叠加** — 即使换了电池，Smartisan OS 的稳定性也无法与 LineageOS 相比

## 用户对比
用户明确指出 Mi8（骁龙 845）比 Nut3 更老但跑得很稳，因为 Mi8 刷了 LineageOS 22.2。这个对比说明：
- **不是硬件年龄决定稳定性**，而是 ROM 质量
- Nut3 如果刷掉 Smartisan OS 大概率也能救活

## 经验教训

1. **不要过早锁定"电池问题"** — 虽然电池有症状，但用户反复纠正后应重新审视 ROM 层面的原因
2. **跨启动周期监测负载** — 负载趋势比单次快照更有诊断价值
3. **用户对设备的了解 > 你的初始诊断** — 用户说"不是电池原因"时应当信任并重新分析
4. **对比法很有效** — 同品牌更老的设备刷了不同系统跑得稳，直接点出问题在 ROM 而非硬件
