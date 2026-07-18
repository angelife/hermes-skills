# AppleSmartBattery Error Code Reference

## NotChargingReason (ChargerData dict)

Apple does not publish these codes. The following are empirically observed:

| Code | Meaning | Notes |
|------|---------|-------|
| 0 | Charging normally | Current flowing into battery |
| 1 | Not charging / paused | Vague — can mean "no charge needed", "adapter insufficient", or "normal pause during transition". Most common on healthy batteries when they unplug/replug. |
| 2 | Battery too hot | Temperature above safe charging threshold (~45–50°C) |
| 3 | Battery too cold | Below 0–5°C charging threshold (rare on macOS) |
| 4 | Fully charged | Battery at 100% per gauge |
| 5 | Charging suspended (temperature) | PMU-halted, different from code 2 |
| 6 | Discharging | Normal — not on AC power |
| 7 | Battery not present | No battery detected |
| 9 | PMU disabled charging | Software/configuration disabled |
| 10 | Battery not detected | System can't communicate with gauge |
| 14 | Charging paused / voltage at target | Common near full charge — battery at charge termination voltage, charger in CV mode with minimal current |

**Code 14 + FullyCharged=No:** Battery voltage has reached the termination threshold (~12.64V for 3-cell), but the gauge hasn't declared "FullyCharged" because learned MaxCapacity hasn't been reached. This is typical of gauge mis-calibration.

## PermanentFailureStatus (PermanentFailureStatus field)

| Bit | Meaning |
|-----|---------|
| 0 (0x01) | Permanent failure — general |
| 1 (0x02) | Over-temperature failure |
| 2 (0x04) | Over-voltage failure |
| 3 (0x08) | Under-voltage failure |
| 4 (0x10) | Over-current failure |
| 5 (0x20) | Short-circuit failure |
| 6 (0x40) | Cell balancing failure |
| 7 (0x80) | Manufacturer-specific |

Value `0` = no permanent failure (battery is not "bricked").

## OperationStatus (operation status bitfield)

| Bit | Meaning |
|-----|---------|
| 0 (0x0001) | Discharging |
| 1 (0x0002) | Charging |
| 2 (0x0004) | Charging terminated |
| 3 (0x0008) | Fully charged |
| 4 (0x0010) | Battery present |
| 5 (0x0020) | Over-temperature |
| 6 (0x0040) | Under-temperature |
| 7 (0x0080) | System present |
| 8 (0x0100) | EOS (end of service) |

## Condition (from system_profiler)

| Value | Meaning |
|-------|---------|
| Normal | Battery communicating correctly, no faults |
| Service Recommended | SMC has detected something abnormal — could be genuine degradation OR gauge mis-calibration. Check Qmax vs MaxCapacity to distinguish. |
| Replace Soon | Capacity below 85% of design |
| Replace Now | Capacity below 65% of design |
| Battery Not Recognized | SMC can't communicate with the battery gauge at all |

## Temperature Conversion

`ioreg` reports temperature in 0.1 Kelvin format. Convert:

```
°C = (Temperature_value - 2732) / 10
```

Example: `Temperature = 3092` → `(3092 - 2732) / 10 = 36.0°C`

## Amperage Signed Conversion

When `Amperage` appears as a very large unsigned value (>2^63), it's a negative number in two's complement format:

```python
if amperage > 2**63:
    actual = amperage - 2**64
```

Example: `18446744073709546796` → `18446744073709546796 - 18446744073709551616 = -4820 mA` (discharging)
