#!/system/bin/sh
# Persistent TCP ADB over wired network.
# Place in /data/local/tmp/adb-tcp-service.sh and link to service.d.
setprop service.adb.tcp.port 5555
stop adbd 2>/dev/null || true
start adbd
