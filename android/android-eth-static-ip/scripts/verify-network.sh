#!/system/bin/sh
# Quick Mi8 network verification script
echo "=== interfaces ==="
ls /sys/class/net/ 2>/dev/null || echo no-sysfs
echo
echo "=== ip addr ==="
ip -4 addr show 2>/dev/null | grep -E "^[0-9]|inet" || true
echo
echo "=== ip route ==="
ip route show 2>/dev/null || true
echo
echo "=== operstate ==="
for f in /sys/class/net/eth*/operstate /sys/class/net/enp*/operstate; do
  [ -f "$f" ] && echo "$f: $(cat "$f")"
done
echo
echo "=== default gateway reachable ==="
ping -c1 -W2 192.168.1.1 2>&1 | tail -2 || echo gateway-fail
echo
echo "=== DNS ==="
cat /data/local/tmp/eth-setup/resolv.conf 2>/dev/null || echo missing
