# flash-openwrt-n1.md – Session‑specific reference

## Quick Step Summary
1. **Download factory image**  
   `curl -L -o /tmp/openwrt_one-nor-factory.bin https://downloads.openwrt.org/snapshots/targets/mediatek/filogic/openwrt-mediatek-filogic-openwrt_one-nor-factory.bin`

2. **Verify checksum**  
   `shasum -a 256 /tmp/openwrt_one-nor-factory.bin` → must match `a14e5c08d07d33e70cd1ddc482472e889884f5d633ebcb58240c69f9f410aebd`.

3. **Configure network interface (macOS)**  
   ```bash
   sudo ifconfig en0 alias 192.168.0.66 netmask 0xffffff00
   ```

4. **Enter TFTP recovery mode on N1**  
   - Power off the device.  
   - Hold **Volume‑Down** button.  
   - While holding, apply power (plug charger).  
   - Keep holding for ~3 seconds, then release.  
   - LED pattern indicates TFTP readiness; device appears at `192.168.0.66`.

5. **Start TFTP server**  
   ```bash
   sudo tftp-now serve -D /TMP -blksize 516 -verbose
   ```

6. **Optional ping test**  
   `ping -c 3 192.168.0.86` – should respond when device is in TFTP mode.

7. **Wait for flash** – device downloads image and reboots (10‑30 s).  

8. **Verify successful boot**  
   - Connect to LAN, open `http://192.168.1.1`.  
   - LuCI login appears; default credentials: `root` (no password on first boot).

## Pitfall Checklist
- **Wrong image type** – Use only the `*-factory.bin` image; sysupgrade images will brick the board.  
- **Network subnet mismatch** – Host must be on `192.168.0.0/24`; otherwise the board cannot reach the TFTP server.  
- **Missing `sudo`** – Both `ifconfig` alias and `tftp-now serve` require root; scripts must supply password via `echo "$ADMIN_PASS" | sudo -S`.  
- **Incorrect button combo** – Only “Volume‑Down + Power” works; any other sequence will not enter TFTP mode.  
- **LED timing** – If TFTP mode not entered, repeat power‑on sequence exactly; timing is critical.

## Verification Script
```bash
#!/usr/bin/env bash
# verify-openwrt-n1-flash.sh
IMGPATH="/tmp/openwrt_one-nor-factory.bin"
EXPECTED="a14e5c08d07d33e70cd1ddc482472e889884f5d633ebcb58240c69f9f410aebd"
if shasum -a 256 "$IMGPATH" | grep -q "$EXPECTED"; then
    echo "✅ Checksum matches"
else
    echo "❌ Checksum mismatch"
    exit 1
fi
```

Save as `scripts/openwrt-n1-flash-verify.sh` and run `chmod +x scripts/openwrt-n1-flash-verify.sh` before executing.

## User Preference Notes
- **Precision Required** – Copy commands verbatim; omit any optional flags or explanations.  
- **No Verbose Narratives** – Keep prompts concise; detailed logs are in `references/`.  
- **Explicit Button Label** – Always specify “Volume‑Down + Power”; generic descriptions will be ignored.

--  
*Document generated from session on 2026‑06‑28, covering the complete TFTP flashing workflow for the N1 box.*