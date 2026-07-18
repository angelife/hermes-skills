# MacBook gas gauge 深度校准流程

## 适用场景

MacBook 长期插电使用后，电池误报 "Service Recommended"，MaxCapacity（FullChargeCapacity）严重低于 DesignCapacity，但 Qmax 和电压一致性正常。

## 根因

电池 PCB 上的 TI BQ 系列 gas gauge IC（coulomb counter）因长期浅循环丢失锚点，MaxCapacity 漂移到 Qmax 的 15%~30%。电池化学状态健康，只是 gauge 的线性估算模型失准。

## 校准流程

### 前置验证

```bash
# 验证电池化学状态是否健康（不健康则校准无效）
ioreg -l -w0 -r -c AppleSmartBattery 2>/dev/null | grep -E '"Qmax"|"DesignCapacity"|"CellVoltage"'
```

**健康信号：**
- Qmax ≈ DesignCapacity（三组值接近）
- 三节电压差 < 50mV
- CycleCount < 200

### 第一轮

1. 满充到 100% → **再插着充 20-30 分钟**（等待 charge-terminate 完成）
2. 检查：`ioreg | grep AppleRawMaxCapacity` → 如果已经恢复，完成
3. 如果没变 → 拔电源，正常使用到**系统自动关机**（~3.3V/cell）
4. **关机后静置 1-2 小时**（关键！让 OCV 稳定，gas gauge 做放电 OCV 测量）
5. 插电满充到 100% → 再插 20-30 分钟
6. 检查 AppleRawMaxCapacity

### 第二轮（如果第一轮 MaxCapacity 没动）

**通常原因：** DOD0（放电深度）差不足 90%，gas gauge 不 commit Qmax。

1. 放电到系统自动关机 → 关机后静置 2-5 小时
2. 满充到 100% → 插着 1-2 小时
3. 查 AppleRawMaxCapacity

### 预期效果

- 通常 2-3 轮深循环可恢复至 DesignCapacity 的 80-100%
- 恢复速率取决于放电深度（越深越快收敛）
- Qmax 不变说明化学层健康，恢复只是时间问题

## 关键细节

### 为什么 MaxCapacity 不自动恢复

- CycleCount +1 只说明完成了一次循环，但 gas gauge 需要同时看到**满充锚点 + 放松 OCV + DOD0 差 > 90%** 才 commit Qmax
- DOD0 差的 TI 原始参考值：> 14745 / 16384（约 90%）
- 放电后放松时间不足是首次循环后 MaxCapacity 不变的最常见原因

### TI Learning Cycle 标准要求（SLUA777/SLUA903）

放电到空 → [放松 2-5h] → 充到满 → [放松 2h] → Update Status 0x04→0x05→0x0E

多节串联电池需要额外一轮。

### 不要做的事

- 不要用 SMC reset（不碰 coulomb counting）
- 不要每循环都放到底（3.0V 硬件保护），系统关机点即可
- 不要设自动监控 cron（用户偏好：手动查）
- 不必安装第三方工具——`ioreg` 读 raw 值即足够

## 参考资料

- TI SLUA777: Achieving the Successful Learning Cycle (gas gauge calibration)
- TI SLUA903: BQ28Z610 Technical Reference Manual
- TI E2E forum: QMax Not Updated in Learning Cycle
- Apple Support: iOS 14.5+ battery recalibration
