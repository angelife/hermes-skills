# 2026-07-03 Session: Real MacBook Battery Calibration Case

## Device
MacBook (Intel), macOS 15.7
Battery Serial: D861015004NDGDL3T, Firmware v2
Cycle Count: 64, DesignCapacity: 8,600 mAh

## Symptom
Condition: "Service Recommended"
Full Charge Capacity (MaxCapacity): 1,316 mAh (only 15% of Design Capacity)

## Key Data

| Metric | Value |
|--------|-------|
| DesignCapacity | 8,600 mAh |
| MaxCapacity | **1,316 mAh** |
| Qmax Cell 1-3 | 8,856 / 8,887 / 8,835 mAh |
| Cell Voltage (100%) | 4,212 / 4,188 / 4,230 mV |
| Temperature | 29.6°C |

## Diagnosis
- Qmax ≈ DesignCapacity → cells are chemically healthy
- MaxCapacity << Qmax → gas gauge coulomb counter drifted from years of shallow cycles
- Voltage balance excellent → no cell damage
- Not a "battery replacement with old BMS" case — this is purely calibration drift from prolonged shallow cycling

## Corrective Action
- Full charge → normal use until system auto-shutdown (~3.3V/cell) → immediate full charge
- Expected: multi-cycle convergence (not single-cycle)
- Track MaxCapacity after each cycle

## Correction History
User provided source-backed corrections (Battery University BU-603, iFixit, Analog Devices):
1. Gas gauge is on battery PCB (TI bq/SMBus), not in SMC
2. Discharge to software shutdown (~3.3V), not hardware protection (3.0V)  
3. SMC reset won't help — gauge IC's data flash stores calibration
4. Direct register write requires unseal key — Apple doesn't publish it
