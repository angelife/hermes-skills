#!/system/bin/sh
# ethernet-watch-staticip.sh
# Waits for a USB Ethernet interface to appear, assigns a static IP.
# Designed for phones with dead screens where DHCP IP is invisible.
# Run this BEFORE connecting the OTG+Ethernet adapter.
#
# Usage: adb push ethernet-watch-staticip.sh /data/local/tmp/
#        adb shell su -c 'sh /data/local/tmp/ethernet-watch-staticip.sh 192.168.1.250 24 192.168.1.1 &'
#
# Args: [STATIC_IP] [NETMASK] [GATEWAY]
#   Defaults: 192.168.1.250, 24, 192.168.1.1

STATIC_IP="${1:-192.168.1.250}"
NETMASK="${2:-24}"
GATEWAY="${3:-192.168.1.1}"
LOG="/data/local/tmp/ethernet-watch.log"

# Interfaces to skip (system/radio interfaces)
KNOWN_IFACES="lo bond0 dummy0 ip_vti0 ip6_vti0 sit0 ip6tnl0 rmnet_ipa0"

# Persist across shell exit via nohup-style
trap '' HUP

echo "[$(date)] ethernet-watch started: target=$STATIC_IP/$NETMASK gw=$GATEWAY" >> "$LOG"

while true; do
    for iface in $(ls /sys/class/net/ 2>/dev/null); do
        # Skip known system interfaces
        echo "$KNOWN_IFACES" | grep -q "$iface" && continue
        # Skip wlan, rmnet, p2p
        echo "$iface" | grep -qE "^(wlan|rmnet|p2p)" && continue
        [ "$iface" = "lo" ] && continue

        # Must have a real MAC address
        mac=$(cat /sys/class/net/$iface/address 2>/dev/null)
        [ -z "$mac" ] && continue
        [ "$mac" = "00:00:00:00:00:00" ] && continue

        # Skip if already has an IP
        has_ip=$(ip addr show "$iface" 2>/dev/null | grep "inet " | head -1)
        [ -n "$has_ip" ] && continue

        # This is a new, unconfigured interface — assign our static IP
        echo "[$(date)] Found new interface: $iface (mac=$mac)" >> "$LOG"
        ip addr add "$STATIC_IP/$NETMASK" dev "$iface" 2>/dev/null
        ip link set "$iface" up 2>/dev/null
        sleep 1

        if ip addr show "$iface" | grep -q "$STATIC_IP"; then
            echo "[$(date)] IP $STATIC_IP assigned to $iface SUCCESS" >> "$LOG"
            # Add default route (may fail if gateway is not directly reachable)
            ip route add default via "$GATEWAY" dev "$iface" 2>/dev/null || true
            echo "[$(date)] ethernet-watch: done — exiting" >> "$LOG"
            exit 0
        else
            echo "[$(date)] Failed to assign IP to $iface" >> "$LOG"
        fi
    done
    sleep 2
done
