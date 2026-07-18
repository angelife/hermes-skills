# Android WeChat 8.x — 密钥派生机制变更

## 背景

**⚠️ 2026-07-12 更新：公式其实是有效的，关键在 IMEI 来源。**

WeChat 8.0+（Android）中，Android 10+ 限制了对真实 IMEI 的访问。微信降级使用**默认 IMEI `1234567890ABCDEF`**。因此如果拿真实硬件 IMEI 去算，公式当然不匹配——要用微信自己看到的那个 IMEI。

## 验证结论（2026-07-12, WeChat 8.0.76 on LineageOS 22.2, Mi8）

| 参数 | 值 |
|------|-----|
| 真实 IMEI | 867252038607635 |
| 微信使用的 IMEI | **1234567890ABCDEF**（Android 10+ 默认） |
| UIN（含负号） | -185082944 |
| **正确 Key** | **`0273023`** |
| 解密结果 | ✅ **成功**（sqlcipher v4.17.0 + cipher_compatibility=1） |

【更正】最初用真实 IMEI 算出的 `702e092` 无效，改用默认 IMEI `1234567890ABCDEF` 后正确。

## 正确流程

```python
import hashlib
imei = "1234567890ABCDEF"   # 微信看到的 IMEI（非硬件 IMEI）
uin = "-185082944"          # 含负号
key = hashlib.md5((imei + uin).encode()).hexdigest()[:7]
print(key)  # 0273023
```

### 解密命令

```bash
# 用 sqlcipher v4（/tmp/sqlcipher/sqlite3）
/tmp/sqlcipher/sqlite3 /tmp/EnMicroMsg_encrypted.db <<'EOF'
PRAGMA key = '0273023';
PRAGMA cipher_compatibility = 1;
ATTACH DATABASE '/tmp/EnMicroMsg_decrypted.db' AS decrypted KEY '';
SELECT sqlcipher_export('decrypted');
DETACH DATABASE decrypted;
EOF
```

## ADB 多设备坑

当 USB + 离线 TCP 同时存在时，`adb shell` 报 `more than one device/emulator`：

```bash
adb devices
# a6520fa3               device usb:20-2
# 192.168.0.171:5555     offline
adb shell ...  # ERROR

# 修复：用 -s 指定 USB 设备
adb -s a6520fa3 shell ...
```

## 为什么之前误判

1. 初次拿到的是真实 IMEI（`867252038607635`）→ 算出 `702e092`
2. 用 sqlcipher 4 默认参数尝试 + 各种 PBKDF2 组合 → 全部失败
3. 结论：新版改了密钥机制 → 写入 skill 供以后参考
4. **但实际上** 4 年前就已经用 Frida 提过正确的 key（`0273023`），这会通过 session_search 才发现
5. 教训：**先搜历史记录再下结论**，经验卡片和经验值比当次的尝试结果更可靠

## 可行方案

### 方案 A：Frida Hook (推荐)

```bash
# 1. 手机端启动 frida-server
adb shell su -c '/data/local/tmp/frida-server &'

# 2. Mac 端安装 frida-tools
pip3 install frida-tools
# 注意：frida-tools 包较大，pip 安装可能需要 2-5 分钟

# 3. 编写 hook 脚本 hook_sqlite3_key.js
# 目标：hook libWCDB.so 中调用 sqlite3_key 的位置
# 参考：ylytdeng/wechat-decrypt Issue #96

# 4. 运行 hook
frida -U com.tencent.mm -l hook_sqlite3_key.js
```

### 方案 B：wcdb-key-tool（仅 macOS/Windows，不适用于 Android）

Android 上没有等效的 LLDB/GDB 断点方案，无法复用 wcdb-key-tool。

### 方案 C：直接使用手机上的 sqlcipher

```bash
# 如果手机编译了 sqlcipher 静态二进制：
adb push sqlcipher-static /data/local/tmp/
adb shell su -c 'chmod +x /data/local/tmp/sqlcipher-static'
adb shell su -c '/data/local/tmp/sqlcipher-static /data/data/.../EnMicroMsg.db'
```

## 提醒

- macOS 降级到 4.0.6 后内存扫描是当前最稳定的路线
- Android 8.x 的 Frida Hook 方案已验证但未在本会话中完整跑通（frida-tools 安装超时）
