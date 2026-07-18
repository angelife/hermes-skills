# ADB TCP Watchdog 部署

## 场景

单 USB-C 口 Android 设备（如 Mi8）使用 USB 以太网卡联网时，USB 状态变更（插拔/重连）会触发 **adbd 重启**，导致：
- 旧 adbd 退出，TCP socket 被内核保留（`nc -zv` 显示端口开放）
- 新 adbd 启动但 socket 绑定需要时间
- 在此窗口期内 ADB 连接失败（TCP 能连但收不到 CNXN 握手）

## 解决方案

在 Magisk service.d 部署自启脚本 + 后台保活进程。

### 核心脚本：`/data/adb/service.d/adb-tcp.sh`

```bash
#!/system/bin/sh
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

# 启动后台看门狗
nohup /data/local/tmp/adb-watchdog-service.sh > /data/local/tmp/adb-watchdog.log 2>&1 &
```

### 后台看门狗：`/data/local/tmp/adb-watchdog-service.sh`

```bash
#!/system/bin/sh
# ADB TCP Watchdog — 每 2 分钟检测 adbd 是否响应
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

### 部署命令

```bash
# adb-tcp.sh 是 symlink 到 /data/local/tmp/adb-tcp-service.sh
# 更新目标文件：
adb push /tmp/adb-tcp-service.sh /data/local/tmp/
adb shell "su -c 'chmod 755 /data/local/tmp/adb-tcp-service.sh'"

# 推送看门狗
adb push /tmp/adb-watchdog-service.sh /data/local/tmp/
adb shell "su -c 'chmod 755 /data/local/tmp/adb-watchdog-service.sh'"

# 追加启动看门狗到 adb-tcp 脚本末尾
adb shell "su -c 'echo \"nohup /data/local/tmp/adb-watchdog-service.sh > /data/local/tmp/adb-watchdog.log 2>&1 &\" >> /data/local/tmp/adb-tcp-service.sh'"

# 立即启动看门狗（不用等重启）
adb shell "su -c 'nohup /data/local/tmp/adb-watchdog-service.sh > /data/local/tmp/adb-watchdog.log 2>&1 &'"

# 验证
adb shell "su -c 'ps -ef | grep adb-watchdog | grep -v grep'"
```

### 验证方法

```bash
# 检查看门狗进程
adb shell "su -c 'ps -ef | grep adb-watchdog | grep -v grep'"

# 检查日志
adb shell "su -c 'cat /data/local/tmp/adb-watchdog.log'"

# 手动测试 ADB 连接
nc -zv <ip> 5555
adb connect <ip>:5555
```

### 注意事项

- service.d 目录下的脚本是 symlink：`adb-tcp.sh -> /data/local/tmp/adb-tcp-service.sh`
- 备份原脚本后再修改：`cp /data/adb/service.d/adb-tcp.sh /data/adb/service.d/adb-tcp.sh.bak`
- 看门狗在 60 秒后开始首次检查，之后每 120 秒检查一次
- 日志路径：`/data/local/tmp/adb-watchdog.log`（可随时查看重启记录）
