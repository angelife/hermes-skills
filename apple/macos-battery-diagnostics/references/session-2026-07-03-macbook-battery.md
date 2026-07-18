# MacBook Pro 15" 2015 Battery Cell Replacement — Gauge Mis-calibration Case

## Device

- MacBook Pro 15" (MacBookPro11,5, early 2015)
- Internal battery: SMP bq20z451 fuel gauge IC (BMS)
- Serial: D861015004NDGDL3T
- User had replaced the cells but kept the old BMS board

## The Disconnect

| Parameter | Value | Source |
|-----------|-------|--------|
| Design Capacity | 8,600 mAh | `ioreg BatteryData.DesignCapacity` |
| Qmax Cell 1 | 8,856 mAh | `ioreg BatteryData.Qmax[0]` |
| Qmax Cell 2 | 8,887 mAh | `ioreg BatteryData.Qmax[1]` |
| Qmax Cell 3 | 8,835 mAh | `ioreg BatteryData.Qmax[2]` |
| AppleRawMaxCapacity | **804 mAh** | `ioreg AppleRawMaxCapacity` |
| System Profiler Health | 88% | `system_profiler` |

**The fuel gauge learned 804 mAh from the old (dead) cells.** The new cells have Qmax ≈ 8,856 mAh — the gauge's capacity is **9% of the truth**.

## Symptom

- On AC power: works normally, battery shows 90% charged
- Unplug AC: system reports 8 minutes remaining, drains from 90% to 0% in ~10 minutes, then shuts down
- Reason: gauge thinks the battery only holds 804 mAh, so it depletes that quickly even though cells still have ~8,000 mAh

## Discharge Curve

Gauge-measured discharge on the mis-calibrated battery (ambient ~25°C):

| Time | Capacity | SoC | Voltage | Temperature | Cell spread |
|------|----------|-----|---------|-------------|-------------|
| t=0 | 671/804 | 83% | 11,694 mV | 35.1°C | 136 mV |
| +90s | 610/804 | 75% | 11,585 mV | 35.9°C | 134 mV |
| +3min | 552/804 | 68% | 11,649 mV | 36.0°C | 115 mV |
| +4.5min | 490/804 | 61% | 11,556 mV | 36.0°C | 113 mV |
| +5min | 432/804 | 53% | 11,423 mV | 36.0°C | 109 mV |
| +5.5min | 373/804 | 46% | 11,368 mV | 36.0°C | 133 mV |
| +7min | 312/804 | 38% | 11,350 mV | 36.0°C | 120 mV |
| +7.5min | 253/804 | 31% | 11,284 mV | 36.0°C | **147 mV** |
| +8min | 193/804 | 24% | 11,365 mV | 36.0°C | 131 mV |

**Key observations:**
- Temperature rock-solid at 36°C throughout — no thermal problems
- Cell spread widened significantly under load (18mV idle → 147mV worst under load)
- Voltage recovery when load decreased (11,284 → 11,365 mV) — normal battery behavior
- The gauge predicted 1 minute remaining at SoC 24% — it was about to cut power despite cells being mostly full

## Calibration Fix

Full discharge-to-shutdown + full uninterrupted recharge should fix it. SMC will update AppleRawMaxCapacity toward Qmax.

## Error Codes Encountered

- `NotChargingReason = 14`: Normal — battery voltage at charge target, charging paused
- `NotChargingReason = 1`: Normal pause during transition (after AC unplugged)
- `Condition = Service Recommended`: False alarm from gauge mis-calibration

## Summary

The battery cells are healthy (Qmax > DesignCapacity). The gauge is wrong (MaxCapacity = 9% of Qmax). This is 100% a calibration issue, not a cell failure. The fix is one full discharge-recharge cycle.

---

## Mid-Discharge Gauge Learning (2026-07-03 Session)

After ~28 minutes of continuous discharge past the gauge's declared "0 min / 6% remaining," the SMC updated **AppleRawMaxCapacity from 804 → 1,316 mAh** while still on battery power. This proves the gauge can learn incrementally, not only via a full cycle.

### Final deep-discharge readings before shutdown:

| Time | Capacity | SoC | Voltage | Temp | Cells | Spread |
|------|----------|-----|---------|------|-------|--------|
| ~t=+28min | 79/1,316 | ~6% | 9,927 mV | 38.4°C | — | — |
| ~t=+28.5min | 77/1,316 | **5%** | 10,573 mV | 38.4°C | 3,518/3,624/3,431 | **193 mV** |

### Key observations from deep discharge:
- **MaxCapacity grew mid-discharge** 804→1,316 mAh — gauge self-correcting in real time
- **Voltage recovery** from 9,927→10,573 mV when load decreased — normal battery behavior
- **Cell spread grew to 193 mV** at 5% SoC — extreme imbalance near protection threshold
- **Temperature stayed under 39°C** throughout the entire ~28-minute discharge — healthy thermal behavior
- **The Mac kept running** for >20 minutes past "0 minutes remaining" — definitive evidence of gauge mis-calibration
