# Mi8 Termux Hermes Agent 完整安装记录

## 设备状态

| 项目 | 值 |
|------|-----|
| Device | Mi8 (dipper) |
| ROM | LineageOS 22.2 (Android 15) |
| Root | Magisk ✅ |
| Termux | Python 3.13.13 |
| ADB | 192.168.1.21（USB 有线网卡 RTL8153） |

## 核心阻碍

一个循环依赖链和三处缺失：

```
clang ↔ ndk-sysroot ↔ rust-std-aarch64-linux-android
        apt --fix-broken install 被 Magisk root 保护拒绝
                    ↓
pip wheel 缺失（ensurepip/_bundled 目录空）
pydantic-core 无 aarch64 Android wheel
hermes_agent 包目录缺失（flat 结构）
```

## 逐步解决

### Step 1: 修复 apt 依赖死锁

**关键绕过：** MagiskSU 阻止 `apt` 以 root 运行（"Ability to run this command as root has been disabled permanently"），但允许 `dpkg` 以 root 运行。

```
# run-as 下 apt download 到 /data/user/0/com.termux/
adb shell "run-as com.termux sh -c 'apt download ndk-sysroot rust-std-aarch64-linux-android'"

# su 下 dpkg -i 安装（不用 apt）
adb shell "su -c 'export PATH=/data/data/com.termux/files/usr/bin:/data/data/com.termux/files/usr/libexec:\$PATH;
  dpkg -i /data/user/0/com.termux/ndk-sysroot_29-2_aarch64.deb \
         /data/user/0/com.termux/rust-std-aarch64-linux-android_1.95.0-1_aarch64.deb'"

adb shell "su -c 'export PATH=/data/data/com.termux/files/usr/bin:/data/data/com.termux/files/usr/libexec:\$PATH; dpkg --configure -a'"
# → Setting up clang ... Setting up rust ...
```

### Step 2: 恢复 pip

pip wheel 缺失 → 用 get-pip.py：

```
adb shell "run-as com.termux sh -c 'curl -s https://bootstrap.pypa.io/get-pip.py -o /data/data/com.termux/files/home/get-pip.py'"
adb shell "run-as com.termux sh -c 'HOME=/data/data/com.termux/files/home /data/data/com.termux/files/usr/bin/python3 /data/data/com.termux/files/home/get-pip.py'"
```

可能遇到的坑：`/data/data/com.termux/files/home/.local` 被 root 拥有 → `su -c chown`。

### Step 3: pydantic-core 社区 wheel

无 aarch64 Android wheel（known issue: https://github.com/pydantic/pydantic-core/issues/1012）

```
curl -sLO "https://github.com/Eutalix/android-pydantic-core/releases/download/v2.46.3/pydantic_core-2.46.3-cp313-cp313-linux_aarch64.whl"
unzip -qo pydantic_core-*.whl -d pydantic_extracted
adb shell "su -c 'cp -r pydantic_extracted/pydantic_core /data/data/com.termux/files/usr/lib/python3.13/site-packages/'"
adb shell "su -c 'cp -r pydantic_extracted/pydantic_core-2.46.3.dist-info /data/data/com.termux/files/usr/lib/python3.13/site-packages/'"
```

**平台标签坑：** wheel 是 `linux_aarch64` 但 Termux Python 报告 `android`。pip 拒绝安装。手动 unzip 到 site-packages 后 .so 兼容（都是 Linux 用户空间的 Bionic libc）。

### Step 4: hermes-agent 安装

```
adb shell "run-as com.termux sh -c 'HOME=/data/data/com.termux/files/home PATH=/data/data/com.termux/files/home/.local/bin:\$PATH /data/data/com.termux/files/usr/bin/python3 -m pip install hermes-agent --no-deps'"
```

### Step 5: 创建 wrapper（hermes + hermes-agent）

```
# hermes CLI wrapper
adb shell "su -c 'cat > /data/data/com.termux/files/usr/bin/hermes << SCRIPTEOF
#!/data/data/com.termux/files/usr/bin/bash
export HOME=/data/data/com.termux/files/home
export SSL_CERT_FILE=/data/data/com.termux/files/usr/lib/python3.13/site-packages/certifi/cacert.pem
export PATH=/data/data/com.termux/files/usr/bin:\$PATH
export PYTHONPATH=/data/data/com.termux/files/usr/lib/python3.13/site-packages:\$PYTHONPATH
exec /data/data/com.termux/files/usr/bin/python3 -m hermes_cli.main \"\$@\"
SCRIPTEOF
chmod +x /data/data/com.termux/files/usr/bin/hermes'"

# hermes-agent wrapper
adb shell "su -c 'cat > /data/data/com.termux/files/usr/bin/hermes-agent << SCRIPTEOF
#!/data/data/com.termux/files/usr/bin/bash
export HOME=/data/data/com.termux/files/home
export SSL_CERT_FILE=/data/data/com.termux/files/usr/lib/python3.13/site-packages/certifi/cacert.pem
export PATH=/data/data/com.termux/files/usr/bin:\$PATH
export PYTHONPATH=/data/data/com.termux/files/usr/lib/python3.13/site-packages:\$PYTHONPATH
exec /data/data/com.termux/files/usr/bin/python3 -m run_agent \"\$@\"
SCRIPTEOF
chmod +x /data/data/com.termux/files/usr/bin/hermes-agent'"
```

### Step 6: 修复 .hermes 目录 owner

```
adb shell "su -c 'chown -R u0_a192:u0_a192 /data/data/com.termux/files/home/.hermes'"
adb shell "su -c 'chmod -R u+rwX /data/data/com.termux/files/home/.hermes'"
```

**注意：** `u0_a192` 是当前 Termux UID。用 `run-as com.termux id` 确认。

## 最终验证

```
$ adb shell "run-as com.termux sh -c 'HOME=/data/data/com.termux/files/home /data/data/com.termux/files/usr/bin/hermes version'"
Hermes Agent v0.17.0 (2026.6.19)
```

## 已知限制

- **pydantic-core 版本差：** 装的是 2.46.3（Eutalix 最新），hermes-agent 需要 2.46.4（pydantic 2.13.4 指定）。当前 2.46.3 尚能工作，未来如果出现 `AttributeError: module 'pydantic_core' has no attribute 'XXX'`，需要等 Eutalix 出 2.46.4 或手动降级 pydantic。
- **`import hermes_agent` 报 ModuleNotFoundError：** 这是预期的。hermes-agent 0.17.0 采用扁平包结构，顶层是 `hermes_cli`、`agent`、`gateway` 等，无 `hermes_agent/` 目录。`python3 -m hermes_cli.main` 和 `python3 -m run_agent` 正常工作。
- **Magisk 阻止 `apt` 但允许 `dpkg`：** 这是编译时的 `getuid() == 0` 检查，不是运行时策略。所有 apt相关操作需绕过。
