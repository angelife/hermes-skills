# gnirehtet 反向 USB 共享网络

## 适用场景
Android 手机 WiFi 硬件损坏/不可用，移动数据不可用，需要通过网络下载包（apt/pip/curl）

## 原理
通过 ADB reverse tunnel 在手机和电脑之间建立 VPN 隧道，手机走电脑的网络

## 需求
- 手机 USB 连接电脑
- ADB 调试已启用
- 不需要 root / 不需要 RNDIS / 不需要 WiFi

## ⚠️ Pitfall: Mac 上 Java 版 relay 静默失败

**现象**：`java -jar gnirehtet.jar relay` 看起来启动了（无报错），但实际手机端 `ping 8.8.8.8` 无回复。

**根因**：Mac 未安装 Java Runtime（JRE）。gnirehtet Java 版依赖 Java 8+，无 JRE 时 relay 进程立即退出但不报错。

**解决方案**：优先使用 Rust 版（无需 Java）：
```bash
brew install gnirehtet
gnirehtet run
```

如果必须用 Java 版，先确认：
```bash
java -version 2>/dev/null || echo "NO JAVA - install with: brew install java"
```

## ⚠️ Pitfall: Termux apt 仍然 DNS 不通（即使手机能上网）

**现象**：手机上浏览器能上网、`ping 8.8.8.8` 能通，但在 Termux 里 `apt-get update` 报 DNS 错误。

**根因**：Termux 的用户空间（不同 UID）不继承系统 DNS 配置，自己的 `/usr/etc/resolv.conf` 没有正确 DNS。

**解决方案**：
```bash
adb shell "su -c 'echo \"nameserver 8.8.8.8\" > /data/data/com.termux/files/usr/etc/resolv.conf'"
```

## 安装步骤

### Rust 版（推荐，无需 Java）
```bash
brew install gnirehtet

# 安装 APK（brew 装好后 APK 在 Cellar 里）
ls /usr/local/Cellar/gnirehtet/*/gnirehtet.apk 2>/dev/null
adb install -r $(ls /usr/local/Cellar/gnirehtet/*/gnirehtet.apk)
```

### Java 版（跨平台备选）
```bash
java -version || brew install java
cd /tmp
curl -LO "https://github.com/Genymobile/gnirehtet/releases/download/v2.5.1/gnirehtet-java-v2.5.1.zip"
unzip gnirehtet-java-v2.5.1.zip
cd gnirehtet-java
java -jar gnirehtet.jar run
```

## 启动流程

### 一键启动
```bash
gnirehtet run
```

### 分步启动
```bash
# 1. 启动 relay（后台）
gnirehtet relay &

# 2. 建立 reverse tunnel
adb reverse localabstract:gnirehtet tcp:31416

# 3. 启动客户端
adb shell am start -a com.genymobile.gnirehtet.START -n com.genymobile.gnirehtet/.GnirehtetActivity

# 4. 手机上确认 VPN 请求
# 5. 验证
adb shell ping -c 2 8.8.8.8
```

## 停止
```bash
adb shell am start -a com.genymobile.gnirehtet.STOP -n com.genymobile.gnirehtet/.GnirehtetActivity
# Ctrl+C 停止 relay（或 kill -9 <PID>）
```

## 故障排除

### VPN 弹框未出现
- 检查 adb 连接：`adb devices`
- 检查 reverse tunnel：`adb reverse --list`
- 重新安装 APK：`adb install -r gnirehtet.apk`

### Termux apt 仍报网络错误
- 检查 tun0 接口：`adb shell "su -c 'ip addr show tun0'"`
- 路由表应有默认路由指向 tun0
- 手动写 DNS 到 Termux resolv.conf（见上方 pitfall）

## 工作流程偏好
遇到 Android 手机无网络时：
1. **先 web_search** 搜关键词 `termux 无网络`、`Android reverse tether ADB`、`gnirehtet` 等
2. 用已知方案验证，而不是自己一步步试错
3. 不要在已有成熟工具的场景下自己摸索 socket/tunnel 方案