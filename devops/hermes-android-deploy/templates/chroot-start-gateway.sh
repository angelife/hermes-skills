#!/bin/sh
# chroot-start-gateway.sh — Correct startup script template for Hermes gateway in Android chroot
# Copy into chroot /tmp/ and run via:
#   adb shell 'su 0 -c "cp /data/local/tmp/start_gw.sh /data/local/tmp/chroot/debian/tmp/ \
#     && nohup chroot /data/local/tmp/chroot/debian /bin/sh /tmp/start_gw.sh \
#     > /data/local/tmp/chroot/debian/root/.hermes/logs/gateway.log 2>&1 & echo OK"'

# CRITICAL: set -a ensures .env variables are exported to child processes
# Without this, AGNES_API_KEY and other env vars stay local to this shell
set -a
. /root/.hermes/.env
set +a

export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/root/.hermes/hermes-agent/venv/bin
export PYTHONPATH=/root/.hermes/hermes-agent
export HERMES_HOME=/root/.hermes
# ADB reverse pattern: when the phone has no WiFi but USB ADB, set up reverse tunnels:
#   adb reverse tcp:10808 tcp:10808   (proxy via Mac xray)
#   adb reverse tcp:3000  tcp:3000    (NewAPI via Mac New API)
#   adb reverse tcp:8888  tcp:8888    (Hindsight via Mac hindsight)
# Then all service addresses become 127.0.0.1 and no external IP is needed.
# For LAN-tethered setups (phone on same subnet as Mac), replace with:
#   export HTTPS_PROXY=http://192.168.1.8:10808
export HTTPS_PROXY=http://127.0.0.1:10808
export HTTP_PROXY=http://127.0.0.1:10808
export ALL_PROXY=http://127.0.0.1:10808
# Local services (NewAPI, Hindsight) must never go through proxy
export NO_PROXY=127.0.0.1,localhost

# Clean stale locks from previous run
rm -f /root/.hermes/gateway.lock /root/.hermes/hermes.pid

# IMPORTANT: --replace ensures only one instance runs.
# Without --replace, consecutive starts create competing gateway processes.
# ⚠️ nohup is NOT available in minimal Debian chroots (common on Mi6/Mi8/LineageOS).
# Use plain background with stdin redirect instead — same effect, no nohup needed.
cd /root/.hermes
hermes gateway run --replace >> /root/.hermes/logs/gateway.log 2>&1 < /dev/null &
echo "PID=$!"
