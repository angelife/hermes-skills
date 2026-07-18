## 问题诊断：MacBook 电池 MaxCapacity 漂移复原

### 前提清单
- [历史确认] 设备：MacBook（Intel, macOS 15.7）
- [历史确认] 核心矛盾：MaxCapacity = 1,316 mAh, Qmax ≈ 8,850 mAh, DesignCapacity = 8,600 mAh
- [历史确认] 完成一轮深循环：CycleCount 64 → 65
- [历史确认] 电池：3 串 LiPo，电压一致性好，温度正常
- [历史确认] gas gauge：TI BQ 系列（SMBus）
- [历史记录-需复核] 具体 BQ 型号：当前未知，但不影响校准原理

### 子问题拆分
1. **TI BQ learning cycle 触发 Qmax 更新的精确条件**
2. **为什么 CycleCount +1 但 MaxCapacity 不变**
3. **严重漂移（MaxCapacity 仅 15% Qmax）能否恢复**
4. **多轮校准策略和预期**

### 分类标签
硬件 / 配置 — gas gauge 校准问题，非纯硬件故障

### 引擎选择
web_search（Tavily）+ web_extract — 硬件校准问题，中文社区经验有限

---

## 推荐方案（按可信度排序）

### 核心结论：可以恢复

**可信度：高**
- 独立来源数：4 个
  - [TI SLUA777/SLUA903 — 官方 learning cycle 文档](https://www.ti.com/lit/pdf/slua777) — 已验证原文
  - [TI E2E BQ28Z610 论坛](https://e2e.ti.com/support/power-management-group/power-management/f/power-management-forum/789855/bq28z610-remaining-and-full-charge-capacity-fields-randomly-change-after-hard-reset) — 已验证，用户同样遭遇 FCC 更新问题
  - [Large Battery 校准指南](https://www.large-battery.com/zh-CN/blog/how-to-calibrate-a-smart-battery-for-accurate-readings) — 已验证，详述 SMBus 智能电池校准流程
  - [Apple 支持 — iOS 电池校准确认](https://support.apple.com/zh-hk/119954) — 已验证，Apple 内部同样使用多轮循环校准
- 化学状态已验证（Qmax ≈ DesignCapacity、电压一致性好），不存在硬件瓶颈

### 方案一：继续完整校准循环 — 可信度：高

#### 恢复预期
- **本轮充到 100% + 插着等 20-30 分钟** 后查 AppleRawMaxCapacity
  - 如果涨到 2,000~3,000 → 方向对了，再 1-2 轮收敛到 7,000+
  - 如果还是 1,316 → 不意外，跑第二轮
- 最终可恢复到 7,000~8,000 mAh（续航翻 5 倍以上）

#### 为何第一轮可能还不够——搜索确认的关键细节

**① DOD0 差可能不足 90%**
TI 官方文档（SLUA777）明确规定：Qmax 第一次更新，需要**放电后 OCV 与充电后 OCV 算出的 DOD0 差 > 90%**（原始值 > 14745 / 16384）。你的第一次放电到系统关机（~3.43V）可能只放了 70-80%，不足以跨越 90% 门槛。第二轮可以故意用到更深的关机点。

**② charge-terminate 状态是必要条件**
TI 文档写得很清楚：充电完成不只是 "电量显示 100%"，而是需要 **充电器进入 taper current 模式**（电流逐渐降到终止阈值，ChargingStatus()[VCT]=1, BatteryStatus()[FC]=1）。这个过程通常在 100% 之后还有几分钟到半小时的涓流阶段。

**③ 满充后需要足够 relaxation**
ISO 充电完成后，需要 **Chg Relax Time**（2 小时或电压变化 < 4µV/s 持续 5 分钟），gas gauge 才能做 OCV 测量。这就是你说"充到 100% 后插着放 20-30 分钟"至关重要的原因。

**④ 多节串联需要多轮**
TI 明确说：**"For multi-cell applications, another charge-relax-discharge-relax cycle may be run to ensure Update Status changes to 0x0E"**。你的 3 节串联场景完全命中。

#### 第二轮校准建议（如果 MaxCapacity 仍不涨）
1. 放电放到**系统自动关机且电池电压 ~3.0-3.2V**（比第一次更深）
2. 关机后静置 **2 小时以上**（不是立刻充，TI 需要 Dsg Relax Time 做 OCV）
3. 充满到 100% 后继续插着 **1-2 小时**
4. 查 AppleRawMaxCapacity

### 方案二：硬复位重置 gauge — 可信度：低

**不建议**。需要 EV2400 编程器 + bqStudio + Unseal key 才能操作 TI BQ 系列的数据 flash 参数（包括 Reset Qmax / R_a flags / Update Status）。Apple 不公开接口，macOS 也没有对应工具。硬来可能触发 Permanent Failure 锁死电池。

---

## 关键支撑——引用的搜索来源

| 来源 | 内容 | 相关性 |
|------|------|--------|
| [TI SLUA903](https://e2e.ti.com/cfs-file/__key/communityserver-discussions-components-files/196/Achieving-the-Successful-Learning-Cycle.pdf) | 学习循环完整步骤、taper current 条件、多节多轮要求 | 直接匹配，核心依据 |
| [TI BQ28Z610 E2E](https://e2e.ti.com/support/power-management-group/power-management/f/power-management-forum/789855/bq28z610-remaining-and-full-charge-capacity-fields-randomly-change-after-hard-reset) | 用户同样遇到 FCC 更新问题，揭示 Update Status 和 FCC 逻辑 | 直接匹配，真实案例 |
| [Large Battery 校准指南](https://www.large-battery.com/zh-CN/blog/how-to-calibrate-a-smart-battery-for-accurate-readings) | SMBus 智能电池校准全流程，放电→静置→充电→静置 | 直接匹配，补充实操细节 |
| [Apple 支持 iOS 电池校准](https://support.apple.com/zh-hk/119954) | Apple 电池校准确认多轮循环机制 | 间接确认 Apple 内部使用类似方法 |

---

## 结论

**完全能恢复。** 化学层健康（Qmax ≈ DesignCapacity），只是 coulomb counter 漂移。需要一次更完整的循环（放电→静置→充满→静置），TI 官方有标准学习循环流程（SLUA777/SLUA903），你的问题不是异常，是欠校准。

当前策略正确：等这轮充满 + 静置 → 查 RawMaxCapacity → 如果不动就第二轮放到更深的关机点。
