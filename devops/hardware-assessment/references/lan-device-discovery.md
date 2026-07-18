# LAN 设备发现

快速扫描局域网找出所有在线设备的参考。

## 常用方式

### 1. ARP 表（不主动扫描，仅看缓存）
```bash
arp -a
```

### 2. ping 扫描（逐个探测）
```bash
# 顺序扫描（推荐，兼容性好）
for i in $(seq 1 254); do
  ping -c1 -W1 192.168.0.$i 2>/dev/null | grep -q "from" && echo "192.168.0.$i alive"
done
```

### 3. nmap（如已安装）
```bash
nmap -sn 192.168.0.0/24
```

## 已知设备的 MAC 特征

| MAC 前缀 | 厂商 | 可能设备 |
|----------|------|----------|
| 34:96:72 | Unknown | OpenWrt 路由器 |
| 00:08:0a | Unknown | Mi8 USB 网卡 |

## 服务探测

发现 IP 后判断是什么设备：
```bash
# 看端口开放
nc -zv -G2 <IP> 22     # SSH
nc -zv -G2 <IP> 80     # HTTP
nc -zv -G2 <IP> 443    # HTTPS
nc -zv -G2 <IP> 8080   # 备用 HTTP
nc -zv -G2 <IP> 9090   # Kodi JSON-RPC
nc -zv -G2 <IP> 445    # SMB
curl -s --connect-timeout 5 http://<IP>/ | head -5  # 看 web 页面
```