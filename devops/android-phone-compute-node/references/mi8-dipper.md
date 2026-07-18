# Xiaomi Mi 8 (dipper) — Android Compute Node Notes

## Device Specs (as of Jun 2026)

| Attribute | Value |
|-----------|-------|
| SoC | Snapdragon 845 (SDM845), 4x Kryo 385 Gold @ 2.8GHz + 4x Kryo 385 Silver @ 1.76GHz |
| RAM | 6 GB |
| Storage | UFS ~128GB |
| OS (current) | LineageOS 21.0 (Android 14, build lineage_dipper-userdebug 14 UQ1A.240205.004) |
| Kernel | 4.9.337-perf-g93c252af538f (Clang 17.0.2, March 2024); MODVERSIONS=y |
| WiFi | HARDWARE-BROKEN. Interface wlan0 never appears. Only recovery: USB Ethernet adapter (drivers built-in). |
| Screen | Working |
| Bootloader | Unlocked |
| Root | Magisk (su at /debug_ramdisk/su; adb shell gives root directly) |
| Bluetooth | 5.0 with A2DP + aptX HD |
| Sensors | All detected |
| Battery | 99%, USB powered (when connected to Mac) |

## Kernel Config (USB Network Drivers Built In)

Both RTL8152 and AX88179 drivers are compiled statically (y, not m):

```
CONFIG_USB_RTL8152=y      # Covers BOTH RTL8152 (100Mbps) AND RTL8153 (1000Mbps)
CONFIG_USB_NET_AX8817X=y
CONFIG_USB_NET_AX88179_178A=y
CONFIG_USB_NET_CDCETHER=y
```

USB WiFi drivers (rtl8xxxu, mt7601u, etc.) are absent — USB WiFi adapters will NOT work.

## USB Gadget

Single USB-C port, dwc3 controller. Either peripheral mode (ADB/MTP) or host mode (hub/Ethernet), never both.

## ROM Upgrade Path

The Mi8 can go from LineageOS 21.0 → 22.2 (Android 15) directly via `adb reboot sideload`:

```bash
adb reboot sideload      # boots recovery directly into sideload mode
adb wait-for-device
adb sideload lineage-22.2-*.zip
```

Firmware requirement: Already on LineageOS 21.0 means firmware meets the 22.2 requirement (upgrading from 19.1+ is sufficient per LineageOS wiki).

For clean flash from scratch (stock MIUI → LineageOS): Flash firmware first via fastboot (see firmware-update section in main skill), then flash recovery, then sideload ROM.

## Installed Apps (bare setup for Termux)

- Termux (com.termux) - installed and working
- Magisk (com.topjohnwu.magisk)
- No GApps, no Google services

Termux: Python 3.13 + pip installed, hermes-venv present. Used as headless compute node.

## Cellular

- Mobile data works via rmnet_data interfaces
- Not metered (confirm with user before large downloads)

## ADB Transport

- Serial: a6520fa3
- USB ADB only (no TCP ADB configured)
- ADB shell gives root directly (Magisk + userdebug build)
- TCP ADB over Ethernet configured on port 5555
- Wired ADB maintenance works via USB-C Ethernet adapter; device IP may change, confirm with user before connecting
