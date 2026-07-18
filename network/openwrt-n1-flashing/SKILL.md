---
name: openwrt-n1-flashing
title: openwrt-n1-flashing
category: network
description: Flash the N1 board via TFTP using OpenWrt factory image
---
# OpenWrt N1 Flashing (TFTP)

## Goal
Flash the MediaTek MT7981 “N1” board using TFTP recovery with an OpenWrt factory image.

## Prereqs
- macOS + USB‑to‑Ethernet adapter.
- Direct cable from Mac to N1 LAN port.
- OpenWrt factory image (e.g., `openwrt-mediatek-filogic-openwrt_one-factory.ubi`).
- `tftpd-hpa` installed (`brew install tftpd-hpa`).

## Steps
1. **Download factory image** – use https://firmware-selector.openwrt.org, select *OpenWrt One*, pick a stable version (e.g., 23.05.0), download the *factory* image.
2. **Install & start TFTP server**  
   ```bash
   sudo mkdir -p /usr/local/var/tftp
   sudo cp ~/Downloads/openwrt_factory.ubi /usr/local/var/tftp/
   sudo brew services start tftpd-hpa
   ```
3. **Enter TFTP recovery** – power off N1, hold RESET, apply power, keep holding ~3 s, release. N1 shows TFTP mode (LED pattern). It will request `192.168.0.66`.
4. **Flash** – the N1 automatically downloads the file served by the TFTP server and flashes it. No further action needed.
5. **Verify** – after reboot, connect to `192.168.1.1` (browser or `ssh root@192.168.1.1`) and confirm OpenWrt version.

## Pitfalls
- **Daemon transport error** – may occur if `tftpd-hpa` isn’t ready; retry or add a short `sleep 1`.
- **Wrong image type** – use the *factory* image, not a sysupgrade image.
- **Firewall block** – allow UDP/69 on macOS firewall.

## Script
`scripts/flash-n1.sh` – automates steps 2‑4.

**注意:** 此技能涵盖两个场景——刷机(新固件)和渗透(已知密码恢复)。斐讯N1(Amlogic S905D)与OpenWrt One(MTK MT7981)是不同设备，注意区分。

## References
- Firmware selector: https://firmware-selector.openwrt.org
- TFTP recovery guide: https://openwrt.org/docs/guide-user/installation/tftp
- **N1渗透参考:** `references/openwrt-n1-pentest-reference.md` — 比赛场景密码破解完整战报与攻击矩阵