# TI BQ Series Gas Gauge Learning Cycle — Reference

Sources: TI SLUA903 "Achieving the Successful Learning Cycle", TI SLUA777 "How to Complete a Successful Learning Cycle for the bq28z610", LinkedIn practical guide by Oleksii Sylichenko (2024, citing official TI docs).

## Architecture

The gas gauge IC (Apple uses TI bq series, e.g. bq28z610 or similar, communicating via SMBus) stores calibration data in its own data flash/EEPROM. The key registers:

| Register | Address | Purpose |
|----------|---------|---------|
| Qmax Cell 0 | 0x4206 | Learned max capacity per cell |
| Qmax Cell 1 | 0x4208 | Learned max capacity per cell |
| Qmax Pack | 0x420A | min(Qmax Cell 0, Qmax Cell 1) |
| Update Status | 0x420E | Learning cycle progress state |
| Design Capacity | 0x462A | Factory spec (8,600 mAh for the MacBook case) |
| Cycle Count | 0x4240 | Total completed cycles |

## Update Status Flow

```
0x04 (learning in progress)
  ↓  discharge to empty → relax → charge to full → relax
0x05 (QMax updated, Ra learning in progress)
  ↓  if multi-cell: another charge-relax-discharge-relax cycle
0x06 (Ra table updated, learning incomplete — R_a flags not reset)
  ↓  or if R_a flags were reset:
0x0E (QMax + Ra table both updated → learning complete, cell balancing activated)
```

### Update Status 0x04 → 0x05 (QMax update)

Requirements:
1. Full discharge (software shutdown level, ~3.3V/cell)
2. Relaxation after discharge (up to 5h, or voltage change < 4µV/s per cell)
3. Full charge to termination (current drops below taper threshold)
4. Relaxation after charge (up to 2h, or voltage change < 4µV/s per cell)
5. **DOD0 difference > 90%** between empty OCV and full OCV

**DOD0 difference is the most common blocker.** If discharge doesn't go deep enough, the DOD0 (Depth of Discharge from OCV reading) difference will be < 90% and the gauge will NOT update Qmax even if CycleCount increments. Raw DOD0 value of 14,745 = 90% of 16,384 (2^14 range).

### Update Status 0x05 → 0x0E (Ra table + completion)

For multi-cell applications (2s+, including MacBook's 3s), TI explicitly recommends **"another charge-relax-discharge-relax cycle may be run to ensure Update Status changes to 0x0E"**. This means at least 2 full learning cycles are expected for multi-cell packs.

## Relaxation Time Constants

| Phase | Condition | Typical time |
|-------|-----------|-------------|
| Post-discharge relax | Current < Quit Current for Dsg Relax Time, and each cell voltage change < 4µV/s | Up to 5 hours (or ~5 min if voltage stable) |
| Post-charge relax (Chg Relax Time) | Current < Quit Current for Chg Relax Time, and each cell voltage change < 4µV/s | Up to 2 hours (or ~5 min if voltage stable) |

The practical effect: **unplugging immediately at 100% prevents the relax condition from being met**, so the gauge never gets a valid OCV reading and may not commit the Qmax update.

## Ra Table Update Conditions

The impedance table (15 grid points per cell, 0%–100% DOD) is updated during discharge ONLY when:
- Update Status ≥ 0x05 (QMax already learned)
- Charge accumulation error < 2% of Design Capacity
- No negative or invalid Ra values calculated

**Ra update is disabled** (GaugingStatus[R_DIS] = 1) during optimization cycle until QMax is updated. This is why the first cycle only learns Qmax — Ra comes later.

## Key Differences from User-Facing Tools

| Tool/Interface | What it shows | What it hides |
|----------------|---------------|---------------|
| macOS battery menu | Smoothed percentage | Delayed/cached, no raw values |
| `system_profiler` | FullChargeCapacity | May reflect old value before gauge commits |
| `ioreg AppleRawMaxCapacity` | Gas gauge's internal MaxCapacity register | **This is the real-time value** — no smoothing |
| `ioreg AppleSmartBattery.BatteryData.Qmax` | Per-cell chemical capacity | The true capacity of cells (if recently learned) |

## Practical Rules from This Session (2026-07-03)

1. **Hold at 100% for 20-30 min after charging** — The gauge needs Chg Relax Time to commit FCC. Don't unplug immediately.
2. **System auto-shutdown (~3.3V/cell) is the correct discharge target** — Not hardware protection (3.0V/cell). HW protection is last-resort safety, not for routine calibration.
3. **Expect multi-cycle convergence** — From 15% drift (MaxCapacity=1,316 vs Qmax≈8,850), a single cycle may only move MaxCapacity incrementally (e.g. 15%→30%), not all the way to 100%.
4. **DOD0 difference may be insufficient on first cycle** — If auto-shutdown happens at 3.43V (70-80% depth), DOD0 difference might be < 90%. Next cycle, discharge slightly deeper (to 1-2%, not 3.0V cutoff).
5. **SMC reset does NOT affect gauge calibration** — The gauge IC is on the battery PCB, not in SMC. Data flash is persistent.
6. **Register write requires unseal key** — Apple does not publish the unseal key for the TI bq series in their MacBook batteries. Even with bqStudio, the key is proprietary.
