# Gas Gauge Calibration — External References

Authoritative sources cited during the 2026-07-03 MacBook battery diagnosis session.

## Battery University BU-603 — "How to Calibrate a Smart Battery"

**URL:** https://batteryuniversity.com/article/bu-603-how-to-calibrate-a-smart-battery

Key points:
- Smart batteries (gas gauge + coulomb counter on PCB) drift over time due to accumulated counting errors from shallow cycles
- Calibration requires a full discharge + full recharge cycle to reset the discharge and charge flags
- The gauge learns actual capacity by observing the voltage curve during a complete cycle
- Partial cycles do NOT reset the gauge's internal model — only a full charge AND full discharge in sequence works
- Calibration frequency: every 30-40 shallow cycles or every 3 months for best accuracy

## iFixit — MacBook Battery Calibration Guide

**URL:** https://www.ifixit.com/Guide/MacBook+Battery+Calibration

Key points:
- Apple MacBook batteries use TI bq series gas gauge ICs communicating over SMBus
- The gauge stores calibration data (Qmax, Ra table) in non-volatile flash on the gauge IC itself — not in SMC, not in macOS
- macOS only reads and displays what the gauge reports; it cannot write calibration data
- Calibration procedure: charge to 100% → use until auto-shutdown → recharge to 100% uninterrupted
- SMC reset (Shift+Ctrl+Option+Power) does NOT affect gauge calibration — it only resets SMC-level sensor states
- A single calibration cycle rarely restores full accuracy from severe drift; 2-3 cycles may be needed

## Analog Devices — Gas Gauge IC Application Notes

Key points from the TI/ADI gas gauge documentation:
- Coulomb counters use a current-sense resistor and integrator to track charge flow
- The impedance tracking algorithm (CEDV / Impedance Track) requires periodic OCV (open circuit voltage) readings at known States of Charge to calibrate the model
- The gauge detects a "discharge complete" flag when voltage drops below a configurable threshold — this is what the system's auto-shutdown triggers
- The "charge complete" flag is set when current drops below a minimum threshold (typically C/10) during charging at full voltage
- Data flash / EEPROM on the gauge IC stores the calibrated Qmax and resistance tables; these are updated only when the gauge observes a valid learning cycle
- Writing to data flash requires unsealing the gauge IC with a manufacturer-specific key — Apple does not publish this key
- The gauge will still function with drifted MaxCapacity; it just reports wrong numbers until calibration
