# ADB Reverse Proxy: 让 Android 设备使用 Mac 的 New API

## 场景

Android 设备（如 Mi8/金同学）通过 USB ADB 连接 Mac，但无法直连 Mac 的 New API（运行在 Mac 的 `127.0.0.1:3000`）。通过 `adb reverse` 将设备的 `127.0.0.1:3000` 映射到 Mac 的 `127.0.0.1:3000`。

## 步骤

### 1. 设置 ADB reverse

```bash
adb -s <serial> reverse tcp:3000 tcp:3000
# 验证：adb reverse --list
```

### 2. 创建 New API token

```bash
# 先登录
curl -c /tmp/nac.txt http://127.0.0.1:3000/api/user/login \
  -X POST -H "Content-Type: application/json" \
  -d '{"username":"root","password":"123456"}'

# 创建 token（返回的 key 在 API response 中但不完整，需从 DB 回读）
curl -b /tmp/nac.txt -H "New-Api-User: 1" \
  http://127.0.0.1:3000/api/token/ \
  -X POST -H "Content-Type: application/json" \
  -d '{"name":"<device-name>","user_id":1,"remain_quota":99999999,"unlimited_quota":true}'

# 从 DB 读取完整 key
python3 -c "
import sqlite3
conn = sqlite3.connect('/tmp/na-current.db')
c = conn.cursor()
c.execute(\"SELECT key FROM tokens WHERE name='<device-name>' ORDER BY id DESC LIMIT 1\")
print(c.fetchone()[0])
"
```

### 3. 更新 Android 设备的 Hermes config

**环境：debian chroot（如 Mi8）— 路径在 `/data/local/tmp/debian/root/.hermes/config.yaml`**

```bash
# 推送到 sdcard 中转
adb push /tmp/<config>.yaml /sdcard/na-config.yaml

# 用 root 复制到 debian chroot
adb shell "su -c 'cp /sdcard/na-config.yaml /data/local/tmp/debian/root/.hermes/config.yaml && chown root:root /data/local/tmp/debian/root/.hermes/config.yaml'"
```

**环境：Termux — 路径在 `/data/data/com.termux/files/home/.hermes/config.yaml`**

```bash
adb push /tmp/<config>.yaml /sdcard/na-config.yaml
adb shell "run-as com.termux cp /sdcard/na-config.yaml /data/data/com.termux/files/home/.hermes/config.yaml"
```

### 4. Config 模板（添加 New API provider）

```yaml
model:
  default: newapi/grok-4.5

providers:
  newapi:
    base_url: http://127.0.0.1:3000/v1
    api_key: <token-from-step-2>
    timeout: 60
    max_tokens: 4096

fallback_providers:
  - provider: newapi
    model: grok-4.5
```

保留原有的其他 provider（如 omniroute、agnes）作为 fallback。不要覆盖整个文件，只添加 `newapi` 块。

### 5. 从设备内测试

```bash
# 直接在 chroot/termux 内测试
adb shell "su -c 'curl -sS -m15 http://127.0.0.1:3000/v1/chat/completions \
  -H \"Authorization: Bearer <token>\" \
  -H \"Content-Type: application/json\" \
  -d '\''{\"model\":\"grok-4.5\",\"messages\":[{\"role\":\"user\",\"content\":\"只回ok\"}],\"max_tokens\":10}'\''"
```

### 6. 重启 gateway

通过 ADB shell（**不能**从 gateway 进程内执行 `hermes gateway restart`）：

```bash
adb shell "su -c 'pkill -f hermes 2>/dev/null; sleep 1'"
sleep 2
adb shell "su -c 'cd /data/local/tmp/debian && /usr/sbin/chroot . /root/.local/bin/hermes gateway start > /tmp/hermes_gw.log 2>&1 &'"
```

## 注意事项

- ADB reverse 在设备重连（拔线/重插 USB）后**失效**，需要重新设置
- 可配合 cron/watchdog 脚本保持 reverse 持久化
- 从 gateway 内部无法 `pkill hermes`（SIGTERM 会传播到子进程，ADB 连接断开）。必须通过 ADB 外部执行
- debian chroot 环境的 config 需 `su -c`（root）写入；Termux 环境需 `run-as com.termux`（app user）
