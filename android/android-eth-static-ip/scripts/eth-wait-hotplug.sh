#!/system/bin/sh
# eth-wait-hotplug.sh
# Wait for USB ethernet interface to appear (hotplug), then apply static IP.
# Deploy before unplugging USB ADB so the device self-configures when
# the ethernet adapter is plugged in.
#
# Deployment:
#   adb push eth-wait-hotplug.sh /data/local/tmp/
#   adb shell 'su 0 -c "chmod +x /data/local/tmp/eth-wait-hotplug.sh"'
#   adb shell 'su 0 -c "sh /data/local/tmp/eth-wait-hotplug.sh &"'
#   # Now unplug USB, plug ethernet — script sets IP automatically

# --- CONFIGURABLE ---
TARGET_IP="192.168.1.26"
NETMASK="255.255.255.0"
GATEWAY="192.168.1.1"
DNS1="223.5.5.5"
DNS2="8.8.8.8"
# --------------------

while true; do
    IFACE=$(ls /sys/class/net/ | grep -E "^eth|^en" | head -n 1)
    [ -n "$IFACE" ] && break
    sleep 2
done

ifconfig "$IFACE" "$TARGET_IP" netmask "$NETMASK" up
ip route replace default via "$GATEWAY" dev "$IFACE"
mkdir -p /data/local/tmp/eth-setup
echo "nameserver $DNS1" > /data/local/tmp/eth-setup/resolv.conf
echo "nameserver $DNS2" >> /data/local/tmp/eth-setup/resolv.conf

logger -t eth-wait "=== ETH READY: $IFACE = $TARGET_IP ==="
echo "=== ETH READY: $IFACE = $TARGET_IP ==="
