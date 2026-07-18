#!/usr/bin/env bash
# flash-n1.sh – automate flashing of N1 via TFTP

set -euo pipefail

# ---- CONFIG ----
TFTP_ROOT="/usr/local/var/tftp"
IMG_NAME="openwrt_factory.ubi"   # <-- replace with your factory image filename
# ----------------

echo "=== Starting TFTP server (tftpd-hpa) ==="
# Ensure the image exists
if [[ ! -f "${TFTP_ROOT}/${IMG_NAME}" ]]; then
  echo "Error: Image ${IMG_NAME} not found in ${TFTP_ROOT}"
  exit 1
fi

# Start tftpd-hpa (macOS brew service)
echo "Starting tftpd-hpa..."
brew services start tftpd-hpa > /dev/null 2>&1 || true
sleep 1

# Put image into TFTP root
echo "Copying ${IMG_NAME} to ${TFTP_ROOT}"
cp "${IMG_NAME}" "${TFTP_ROOT}/${IMG_NAME}"

# Prompt user to enter TFTP recovery mode on N1
echo "Prepare the N1: power off, hold RESET, then power on while holding RESET for ~3 seconds, release."
read -p "Press ENTER when the N1 LED pattern indicates TFTP mode..."

# The N1 will auto‑download; no further action needed.
echo "Flashing should begin automatically. When the device reboots, verify at http://192.168.1.1"