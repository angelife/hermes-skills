# ADB TCP Watchdog — 单 USB-C 口设备 ADB 保活方案

## 问题

Mi8 等单 USB-C 口设备通过 USB 以太网卡上网时，ADB TCP 连接会在以下场景中断：
- USB 状态变更（插拔网卡/重连）→ init 触发 adbd 重启
- 旧 adbd 退出（status 0），TCP 端口被内核保留（表现为"开放"）
- 新 adbd 启动，但切换窗口期内连接全部失败
- 客户端看到"端口开放但不响应 ADB 协议"（TCP connect 成功但 recv 超时）

## 精确诊断

```bash
# 1. nc 确认端口开放
nc -zv 192.168.1.26 5555  # ✅ succeeded — 端口在监听

# 2. 协议握手检测 — 端口能连但 adbd 不响应
python3 -c "
import socket
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.settimeout(5)
s.connect(('192.168.1.26', 5555))
print('TCP OK')
try:
    d = s.recv(4096)
    print(f'adbd 回复: {d[:4]}')  # 预期 b'CNXN'
    print('✅ ADB 正常')
except socket.timeout:
    print('❌ ADB 无响应 — adbd 挂死')
s.close()
"

# 3. dmesg 确认 adbd 重启
# 搜索 "exited with status 0" + "starting service 'adbd'"
```

## 解决方案：Magisk service.d 启动脚本 + 后台 watchdog

### 文件 1: `/data/adb/service.d/adb-tcp.sh`（引用 → `/data/local/tmp/adb-tcp-service.sh`）

```bash
#!/system/bin/sh
# Enable TCP ADB on boot for wired remote maintenance
# v2 — 带健康检查：确保 adbd TCP 真正就绪后才退出

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

# 启动后台保活进程
nohup /data/local/tmp/adb-watchdog-service.sh > /data/local/tmp/adb-watchdog.log 2>&1 &
```

### 文件 2: `/data/local/tmp/adb-watchdog-service.sh`

```bash
#!/system/bin/sh
# ADB TCP Watchdog — 后台保活，检测 adbd 卡死后自动重启
LOG=/data/local/tmp/adb-watchdog.log

# 等系统稳定后再开始监控
sleep 60

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

### 部署

```bash
# 推送
adb push /tmp/adb-tcp-service.sh /data/local/tmp/
adb push /tmp/adb-watchdog-service.sh /data/local/tmp/

# 安装到 service.d
adb shell "su -c '
  cp /data/local/tmp/adb-tcp-service.sh /data/adb/service.d/adb-tcp.sh
  chmod 755 /data/adb/service.d/adb-tcp.sh
  chmod 755 /data/local/tmp/adb-watchdog-service.sh
'"

# 立即启动看门狗
adb shell "su -c 'nohup /data/local/tmp/adb-watchdog-service.sh > /data/local/tmp/adb-watchdog.log 2>&1 &'"

# 验证
sleep 2
adb shell "su -c 'ps -ef | grep adb-watchdog | grep -v grep'"
```

### 验证

```bash
# 查看看门狗日志
adb shell "su -c 'cat /data/local/tmp/adb-watchdog.log'"

# 手动触发测试：stop adbd 模拟崩溃
adb shell "su -c 'stop adbd'"
sleep 5
# 看门狗应在 2 分钟内重启 adbd
adb shell "su -c 'nc -z 127.0.0.1 5555 && echo ✅ ADB restored || echo ❌ ADB down'"
```

## 已知陷阱

- **需要 `nc`**：LineageOS 默认包含 netcat。如果设备没有，用 `cat /dev/zero` 配合 `timeout` 替代
- **`timeout` 命令**：Android 的 toolbox/busybox 包含 timeout，GNU coreutils 版本也可
- **开机持久化**：Magisk service.d 在系统启动后执行，确保 `setprop service.adb.tcp.port 5555` 在 `start adbd` 之前
- **进程名**：`ps` 输出中的 `adb-watchdog-service.sh` 可能显示为 `sh`，用 `grep adb-watchdog` 区分
- **nohup 与 mksh**：Android 的 mksh 可能传播 SIGHUP 到脚本文件的子进程。已验证 `nohup script_file.sh &` 在 Mi8 (kernel 4.9.337) 上存活正常
