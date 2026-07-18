# macOS TCP Keepalive Parameters

## View Current Values

sysctl net.inet.tcp.keepidle net.inet.tcp.keepintvl net.inet.tcp.keepinit

## Parameters

net.inet.tcp.keepidle
  Time (ms) before first keepalive probe when connection is idle.
  Default: 7200000 (2 hours). Production: 30000 (30s).

net.inet.tcp.keepintvl
  Time (ms) between keepalive probes.
  Default: 75000 (75s). Production: 10000 (10s).

net.inet.tcp.keepinit
  Time (ms) before dropping connection that doesn't ACK.
  Default: 75000 (75s). Production: 10000 (10s).

## Set Persistently (reboot-safe)

Write to /etc/sysctl.conf:
  net.inet.tcp.keepidle=30000
  net.inet.tcp.keepintvl=10000
  net.inet.tcp.keepinit=10000

Apply immediately:
  sudo sysctl -w net.inet.tcp.keepidle=30000
  sudo sysctl -w net.inet.tcp.keepintvl=10000
  sudo sysctl -w net.inet.tcp.keepinit=10000

## Without Sudo (osascript)

osascript -e 'do shell script "sysctl -w net.inet.tcp.keepidle=30000 net.inet.tcp.keepintvl=10000 net.inet.tcp.keepinit=10000" with administrator privileges'

For /etc/sysctl.conf:
osascript -e 'do shell script "echo net.inet.tcp.keepidle=30000 > /etc/sysctl.conf && echo net.inet.tcp.keepintvl=10000 >> /etc/sysctl.conf && echo net.inet.tcp.keepinit=10000 >> /etc/sysctl.conf" with administrator privileges'

## Effect

With keepidle=30s + keepintvl=10s x 3 probes = dead connection detected in ~60 seconds.
Default: detected in 2 hours + 75s x 8 = ~10 minutes timeout after that.

## Linux Equivalent

net.ipv4.tcp_keepalive_time (instead of keepidle)
net.ipv4.tcp_keepalive_intvl (instead of keepintvl)
net.ipv4.tcp_keepalive_probes (count of probes, not a timeout)
