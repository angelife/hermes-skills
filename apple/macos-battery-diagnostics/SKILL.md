---
name: macos-battery-diagnostics
description: "Diagnose MacBook internal battery health using SMC-level data (ioreg, system_profiler). Detect fuel gauge mis-calibration after cell replacement, measure discharge curve, evaluate cell imbalance, and assess charger performance."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [macos]
tags: [macos, battery, smc, ioreg, diagnostics, fuel-gauge]
---

# MacBook Battery Diagnostics

Diagnose the internal battery of a Mac laptop using gas gauge (fuel gauge) data from `ioreg AppleSmartBattery`, `system_profiler SPPowerDataType`, and `pmset`.

**Architecture note — gas gauge is on the battery PCB, not in SMC:**
The battery's gas gauge IC (Apple uses TI bq series, communicating via SMBus) performs coulomb counting + OCV correction and computes FullChargeCapacity. It reports this to SMC over the bus; SMC caches and relays it upward. The gauge IC stores calibration data in its own data flash/EEPROM. SMC reset does NOT affect coulomb counting or calibration anchors — it only resets sensor-level transient state (fan curves, keyboard backlight, etc.). This distinction drives what calibration paths are viable (see §3 and Pitfalls).

## Diagnostic Principles

These principles govern ALL battery diagnostics. They were derived from user feedback — apply them before any specific workflow step.

1. **Don't trust a single data source** — The system UI saying "Service Recommended" doesn't mean the battery is bad. Cross-validate between `system_profiler`, `pmset`, and `ioreg` raw registers before concluding anything.

2. **Data self-consistency over individual values** — A single number (Qmax=8,856) is weak evidence. A mutually consistent set (Qmax + discharge current + stable temperature + natural cell distribution) is strong evidence. Single values can be faked; a consistent curve is hard to fabricate.

3. **Layer-by-layer reading, top-down** — Start at the system UI layer (`system_profiler`), go deeper to `pmset`, then to `ioreg` driver-level, all the way to raw hardware registers (Qmax, CellVoltage). Each layer has more signal and less processing. Never jump to conclusions at the top layer.

4. **Find contradictions, not answers** — The diagnostic breakthrough is usually a conflict between two data points (MaxCapacity=804 vs Qmax≈8,856). Don't search for "the answer" — search for data that doesn't add up. The contradiction IS the answer.

5. **Official entry points before side channels** — Use `ioreg` (OS standard I/O Kit), `system_profiler` (Apple CLI), `pmset` (power management). Don't use hacks or third-party tools. Official interfaces are documented, stable, and reproducible.

6. **Occam's Razor** — When two explanations fit the data, prefer the one with fewer assumptions. Mis-calibrated gauge (one event) vs. fabricated Qmax + CellVoltage + discharge curve (many events).

This user values understanding WHY over WHAT. When presenting findings, always show the reasoning chain and the conflicting data that led to the conclusion.

## When to Use

- User plugged in a battery and asks "how is it?"
- Battery shows "Service Recommended"
- Battery capacity seems too low or discharges too quickly
- Battery was replaced (new cells on old BMS board) — need to check calibration
- Suspected fuel gauge drift
- Battery not charging when plugged in

## Workflow

### 1. Quick Health Check

```bash
system_profiler SPPowerDataType | grep -E "Condition|Cycle Count|Charge Capacity|State of Charge|Fully|Charging|Amperage"
```

Key indicators:
- **Condition: Normal** → battery is communicating correctly with SMC
- **Condition: Service Recommended** → either the battery is genuinely failing, OR the fuel gauge is mis-calibrated after cell replacement
- **Cycle Count** → indicates usage; 64 cycles but "Service Recommended" is suspicious (likely gauge issue)
- **Full Charge Capacity** vs **Design Capacity** → if wildly different from Qmax (below), gauge is likely wrong

### 2. Deep SMC Fuel Gauge Read

```bash
ioreg -n AppleSmartBattery -r
```

Critical fields to extract:

| Field | What it tells you |
|-------|-------------------|
| `AppleRawMaxCapacity` | What the fuel gauge THINKS the full capacity is (may be wrong) |
| `AppleRawCurrentCapacity` | Current charge in gauge's scale |
| `BatteryData > Qmax` | Per-cell chemical capacity **(the truth about the cells)** |
| `BatteryData > CellVoltage` | Each cell's voltage |
| `BatteryData > DesignCapacity` | Original factory spec |
| `BatteryData > StateOfCharge` | Gauge's SoC percentage |
| `Voltage` | Pack voltage (3-cell: 12.6V full; 4-cell: 16.8V full) |
| `Amperage` | + = charging, - = discharging, 0 = idle |
| `Temperature` | In 0.1 Kelvin (subtract 2732, divide by 10 for °C) |
| `FullyCharged` | Boolean — gauge's sense |
| `ExternalConnected` | Is AC adapter plugged in? |
| `IsCharging` | Is current flowing into battery? |
| `ChargerData > NotChargingReason` | Code for why charging stopped (see references) |

### 3. Gauge Mis-calibration Detection (Critical Test)

**When this applies:** Battery has been replaced with new cells but the old BMS board was reused. The fuel gauge stores calibration parameters in non-volatile memory that reflect the OLD (dead) cells.

#### Cross-validation technique (data integrity check)

Before trusting any battery register, verify data self-consistency:

1. **Qmax inter-cell consistency** — The three Qmax values should be within 1–3% of each other. Identical values = likely fabricated. Wildly different (>10%) = genuine cell mismatch.
2. **Qmax vs DesignCapacity** — Qmax within ±15% of DesignCapacity = healthy cells. Qmax << DesignCapacity = degraded cells.
3. **Qmax vs physical behavior** — Does the discharge current × voltage match a battery of Qmax capacity? ~4.4A × 11.5V ≈ 51W is reasonable for a ~8,800 mAh battery under typical MacBook Pro load.
4. **Temperature sanity** — Healthy discharge stays under 40°C. If temperature spikes above 45°C, the battery has high internal resistance regardless of Qmax.
5. **Voltage recovery** — Does voltage bounce back when load decreases? Yes = normal internal resistance. No recovery = failing cells.

**A single value can be fabricated. A set of mutually consistent curves is much harder to fake.** When the user asks "能作假么" (can this be faked), this is the framework to explain.

#### Diagnosis

| Source | What it means |
|--------|---------------|
| `Qmax` (Cell 1,2,3) | REAL chemical capacity of each cell |
| `AppleRawMaxCapacity` | SMC's learned capacity (gauge) |
| `DesignCapacity` | Original factory spec |

**Diagnostic Signatures:**

- **Qmax ≈ DesignCapacity AND Qmax >> MaxCapacity** →
  The cells are healthy but the gauge has wrong calibration.
  *Fix: Full charge → normal use until system auto-shutdown → immediate full charge. Repeat 2–3 cycles.*

  **Calibration protocol (gas gauge re-anchoring):**

  The gauge's coulomb counter needs two anchor points to converge: a Full-Charge flag (top) and a Shutdown flag (bottom). Without both in the same cycle, the linear interpolation model drifts.

  | Step | Action | What the gauge learns |
  |------|--------|-----------------------|
  | 1 | Fully charge on AC | Sets charge-complete anchor |
  | 2 | Unplug, use normally until **system auto-shutdown** (~3.3V/cell) | Sets discharge-complete anchor |
  | 3 | **Immediately** full charge without interruption | Full cycle observed; gauge prepares MaxCapacity update |
  | 4 | **After reaching 100%, keep AC plugged for 20–30 more minutes** | Charge-terminate relaxation — gauge commits FCC update (step 4 is the most commonly missed step) |
  | 5 | Repeat steps 1–4 for 2–3 cycles | Each cycle refines the estimate toward Qmax |

  **Critical rules:**
  - Do NOT discharge to hardware protection cutoff (3.0V/cell). The software shutdown at ~3.3V/cell is sufficient and avoids risk of over-discharge damage.
  - Do NOT interrupt the recharge mid-cycle — partial cycles don't set the anchor.
  - **Hold at 100% after charging** — FCC (Full Charge Capacity) is NOT committed the instant the battery hits 100%. Most gas gauges (including Apple's TI BQ series) require the battery to remain in charge-terminate state (taper current, voltage stable) for several minutes to tens of minutes before committing the new MaxCapacity. If you unplug immediately at 100%, the gauge may not trigger the update. The TI learning cycle spec calls this "Chg Relax Time" — either 2 hours or voltage change < 4µV/s per cell, whichever comes first.
  - One deep cycle rarely converges from severely drifted MaxCapacity (e.g. 15% of Qmax). Expect sequential steps (e.g. 15%→30%→50%→...). Track `MaxCapacity` after each cycle.
  - SMC reset does NOT affect coulomb counting calibration. Don't waste time on it. (Sources: Battery University BU-603, iFixit MacBook Battery Calibration, Analog Devices gas gauge application notes.)
  - **Use `ioreg` Raw values, not system UI** — The macOS battery icon/menu may have additional smoothing/cache. Read `AppleRawMaxCapacity` (or `MaxCapacity` on newer macOS) from `ioreg -l -w0 -r -c AppleSmartBattery` for the gas gauge's internal state, not the system UI percentage.

  **Why one cycle may not be enough (TI learning cycle DOD0 requirement):**
  The gauge's learning cycle requires a **DOD0 (Depth of Discharge based on OCV) difference > 90%** between the empty state and the full state to update Qmax. If the discharge stops at system auto-shutdown (~3.3V/cell), DOD0 difference might be only 70–80% — enough to increment CycleCount but insufficient to trigger the FCC update. This is the most common reason the first cycle doesn't change MaxCapacity, even when CycleCount increases. Solution: run the next cycle and discharge slightly deeper (to 1–2% battery, not to hardware cutoff), giving the gauge a wider DOD0 window. (Sources: TI SLUA903 "Achieving the Successful Learning Cycle", TI SLUA777 "How to Complete a Successful Learning Cycle for the bq28z610".)

- **Qmax << DesignCapacity** → The cells themselves are degraded.
  *Replace cells. No calibration will fix this.*

- **Qmax ≈ MaxCapacity** → Gauge and cells agree. The reported capacity is real.

### 4. Charging Circuit Test

When the battery is on AC power:

```bash
# Charger identification
system_profiler SPPowerDataType | grep -A 10 "AC Charger"
```

Check:
- Is the charger detected? (85W/96W/140W — should match machine)
- Is `ExternalConnected = Yes`?
- Is `IsCharging` showing current flow? (Amperage > 0)
- If `IsCharging = No` but `FullyCharged = No`, check `NotChargingReason`

**Temperature under charge:** Normal is 25–40°C. Above 45°C = problem.

### 5. Cell Balance Check

Compare the three cell voltages from `BatteryData > CellVoltage`:

| Spread | Assessment |
|--------|------------|
| < 30mV | ✅ Excellent — cells well balanced |
| 30–80mV | ⚠️ Fair — normal aging |
| 80–150mV | ❌ Poor — cells diverging |
| > 150mV | 🔴 Critical — one cell is significantly weaker |

**Load vs idle:** Always check cell balance under load (discharging). Idle balance can look perfect while load balance reveals problems.

### 6. Discharge Monitoring

When the user runs a discharge test (unplug AC, let battery drain):

```bash
# Quick status
pmset -g batt

# Detailed SMC data
ioreg -n AppleSmartBattery -r | grep -E '"Voltage"|"Amperage"|"AppleRawCurrentCapacity"|"AppleRawMaxCapacity"|"Temperature"|"FullyCharged"|"ExternalConnected"|"IsCharging"|"NotChargingReason"'
```

**⚠️ CRITICAL: Save data continuously.** When testing a suspect battery, power may cut at any moment. After EACH reading, append to a file. Do not wait until the end to save. The user expects this — losing data to a sudden shutdown is unprofessional.

Create a monitoring log:
```bash
echo "=== t=+Xmin ===" >> /path/to/log.md
date '+%H:%M:%S' >> /path/to/log.md
ioreg -n AppleSmartBattery -r 2>&1 \
  | grep -E '"AppleRawCurrentCapacity"|"Voltage"|"Temperature"|"CellVoltage"' \
  >> /path/to/log.md
```

Sample every 30–60 seconds until shutdown.

### 7. Interpreting Discharge Curve

Track these metrics over time:

| Metric | What to watch for |
|--------|-------------------|
| Capacity (mAh) | Should drop linearly; spikes = gauge update artifact |
| Voltage (mV) | Gradual decline; sudden drop = internal resistance issue |
| Temperature (°C) | Should stay under 40°C; rising temp + falling voltage = problem |
| Cell spread (mV) | Widening under load = imbalance; should recover on rest |

**The gauge's SoC is unreliable if MaxCapacity is wrong.** The true state of charge is reflected by the Qmax-based ratio, not the gauge percentage.

**Mid-discharge gauge learning phenomenon:** The SMC can update `AppleRawMaxCapacity` upward *during* a deep discharge, not only after a full cycle. In one observed case, MaxCapacity jumped from 804→1,316 mAh while still discharging past the gauge's declared 0% mark. If you see MaxCapacity increase during a discharge, this confirms the gauge was wrong and is self-correcting.

**"0:00 remaining but still running" pattern:** When the gauge reports 0 minutes / 0% remaining but the Mac keeps running for another 20+ minutes, this is definitive evidence of gauge mis-calibration. Document the time gap — it's the user's best evidence that their battery isn't actually dead. This also gives a rough sanity check: if the battery runs for N minutes past "empty" at ~60 mAh/min, the actual remaining capacity is roughly N × 0.06 × (real_max/804) Ah.

**Deep discharge cell behavior:** Cell imbalance at full charge is typically minimal (<30mV on healthy cells). As the battery discharges past the gauge's 0% mark, cell spread widens dramatically — from 18mV at full to as much as 193mV near the protection cutoff (3.2V per cell). This is normal for a deep discharge and does NOT by itself indicate cell failure. The worst cell will hit ~3.4V while the best is still above 3.6V.

### 8. Verification After Calibration

After a full discharge-recharge cycle, verify:

```bash
system_profiler SPPowerDataType 2>&1 | grep "Full Charge Capacity"
ioreg -n AppleSmartBattery -r 2>&1 | grep "AppleRawMaxCapacity"
```

Expected outcome after successful calibration:
- `AppleRawMaxCapacity` jumps from the wrong value (~800 mAh) toward Qmax (~8,800 mAh)
- `Condition` may change from "Service Recommended" to "Normal" (may need 2-3 cycles)

## Pitfalls

1. **Third-party battery monitoring tools (coconutBattery, iStat Menus, Battery Health 3) read the same SMBus/ioreg data natively available to macOS CLI tools.** They don't provide additional diagnostic signal, don't access proprietary gas gauge registers, and cannot initiate or accelerate calibration. Installing one for a calibration check is unnecessary — `ioreg` + `pmset` already gives you the full picture. The main value of coconutBattery is its history graph if you want trend tracking without asking the agent — but for a single diagnostic session, it's just a GUI wrapper around the same numbers.

2. **Modern macOS (15.x) may report `MaxCapacity` instead of the legacy `AppleRawMaxCapacity` key in ioreg.** Both are the same value — just different key names. The skill examples reference both; if `AppleRawMaxCapacity` isn't found, fall back to `MaxCapacity`.

3. **"Service Recommended" does NOT mean "battery is dead."** On a battery with a mis-calibrated gauge, the SMC triggers Service Recommended because the learned capacity dropped drastically. Compare Qmax before concluding.

4. **`BatteryData > Qmax` values are in the nested dictionary.** Parse from the raw `ioreg` output — it's in one big JSON-like block. Use `grep '"Qmax"'` or Python to extract the tuple.

5. **Amperage from `ioreg` is an unsigned 64-bit value for negative currents.** A value like `18446744073709546796` needs conversion: `actual = raw - 2^64`. This represents the actual discharge current in mA.

6. **NotChargingReason codes are not publicly documented by Apple.** Known values:
   - 0 = Charging normally
   - 1 = Not enough power / adapter issue / or normal pause (frequent on healthy batteries)
   - 14 = Charging paused / voltage at target (normal behavior when battery is near full)
   
   Don't over-interpret code 1 — it can mean "not charging right now for acceptable reasons."

7. **Cell voltages under load are always more imbalanced than idle.** A 150mV spread while discharging does not necessarily mean cell failure — compare with the spread after the battery rests.

8. **Fuel gauge updates at discrete intervals.** Two readings 15 seconds apart may show identical values. Wait 30–60 seconds between samples, or trigger an update by changing the load.

9. **Save before shutdown.** When testing a battery that's likely to cut power, write each reading to a file immediately. Don't buffer. The user explicitly expects this (he will remind you if you forget).

10. **Temperature in `ioreg` is in units of 0.1 Kelvin.** To convert: `((temp_value / 10) - 273.15)` for °C, or simpler `(temp_value - 2732) / 10` since the value is in 0.1K increments.

11. **Built-in battery, not USB-C — don't search for external devices.** The Mac's internal battery is always `AppleSmartBattery` in `ioreg`. Don't waste time searching USB devices for a battery.

12. **Battery Health percentage ≠ gauge reading.** `system_profiler` may report 88% health while the gauge shows only 804 mAh. The health percentage is computed differently from the raw MaxCapacity.

13. **SMC reset does NOT fix gas gauge mis-calibration.** SMC is a relay for battery data, not the gauge itself. Resetting SMC clears transient sensor states (fan, keyboard backlight, sudden motion sensor) but leaves the gas gauge IC's coulomb counter and data flash untouched. For gauge calibration, run the deep-cycle protocol (§3), not an SMC reset.

14. **Software auto-shutdown (~3.3V/cell) is the correct discharge target — do NOT discharge to hardware protection cutoff (3.0V/cell).** The hardware protection line is a last-resort safety feature. Repeated hits at 3.0V/cell stress the cells and can trigger permanent protection circuit activation. The system's software low-battery shutdown at ~3.3V/cell is sufficient to set the gauge's discharge anchor without risk.

15. **One deep cycle rarely converges from severely drifted MaxCapacity (e.g. 15% of Qmax).** Expect multi-cycle convergence: each full cycle moves MaxCapacity incrementally toward Qmax. Track the trend, not the absolute value after a single cycle. If 3+ cycles show no movement toward Qmax, the gauge IC may have a more fundamental issue (corrupted data flash calibration table).

16. **Don't contradict your own tools analysis.** If you've just explained that third-party monitoring tools read the same ioreg data as CLI tools and therefore aren't necessary, don't then install one when the user says "你挑一个." Consistency matters — either hold your position or explicitly say you're changing your recommendation.

## Reference Files

- `references/battery-error-code-reference.md` — NotChargingReason codes, PermanentFailureStatus values, and other SMC error codes
- `references/session-2026-07-03-macbook-battery.md` — Full session transcript: cell replacement diagnosis on MacBook Pro 15 inch 2015 with Qmax=8,856 mAh vs MaxCapacity=804 mAh
- `references/gas-gauge-calibration-sources.md` — External reference summaries (Battery University BU-603, iFixit Calibration Guide, Analog Devices gas gauge app notes)
- `references/ti-bq-learning-cycle.md` — TI BQ series learning cycle deep-dive: DOD0 requirement, Update Status flow (0x04→0x05→0x0E), relaxation time constants, Ra table update conditions
