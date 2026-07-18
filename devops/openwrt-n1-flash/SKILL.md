---
name: openwrt-n1-flash
title: OpenWrt N1 Box Flashing
description: Documented workflow for flashing OpenWrt onto the N1 box (mediatek/filogic target) using TFTP, including image download, verification, network setup, TFTP server launch, recovery‑mode instructions, and post‑flash verification.
category: hardware
tags: openwrt,n1,tftp,flashing
---

## Purpose
Procedure for flashing OpenWrt onto the N1 box (mediatek/filogic target) using TFTP.  
Covers image acquisition, checksum verification, network configuration, TFTP server launch, user recovery‑mode instructions, and post‑flash verification.

## Triggers
- Need to flash a fresh OpenWrt image onto an N1 device.  
- Working with devices that use the `mediatek/filogic` target and require bootloader unlocking.  
- Require a repeatable, documented workflow that avoids missing steps or pitfalls.

## Core Steps
1. **Identify target image** – locate the correct `openwrt_one-nor-factory.bin` for the N1 device on the OpenWrt snapshot server.  
2. **Download image** – save to `/tmp` and verify with `sha256sum`.  
3. **Configure network interface** – alias `en0` to `192.168.0.66` netmask `0xffffff00` (requires sudo).  
4. **Start TFTP server** – serve `/tmp` using `tftp-now serve -D /TMP -blksize 512 -verbose`.  
5. **User action** – hold Volume‑Down + Power for ~3 seconds to enter TFTP/recovery mode.  
6. **Optional ping test** – verify device responds at `192.168.0.86`.  
7. **Automatic flash** – device downloads and flashes the image, then reboots.  
8. **Post‑flash verification** – SSH into the device, confirm OpenWrt version, and check services.

## Pitfalls & Fixes
- **Wrong image** – Using a sysupgrade image instead of the factory image will brick the device.  
- **Network mismatch** – The host must be on the `192.168.0.0/24` subnet; otherwise the board will not reach the TFTP server.  
- **Insufficient privileges** – `sudo` is required for both `ifconfig` alias and `tftp-now serve`.  
- **Verbose output overwhelms users** – Summarize with concise prompts; keep detailed logs in `references/`.  
- **LED timing** – If the board does not enter TFTP mode, repeat the power‑on sequence precisely; timing is critical.  
- **Password prompt on sudo** – macOS `sudo` prompts for a password and aborts when not provided interactively. In scripts use `echo "$ADMIN_PASS" | sudo -S <command>` to supply it non‑interactively.

## Verification Checklist
- ✅ Image checksum matches official `sha256sums` entry.  
- ✅ Device enters TFTP mode (LED pattern, screen message).  
- ✅ Ping returns replies from `192.168.0.86`.  
- ✅ After reboot, device is reachable via SSH (`root`/`password` default).  
- ✅ LuCI UI loads, confirming successful flash.

## Tools & Dependencies
- `tftp-now` – lightweight TFTP server.  
- `sha256sum` – checksum verification.  
- `ping` – connectivity test.  
- `ifconfig` – network alias configuration (macOS).  

## Preference Notes (user‑specific)
- **Precision** – every command must be copied verbatim; any deviation (e.g., missing `sudo` or wrong button label) will prevent the board from flashing.  
- **No extra explanation** – the skill’s examples are deliberately terse; avoid verbose narratives.  
- **Explicit button combo** – “Volume‑Down + Power” is the only accepted method; alternate descriptions will be ignored.

## References
- OpenWrt download page: <https://downloads.openwrt.org/snapshots/targets/mediatek/filogic/>  
- Official `sha256sums` file for checksum verification.  
- Session notes: `references/flash-openwrt-n1.md`

## Skill Files
- `scripts/flash_openwrt_n1.sh` – ready‑to‑run script encapsulating the workflow.  
- `scripts/openwrt-n1-flash-verify.sh` – optional verification script (see `scripts/` directory).