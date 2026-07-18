#!/bin/sh
# deliver-to-kindle.sh
# Transfer files to Kindle via USBNet (real interface only)
# Usage: ./deliver-to-kindle.sh <file1> [file2] ...
#
# Prerequisites: real USBNet (not Docker utun false positive).
# See kindle-troubleshooting: USBNet/SSH authenticity checks.
KINDLE_IP="192.168.15.244"
SSH_KEY="${HOME}/.ssh/id_ed25519_kindle"
KINDLE_USER="root"

# 1) ICMP
if ! ping -c 1 -W 1 "$KINDLE_IP" > /dev/null 2>&1; then
    echo "Can't reach $KINDLE_IP."
    echo "Plug Kindle USB + enable USBNet, or use Calibre /Volumes/Kindle."
    exit 1
fi

# 2) Reject Docker/VPN utun false positives (2026-07-17)
ROUTE_IF=$(route get "$KINDLE_IP" 2>/dev/null | awk '/interface:/{print $2}')
case "$ROUTE_IF" in
  utun*|tun*)
    echo "False USBNet: route to $KINDLE_IP goes via $ROUTE_IF (Docker/VPN)."
    echo "Need Mac interface with 192.168.15.1 and USB = Lab126/Kindle."
    echo "Fallback: mount /Volumes/Kindle and cp, or Calibre wireless / Web Bridge :8081."
    exit 1
    ;;
esac
if ! ifconfig 2>/dev/null | grep -q '192\.168\.15\.'; then
    echo "No Mac-side 192.168.15.x address — USBNet interface not up."
    exit 1
fi

# 3) Real SSH (auth + command; not just TCP open)
if ! ssh -o BatchMode=yes -o StrictHostKeyChecking=no -o ConnectTimeout=5 \
    -i "$SSH_KEY" "$KINDLE_USER@$KINDLE_IP" "ls /mnt/us/documents" > /dev/null 2>&1; then
    echo "SSH failed (or kex closed with no banner = fake host)."
    echo "  ssh-keygen -t ed25519 -f ~/.ssh/id_ed25519_kindle"
    echo "  # after REAL USBNet: install pubkey to authorized_keys"
    echo "Alternative: Calibre wireless, or cp via /Volumes/Kindle"
    exit 1
fi

for f in "$@"; do
    if [ -f "$f" ]; then
        echo "delivering $f..."
        scp -o StrictHostKeyChecking=no -i "$SSH_KEY" "$f" "$KINDLE_USER@$KINDLE_IP:documents/"
    else
        echo "Warning: not a file: $f"
    fi
done
