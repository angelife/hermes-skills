# ADB 设备 "offline" 状态诊断

## 现象

`adb devices` 显示设备为 **offline**，而非 `device` 或 `unauthorized`。

```
192.168.1.26:5555      offline
```

## 与其它 ADB 连接失败模式的区分

| 状态 | `adb devices` 显示 | `nc -zv <ip> 5555` | ADB 协议握手 | 根因 |
|------|-------------------|---------------------|-------------|------|
| **offline** | `192.168.1.26:5555  offline` | ✅ 端口开放 | ADB CNXN 收到但 auth token 被拒 | RSA 密钥未授权 |
| **adbd 已退出（孤儿 socket）** | 设备不在列表或 `no route to host` | ✅ 端口开放 | ❌ Python raw socket recv 超时 | adbd 已死，socket 被内核保留 |
| **设备未连接** | 设备不在列表 | ❌ 端口关闭 | — | 网络不通或 adbd 未监听 |
| **unauthorized** | `unauthorized` | ✅ 端口开放 | ADB CNXN 收到但未确认 | RSA 密钥弹出但用户未确认 |

## 诊断流程

### 0. 前置检查：ADB 服务器是否运行

**现象**：`adb devices` 命令**挂死/超时**（10+ 秒无响应），而非快速返回设备列表。

**根因**：Mac 端的 ADB 服务器守护进程（`adb` daemon on port 5037）未运行。`adb devices` 在尝试连接守护进程时阻塞等待，直到超时。

```bash
# 检查 ADB 服务器是否运行
adb kill-server 2>&1
# 输出: * daemon not running; starting now at tcp:5037
# 或: error: cannot connect to daemon at tcp:5037: connection refused

# 启动服务器
adb start-server
# 输出: * daemon started successfully

# 验证
adb devices -l
```

**关键判断**：`adb devices` 挂死/超时 + `adb kill-server` 显示 `daemon not running` = ADB 服务器进程已退出。重启后设备可能显示 `offline`（RSA 授权问题），这是两个独立问题。

### 与其它 ADB 连接失败模式的区分

| 状态 | `adb devices` 行为 | `adb kill-server` 输出 | 根因 |
|------|-------------------|----------------------|------|
| **ADB 服务器未运行** | 挂死/超时（10s+） | `* daemon not running` | ADB 守护进程已退出 |
| **offline** | 快速返回 `offline` | `* daemon not running`（如果服务器也挂了）或正常 | RSA 密钥未授权 |
| **adbd 已退出** | 设备不在列表 | 正常 | 手机端 adbd 进程已死 |

**诊断序列**：`adb devices` 挂死 → `adb kill-server` 看是否 `daemon not running` → `adb start-server` → 再查设备状态。如果重启后设备显示 `offline`，则有两个独立问题需要分别处理。

### 1. 确认设备状态

```bash
adb devices -l
# 输出: 192.168.1.26:5555  offline
```

### 2. 确认网络层可达

```bash
# 网络层
ping -c 2 -W 3 <ip>          # 必须通（否则是网络问题）
nc -z -w 3 <ip> 5555         # 端口必须开放
```

**关键判断**：ping 通 + 端口开放 + `adb devices` 显示 `offline` = **ADB 授权问题**，不是网络问题。

### 3. 确认不是 USB 连接

```bash
adb devices -l
# 如果只有 TCP 设备显示 offline，没有 USB 设备 → 只能通过 TCP 修复
```

### 4. 尝试恢复连接

```bash
# 方案 A：重启 ADB 服务器（清除 Mac 侧缓存）
adb kill-server
sleep 2
adb start-server
adb connect <ip>:5555

# 方案 B：强制重连 offline 设备
adb reconnect offline
sleep 3
adb connect <ip>:5555

# 方案 C：如果 A+B 都失败，说明 RSA 密钥被手机拒绝
# 需要用户手动在手机上接受授权
```

## 根因

ADB over TCP 使用 RSA 密钥对进行身份验证。当手机重启、ADB 调试设置被重置、或密钥文件变更后，手机端不再信任 Mac 的 RSA 公钥。此时：

- 网络层完全正常（ping 通，端口开放）
- ADB 协议层 TCP 连接建立成功（CNXN 握手完成）
- 但 auth token 交换失败 — 手机拒绝 Mac 的 RSA 公钥
- `adb devices` 显示 `offline` 而非 `device`

## 修复方案

### 方案 A：USB 临时连接（推荐）

```
1. 用 USB 线连接手机到 Mac
2. 手机上弹出 "允许 USB 调试？" 对话框
3. 勾选 "始终允许此计算机" → 确认
4. 验证：adb devices 显示 "device"
5. 拔掉 USB，TCP 连接自动恢复授权
```

### 方案 B：重启手机 ADB 调试

```
在手机上：设置 → 开发者选项 → 关闭 "USB 调试" → 重新开启
```

### 方案 C：检查充电时不休眠

部分 MIUI/定制 ROM 在深度休眠时杀掉 ADB 后台进程：
```
设置 → 开发者选项 → "充电时不休眠" → 开启
```

### 方案 D：检查 ADB 密钥文件

```bash
# Mac 侧 ADB 密钥存在性
ls -la ~/.android/adbkey*
# 如果密钥文件损坏或为空，删除后重新生成
rm ~/.android/adbkey*
adb kill-server
adb start-server
# 然后 USB 连接重新授权
```

## 预防措施

- 手机开启"充电时不休眠"（开发者选项）
- 部署 ADB TCP watchdog（见 `references/adb-watchdog-deployment.md`）
- 避免频繁插拔 USB 线导致 adbd 重启
- 手机重启后需要重新 `adb tcpip 5555` 或通过 Magisk service.d 自动设置

## 与"adbd 已退出（孤儿 socket）"的区分

| 特征 | offline | adbd 已退出 |
|------|---------|-------------|
| `adb devices` | 显示设备 + `offline` | 设备不在列表 |
| `nc -zv <ip> 5555` | ✅ 开放 | ✅ 开放 |
| Python raw socket recv | ✅ 收到 CNXN | ❌ 超时 |
| `adb reconnect offline` | 可能移除设备 | 无效果 |
| 根因 | RSA 密钥未授权 | adbd 进程已死 |
| 修复 | USB 连接重新授权 | 重启 adbd 或部署 watchdog |
