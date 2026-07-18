#!/system/bin/sh
set -e
IFACE=$(ls /sys/class/net/ | grep -E '^eth|^en' | head -n 1)
[ -z "$IFACE" ] && exit 0
ifconfig "$IFACE" 192.168.1.26 netmask 255.255.255.0 up
ip route replace default via 192.168.1.1 dev "$IFACE"
mkdir -p /data/local/tmp/eth-setup
echo nameserver 223.5.5.5 > /data/local/tmp/eth-setup/resolv.conf
echo nameserver 8.8.8.8 >> /data/local/tmp/eth-setup/resolv.conf
