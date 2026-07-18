# Mi8 (dipper) Full Reinstall Sequence — LineageOS 22.2

Real-world sequence from 2026-06-27 reinstall after Magisk module boot failure.

## Trigger

- Magisk GApps module (600MB+) caused boot-loop
- TWRP 3.7.0 couldn't decrypt /data (FBE)
- TWRP couldn't mount system partition (dynamic partitions, no EROFS support)

## Step-by-step

### 1. Wipe data in TWRP
```
TWRP → Wipe → Format Data → type 'yes' → confirm
```

### 2. Find that device only boots to fastboot
```
$ fastboot devices
a6520fa3    fastboot        # stuck here
```
No amount of `adb shell "reboot"` from TWRP fixes this — the system boot partition is intact but the device won't boot after data wipe. Full reinstall needed.

### 3. Download ROM from Princeton mirror
Build page: https://download.lineageos.org/dipper (SPA, needs JS)  
Mirror: https://mirror.math.princeton.edu/pub/lineageos/full/dipper/YYYYMMDD/

Download files:
- `lineage-22.2-YYYYMMDD-nightly-dipper-signed.zip` (1.1 GiB)
- `recovery.img` (64 MiB)

SHA256 verify both.

### 4. Flash LineageOS recovery
```
$ fastboot flash recovery los_recovery.img
```
DO NOT rely on `fastboot reboot recovery` — it sends the device back to fastboot.  
User must hold **Volume Up + Power** until LineageOS logo appears.

### 5. Boot to recovery + sideload ROM
- Recovery: **Apply update → Apply from ADB**
- Host: `adb sideload lineage22.zip` (~1.1 GiB, ~2 min via USB 2.0)
- Transfers ends at 47% — normal. Do not interrupt.

### 6. Sideload GApps (no reboot between ROM and GApps)
- Recovery: **back → Apply update → Apply from ADB** (re-enable sideload)
- Host: `adb sideload mindthegapps.zip` (268 MB)
- When signature verification fails → tap **"Yes" / "Install anyway"** on device

### 7. Reboot
- **Reboot system now** from recovery
- First boot: 5–15 minutes (dynamic partition resizing + GApps first-run setup)

## Key Pitfalls

| Pitfall | How to handle |
|---------|--------------|
| Device stuck in fastboot after format | Full reinstall required — no shortcut |
| `fastboot reboot recovery` fails on Mi8 | User must use Volume Up + Power hardware combo |
| ADB "unauthorized" in recovery | User taps "Allow USB debugging" on device screen |
| SPA download page returns HTML | Use Princeton mirror directly |
| Sideload stops at 47% | Normal, not an error |
| GApps signature verification | Tap "Yes" — MindTheGApps uses test keys |
| ROM and GApps order | Flash ROM first, then GApps — NO reboot between them |

## ADB Authorization Loop

After every sideload attempt, ADB authorization resets in recovery. If you need to retry a sideload:
1. User taps "Allow USB debugging" on device
2. Then enters sideload mode in recovery
3. Only then does `adb sideload` work
