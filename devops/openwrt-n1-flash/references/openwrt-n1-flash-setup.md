# OpenWrt N1 Flash – Reference Details

## Host network setup
```bash
# Enable alias on en0
sudo ifconfig en0 alias 192.168.0.66 netmask 0xffffff00
```

> **Note**: macOS will prompt for the user password; enter it when asked.

## N1 TFTP recovery mode
- Power off the N1.
- **Hold Volume‑Down**.
- While holding, plug in power.
- Keep holding ~3 seconds, then release.
- The board should appear as `192.168.0.66` on the network.

## TFTP server launch
```bash
sudo tftp-now serve -d /tmp
```
- Serves the contents of `/tmp` on UDP port 69.
- If the daemon reports “permission denied”, ensure you entered the password correctly.

## Verification
```bash
shasum -a 256 /tmp/openwrt_factory.bin
# Expected: a14e5c08d07d33e70cd1ddc482472e889884f5d633ebcb58240c69f9f410aebd
```

## Pitfalls observed
- Using `ifconfig en0 192.168.0.66` without `alias` fails with “permission denied”.
- Incorrect button combo (e.g., “Volume‑Up”) does not enter TFTP mode.
- Wrong image file (sysupgrade instead of factory) results in bricking.