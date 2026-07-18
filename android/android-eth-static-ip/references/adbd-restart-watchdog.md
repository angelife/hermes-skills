# adbd TCP 看门狗 — 解决单 USB-C 口设备 adbd 重启后端口空挂

## 问题现象

- `nc -zv 192.168.1.26 5555` 显示端口开放
- `adb connect` 报 "No route to host" 或连接后 recv 超时
- Python raw socket 连上后 recv 无响应（无 ADB CNXN 握手）

## 根因

```
dmesg:
[269621.858684] init: Service 'adbd' (pid 22683) exited with status 0
[269621.860489] init: starting service 'adbd'...
```

单 USB-C 口设备（如 Mi8）插着 USB 以太网适配器时，USB 状态变更（FUNCTIONFS_ENABLE/DISABLE 事件）会触发 Android init 重启 adbd。旧 adbd 退出后：
1. TCP 端口 5555 被内核保留（表现为端口开放）
2. 但旧进程已死，新进程刚开始启动
3. 在这个切换窗口期内，TCP 连接能建立但收不到 CNXN 握手

`logcat -b main -s adbd` 可以看到 `already offline` 消息链。

## 稳定方案

### 1. adb-tcp.sh v2（带启动健康检查）

```sh
#!/system/bin/sh
# Enable TCP ADB on boot for wired remote maintenance
setprop service.adb.tcp.port 5555
stop adbd 2>/dev/null || true
sleep 1
start adbd

# 等待 adbd TCP 真正就绪（最长等 30 秒）
for i in $(seq 1 30); do
    sleep 1
    PID=$(getprop init.svc_debug_pid.adbd 2>/dev/null)
    if [ -n "$PID" ] && [ "$PID" != "stopped" ]; then
        if timeout 2 nc -z 127.0.0.1 5555 2>/dev/null; then
            break
        fi
    fi
done
```

### 2. 后台看门狗（每 2 分钟检测）

```sh
#!/system/bin/sh
# ADB TCP Watchdog
LOG=/data/local/tmp/adb-watchdog.log
sleep 60  # 等系统稳定
while true; do
    sleep 120
    if ! timeout 3 nc -z 127.0.0.1 5555 2>/dev/null; then
        echo "[$(date)] ADB watchdog: restarting adbd" >> $LOG
        setprop service.adb.tcp.port 5555
        stop adbd 2>/dev/null || true
        sleep 1
        start adbd
        sleep 3
    fi
done
```

### 3. 诊断命令

```bash
# 检查 adbd 进程状态
adb shell "su -c 'getprop | grep adb'"
adb shell "su -c 'ps -ef | grep adbd | grep -v grep'"

# 看 adbd 重启历史
adb shell "su -c 'dmesg | grep adbd | tail -10'"

# 看 ADB 协议是否响应（raw socket CNXN 检测）
timeout 5 python3 -c "
import socket, struct, time
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.settimeout(4)
s.connect(('192.168.1.26', 5555))
time.sleep(0.5)
try:
    d = s.recv(4096)
    print('OK' if d[:4] == b'CNXN' else 'UNEXPECTED: ' + str(d[:8]))
except socket.timeout:
    print('DEAD - no CNXN response')
s.close()
"
```

## 部署方式

```bash
# 推送看门狗
adb push /tmp/adb-watchdog-service.sh /data/local/tmp/
adb shell "su -c 'chmod 755 /data/local/tmp/adb-watchdog-service.sh'"

# 在 adb-tcp.sh 末尾追加启动
adb shell "su -c \"echo 'nohup /data/local/tmp/adb-watchdog-service.sh > /data/local/tmp/adb-watchdog.log 2>&1 &' >> /data/local/tmp/adb-tcp-service.sh\""

# 立即启动
adb shell "su -c 'nohup /data/local/tmp/adb-watchdog-service.sh &'"

# 验证
adb shell "su -c 'ps -ef | grep adb-watchdog | grep -v grep'"
```
