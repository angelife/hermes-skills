# Dual-Source Hardware Verification Pattern

Derived from analyzing MacCheck 验机宝 (github.com/andyhuo520/MacCheck).
Applicable whenever verifying second-hand hardware or checking for spec tampering.

## Core Principle

Critical hardware parameters should be read from TWO independent system paths.
If the two sources disagree, the data is likely tampered with — flag immediately.

## macOS Dual-Source Table

| Parameter | Source A | Source B | Tamper Signal |
|-----------|----------|----------|---------------|
| Serial number | IOKit `IOPlatformExpertDevice` | `system_profiler SPHardwareDataType -json` | A ≠ B → RED FLAG |
| Battery cycles | IOKit `AppleSmartBattery` `CycleCount` | `ioreg -rd1 -c AppleSmartBattery` | A ≠ B → RED FLAG |
| Model ID | `sysctl hw.model` | `system_profiler` `machine_model` | A ≠ B → warning |
| Chip type | `system_profiler` `chip_type` | `sysctl machdep.cpu.brand_string` | Cross-check |

## Implementation Pattern (macOS)

```swift
// Source A: IOKit (low-level kernel interface)
let service = IOServiceGetMatchingService(kIOMainPortDefault,
    IOServiceMatching("IOPlatformExpertDevice"))
let serialFromIOKit = IORegistryEntryCreateCFProperty(service,
    kIOPlatformSerialNumberKey, kCFAllocatorDefault, 0)

// Source B: system_profiler (user-space command output)
let output = ShellRunner.run("/usr/sbin/system_profiler",
    ["SPHardwareDataType", "-json"])
let serialFromSP = JSON.parse(output).SPHardwareDataType[0].serial_number

// Cross-check
if serialFromIOKit != serialFromSP {
    // RED FLAG: serial number tampered
}
```

## Key Tools by Layer

| Layer | Tool | Source |
|-------|------|--------|
| Kernel IOKit | `IOServiceGetMatchingService` + `IORegistryEntryCreateCFProperty` | Low-level, hard to spoof |
| sysctl | `sysctlbyname("hw.model")` | MIB-based, kernel-provided |
| shell command | `system_profiler SPHardwareDataType -json` | User-space, easier to intercept |
| shell command | `ioreg -rd1 -c AppleSmartBattery` | Second path for battery data |
| AppleSMC | `IOServiceOpen("AppleSMC")` + `IOConnectCallStructMethod` | Firmware-level, most trusted |

## Security/Registration Checks (macOS)

For verifying activation locks and management profiles:

| Check | Command | What It Detects |
|-------|---------|-----------------|
| MDM enrollment | `/usr/bin/profiles status -type enrollment` | Enterprise/school management |
| Configuration profiles | `/usr/bin/profiles list -all` | Installed restrictions |
| Apple ID login | `defaults read MobileMeAccounts Accounts` | Still-signed-in account |
| Activation lock | `system_profiler SPHardwareDataType` `activation_lock_status` | Find My Mac enabled |

## Three-tier Status System

```
PASS (green)    → All checks clear, data consistent
WARNING (amber) → Minor discrepancy, user should verify manually
RED FLAG (red)  → Two sources disagree on critical data, or lock/management active
```

RED FLAG items (serial mismatch, MDM enrolled, activation lock on) should include
a human-readable explanation of why this matters:

- "Two reads of the serial number disagree — the system data has been tampered with"
- "This machine is under enterprise MDM management — the organization can remotely wipe it"
- "Activation Lock is enabled — the seller must disable it before transfer"

## Reference

Full implementation: MacCheck by andyhuo520
https://github.com/andyhuo520/MacCheck
Architecture: IOKit → sysctl → AppleSMC → system_profiler → ioreg, with
dual-source cross-referencing on serial number and battery cycle count.
