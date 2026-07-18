# Magisk v30+ Root 授权策略

## 问题: ADB Shell 的 `su` 返回 Permission Denied

Magisk v30 在 LineageOS 22.x (Android 15) 上，`adb shell su -c id` 可能返回 Permission denied，即使 magiskd 正在运行、版本号正常。

### 诊断步骤

```bash
# 1. Magisk 版本
adb shell magisk -c
# → 30.7:MAGISK:R (30700) ← Magisk 正常

# 2. Magisk daemon
adb shell ps -A | grep magiskd
# → root 952 1 ... magiskd ← daemon 正常运行

# 3. su 路径
adb shell which su
# → /product/bin/su (指向 ./magisk 的符号链接)

# 4. 尝试授权
adb shell su -c id
# → Permission denied ← 授权策略问题

# 5. Termux 用户验证 (如果已授权过)
adb shell "run-as com.termux su -c id"
# → uid=0(root) ← Termux 有权限
```

### 根因

Magisk v30+ 默认不给 ADB shell (UID 2000) root 权限。这是 Magisk 的**策略配置问题，不是安装失败**。不需要重新刷 boot.img。

### 解决方案

在手机上操作:
1. 打开 Magisk app
2. 右下角**盾牌图标**（超级用户页面）
3. 如果有 `shell` 条目 → 点 → 设置为 "允许"
4. 如果没有 → 右上方三点 → "显示所有"
5. 或者: **设置**（齿轮图标）→ **超级用户访问权限** → 改为 **"应用和ADB"** 或 **"所有应用"**

验证:
```bash
adb shell su -c id
# → uid=0(root) gid=0(root) context=u:r:magisk:s0
```

### 如果无法在手机上操作（屏幕不可用等）

使用 `magisk --sqlite` 直接写入授权策略（需要已有 root）:

```bash
adb shell "magisk --sqlite 'INSERT OR REPLACE INTO policies (uid,policy,logging,notification) VALUES (2000,2,1,0);'"
```

但注意: `magisk --sqlite` 需要 root 权限——死循环。如果完全无法在手机 UI 操作，可以考虑:
- ADB 输入模拟: `adb shell input tap <x> <y>`（需要知道 Magisk app 的按钮坐标）
- 通过 Termux 已授权的 su 来操作