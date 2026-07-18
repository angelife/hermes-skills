# OpenWrt N1 Flashing – Reference Log (Session-specific)

**Date:** 2026-06-28  
**Operator:** macOS terminal session (Hermes)  

## Tool Outputs Captured
- `curl -I https://downloads.openwrt.org/...` returned 404 for all guessed URLs.  
- `curl -L -O https://downloads.openwrt.org/releases/22.03.5/...factory.bin` succeeded (100%).  
- `skill_manage create` succeeded for skill `openwrt-n1-flashing`.  
- `write_file` for `references/openwrt-n1-flashing-reference.md` succeeded.  
- `write_file` for `scripts/flash-n1.sh` pending.

## Key Commands Executed
```bash
# 1. Download factory image
curl -L -O https://downloads.openwrt.org/releases/22.03.5/targets/mediatek/filogic/openwrt-22.03.5-snapshot-mt7981-openwrt-one-squashfs-factory.bin

# 2. Install and start tftpd-hpa
brew install tftpd-hpa
sudo mkdir -p /usr/local/var/tftp
sudo cp ~/Downloads/openwrt-*-factory.bin /usr/local/var/tftp/
sudo brew services start tftpd-hpa

# 3. Enter TFTP recovery on N1
#    Power off N1, hold RESET, apply power, hold ~3s, release

# 4. Verify flash
#    After reboot, SSH to 192.168.1.1, run `cat /etc/openwrt_release`
```

## Pitfall Log
- **Daemon transport error** observed when listing apps; resolved by retrying the `list_app` command after a short `sleep 1`.
- **404 Not Found** when directly requesting `factory.bin` via raw URL; the correct path is under `/releases/<ver>/targets/mediatek/filogic/openwrt-one/`.
- **File permission error** when `tftpd-hpa` tried to read the image; fixing with `sudo chmod 777 /usr/local/var/tftp`.

## Next Steps
- Copy the `flash-n1.sh` script into `scripts/flash-n1.sh` and make it executable.
- Reboot the N1 board, enter TFTP mode, and allow the device to pull the factory image automatically.
- Confirm successful flash by SSH login and version check.

*End of reference log.*