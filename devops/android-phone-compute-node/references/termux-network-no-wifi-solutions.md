# 手机无 WiFi 时 Termux 网络连接的方案与失败记录

手机: Mi8(dipper), LOS 22.2, WiFi 硬件损坏, 无 SIM 卡
Mac: Apple Silicon, macOS 15.x
连接: USB ADB (已 root, Magisk 30.7)

## 目标

让 Termux 能 apt-get / pip install 来装 Hermes Agent 或其他包。

## 方案 A (失败): gnirehtet 反向 tethering

gnirehtet 通过 ADB reverse 在手机和 Mac 之间建立 VPN 隧道。

**症状**: 手机 tun0 接口建立(10.0.0.2/32), 但 relay 进程 segfault。

relay 日志:
TcpConnection: 10.0.0.2:42202 -> 114.114.114.114:853 Open
Connection #0 connected
--- 然后 segfault ---
exit code 139

**原因**: gnirehtet 的 Rust 版 relay 进程在 macOS 上不稳定, 反复 segfault (exit code 139)。这是已知问题(GitHub issue #82)。Java 版需要 JRE 但 Mac 没装。

**已排除**, 不要在这条路上浪费时间。

## 方案 B (部分成功但 Termux 内失败): mitmproxy + ADB reverse

在 Mac 上用 mitmproxy（比手写 Python HTTP proxy 更稳定，`brew install mitmproxy`）开 HTTP CONNECT 代理。

```bash
# Mac 侧
mitmdump --listen-port 1080 --mode regular &

# 测试（需用 mitmproxy 自签 CA 证书）
curl -x http://127.0.0.1:1080 --cacert ~/.mitmproxy/mitmproxy-ca-cert.pem -s https://ifconfig.me

# ADB 映射
adb reverse tcp:1080 tcp:1080

# 手机系统 shell 验证
adb shell "curl -x http://127.0.0.1:1080 -s https://ifconfig.me"
```

### 代理实现

```python
from http.server import HTTPServer, BaseHTTPRequestHandler
import urllib.request, socket, select

class Proxy(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            resp = urllib.request.urlopen(self.path, timeout=15)
            self.send_response(resp.status)
            for k,v in resp.headers.items(): self.send_header(k,v)
            self.end_headers()
            self.wfile.write(resp.read())
        except Exception as e:
            self.send_error(502, str(e))

    def do_CONNECT(self):
        host, port = self.path.split(':')
        port = int(port)
        try:
            remote = socket.create_connection((host, port), timeout=15)
            self.send_response(200)
            self.end_headers()
            while True:
                r,_,_ = select.select([self.connection, remote], [], [])
                if self.connection in r:
                    data = self.connection.recv(4096)
                    if not data: break
                    remote.send(data)
                if remote in r:
                    data = remote.recv(4096)
                    if not data: break
                    self.connection.send(data)
            remote.close()
        except: self.send_error(502)

HTTPServer(('127.0.0.1', 1080), Proxy).serve_forever()
```

### 启动步骤

Mac 侧开代理:
  python3 /tmp/httpproxy.py &
  curl -x http://127.0.0.1:1080 -s https://ifconfig.me

ADB 映射:
  adb reverse tcp:1080 tcp:1080

手机系统验证:
  adb shell "curl -x http://127.0.0.1:1080 -s https://ifconfig.me"

### Termux 内失败原因

apt-get update -o Acquire::http::Proxy=http://127.0.0.1:1080
→ Could not create a socket for 127.0.0.1 - socket (13: Permission denied)

**根因**: Android 15 的 SELinux/seccomp 沙箱阻止了 Termux 应用（非 root 进程）创建网络 socket。adb shell su -c curl（系统 root shell）可以上网，但 run-as com.termux 进程不行。和 DNS 无关。

**结论**: 此路不通。必须通过物理网络连接（有线网卡/SIM 数据/另一台手机 tethering）让手机系统先上网，Termux 才能自动继承网络。

## 方案 C: 让手机系统本身先上网

Termux 依赖于系统网络的底层 route/dns。只有系统本身能上网, Termux 才能上网。

### 可行的上网路径

**1. USB 有线网卡(推荐)**
硬件: AX88772D (或其他 ASIX/RTL815x 网卡) + OTG 转接头
Mi8 内核已编译 asix/ax88179_178a 驱动, 即插即用
不需要 root, 不需要配置
连上网线后 ip addr show 会看到 eth0/usb0 接口自动获取 DHCP

**2. 另一台手机 USB tethering**
设备 B 开 USB tethering, 用 USB 线连 Mi8
Mi8 获取 rndis0 IP, 走设备 B 的数据网络

**3. 插 SIM 卡开移动数据**
svc data enable 开启移动数据(需要运营商数据套餐)

## 离线装包(不需要网络)

如果手机始终无法上网, 可以在 Mac 上下载 Termux 的 .deb 包推过去安装:

在 Mac 上解析包索引:
  curl -sL "https://mirrors.tuna.tsinghua.edu.cn/termux/apt/termux-main/dists/stable/main/binary-aarch64/Packages.gz" -o /tmp/p.gz
  gunzip -k /tmp/p.gz

找需要的包:
  for pkg in python python-pip git; do
    fn=$(grep -A 12 "^Package: $pkg$" /tmp/p | grep "^Filename:" | awk '{print $2}')
    curl -sL "https://mirrors.tuna.tsinghua.edu.cn/termux/apt/termux-main/$fn" -o "/tmp/${pkg}.deb"
  done

推送到 Termux:
  adb push /tmp/python.deb /data/local/tmp/
  adb shell su -c "cp /data/local/tmp/python.deb /data/data/com.termux/files/usr/tmp/"
  adb shell 'su 10188 /data/data/com.termux/files/usr/bin/bash -c \
    "dpkg -i /data/data/com.termux/files/usr/tmp/python.deb"'

详见 android-phone-compute-node 的 references/offline-termux-bootstrap.md。