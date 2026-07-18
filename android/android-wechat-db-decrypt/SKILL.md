---
name: android-wechat-db-decrypt
description: "Android root + Frida hook 提取微信 EnMicroMsg.db 解密密钥，sqlcipher 解密明文导出。已验证于 Mi8 (LineageOS 22.2, WeChat 8.0.x)。"
version: 1.0.0
author: Hermes Agent
platforms: [macos, linux]
metadata:
  hermes:
    tags: [WeChat, Android, Frida, SQLCipher, Decryption]
---

# Android WeChat DB Decrypt

通过 Android root + Frida hook 解密微信数据库 EnMicroMsg.db。

**核心链路**: ADB → Frida hook sqlite3_key → 密钥 → sqlcipher → 明文 DB

## ⚠️ 第一优先：查历史 + 查已解密库

**执行任何解密操作之前**，先做以下两步，跳过则被用户严厉纠正：

### 1. 查 session history

```bash
session_search query="Android WeChat decrypt EnMicroMsg <型号>"
```

如果以前解密过，密钥公式、IMEI 默认值、UIN 都已在历史中。**直接取历史密钥解密**。

### 2. 查本地 /tmp/ 已解密库

```bash
ls -lh /tmp/EnMicroMsg_decrypted.db /tmp/Decrypted.db
sqlite3 /tmp/EnMicroMsg_decrypted.db "SELECT COUNT(*) FROM message" 2>/dev/null
sqlite3 /tmp/Decrypted.db "SELECT COUNT(*) FROM message" 2>/dev/null
```

如果已有明文库，**直接进入分析阶段**，不做无用解密。更新数据只需重新 pull + `PRAGMA key` 重解一次（10秒完成）。

### 3. 已知设备直接用密钥（跳过 Frida）

**Mi8 / 金（2026-07-12 起反复验证）：**

| 项 | 值 |
|----|-----|
| serial | `a6520fa3` |
| DB | `/data/data/com.tencent.mm/MicroMsg/d65f989d7e35cd4b56910fb8d96d4ec5/EnMicroMsg.db` |
| IMEI（微信侧） | `1234567890ABCDEF` |
| UIN | `-185082944`（带负号） |
| **key** | **`0273023`** |
| 必设 | `PRAGMA cipher_compatibility = 1` |

用户问「密码/密钥也有的」→ 直接答 **`0273023`**，不要重跑 Frida。

**快速重解（USB 已连）：**
```bash
source ~/.hermes/scripts/adb-connect.sh
adb disconnect <offline_tcp> 2>/dev/null || true   # 避免 multi-device
adb -s a6520fa3 shell "su -c 'killall -9 com.tencent.mm; sleep 2'"
adb -s a6520fa3 exec-out "su -c 'cat /data/data/com.tencent.mm/MicroMsg/d65f989d7e35cd4b56910fb8d96d4ec5/EnMicroMsg.db'" > /tmp/EnMicroMsg.db
/tmp/sqlcipher/sqlite3 /tmp/EnMicroMsg.db <<'EOF'
PRAGMA key = '0273023';
PRAGMA cipher_compatibility = 1;
ATTACH DATABASE '/tmp/Decrypted.db' AS decrypted KEY '';
SELECT sqlcipher_export('decrypted');
DETACH DATABASE decrypted;
EOF
```

## 前置条件

- Android 设备已 root（Magisk）  
- ADB 网络调试连通（TCP 或 USB）  
- Mac/Linux 端：Python3, 已编译 sqlcipher（`/tmp/sqlcipher/sqlite3`，v4.17.0）  
- 微信已登录

## 网络配置：为无 WiFi 的靠线手机设静态 IP

如果手机没有无线网卡、使用 USB 以太网卡联网（如 Mi8 + USB Ethernet 适配器场景），每次启动后需手动配置静态 IP 以保证 ADB 连接稳定：

```bash
# 1. 确认接口名（通常为 eth0 或 usb0）
adb shell "su -c 'ip addr show | grep -B2 \"192.168.1.\"'" 2>/dev/null

# 2. 设置静态 IP（先通过 DHCP 连上后才可执行）
adb shell "su -c '
  ip addr del <当前IP>/<掩码位> dev <接口>
  ip addr add <目标IP>/<掩码位> dev <接口>
  ip route add default via <网关> dev <接口>
'"

# 示例（用于 192.168.1.x 家庭网）：
adb shell "su -c '
  ip addr del 192.168.1.26/24 dev eth0
  ip addr add 192.168.1.26/24 dev eth0
  ip route add default via 192.168.1.1 dev eth0
'"

# 3. 验证
adb shell "su -c 'ip addr show eth0 | grep inet'"
adb shell "su -c 'ip route show'"
```

**注意**：此配置在重启后丢失。如需持久化，需修改 `/data/misc/ethernet/ipconfig.txt`（LineageOS 路径）。

## 完整工作流

### Step 1: ADB 连接设备

**优先使用统一连接管理**（2026-07-17 起）：
```bash
source ~/.hermes/scripts/adb-connect.sh && ADB_TARGET=$(get_adb_device)
```
自动按 USB → TCP(已知IP列表) → 端口扫描 顺序发现设备。多个脚本不再各自硬编码 IP。
详见 `~/.hermes/scripts/adb-connect.sh`，所有 ADB 依赖的脚本已统一导入。

**手动连接（备用）**：
```bash
adb connect 192.168.1.26:5555
```

**⚠️ ADB WiFi 重连失效**：iOS → Android 微信迁移后/断开重连后，TCP 调试模式可能过期。`ping` 通但 `adb connect` 失败时，走 USB 重设：
```bash
adb usb                  # 插 USB 启用 USB 调试
adb tcpip 5555           # 切换到 TCP 模式
# 拔 USB
adb connect <ip>:5555    # 重新连接
```

**⚠️ ADB 多设备冲突**：当 USB 设备 + 历史 TCP 连接同时存在时，`adb shell` 报 `more than one device/emulator`。用 `-s <serial>` 指定设备，或 `adb disconnect` 清理离线连接。

**USB**：
```bash
adb devices  # 确认设备已识别
```

**⚠️ ADB 多设备坑**：当 USB 设备 + 历史 TCP 连接同时存在时，`adb shell` 报 `more than one device/emulator`。用 `-s <serial>` 指定设备，或 `adb disconnect` 清理离线连接。

**⚠️ 设备不可达**：如果 ping 通但 ADB 不通，先 `adb usb` 连 USB 然后 `adb tcpip 5555` 启用 TCP 调试。

**⚠️ 确认 root**：
```bash
adb shell "su -c 'whoami'"  # 确认有 # 返回
```

**⚠️ IMEI 默认值（Android 10+）**：Android 10+ 限制真实 IMEI 访问，微信降级使用默认 IMEI `1234567890ABCDEF`。`getprop persist.radio.imei` 返回的是硬件 IMEI，不等于微信看到的 IMEI。公式不匹配时优先试默认 IMEI。

### Step 2: 查找并拉取微信数据库

```bash
# 拉库前必须先杀微信进程（否则可能拉到脏页，解密报 malformed）
adb shell "su -c 'killall -9 com.tencent.mm 2>/dev/null; sleep 2'"

# 找到微信数据目录
adb shell "su -c 'ls /data/data/com.tencent.mm/MicroMsg/'"
# 找到 hash 目录
adb shell "su -c 'ls /data/data/com.tencent.mm/MicroMsg/*.db'"
# 拉取 EnMicroMsg.db
adb pull /data/data/com.tencent.mm/MicroMsg/<hash>/EnMicroMsg.db /tmp/
```

### Step 3: Frida Hook 提取密钥

```bash
# 1. 下载匹配版本 frida-server-arm64 推送到设备
# 2. 启动 frida-server
adb shell "su -c '/data/local/tmp/frida-server &'"
# 3. 端口转发
adb forward tcp:27042 tcp:27042
# 4. Kill & 重启微信
adb shell "su -c 'am force-stop com.tencent.mm && monkey -p com.tencent.mm 1'"
# 5. 附加并 hook
frida -U com.tencent.mm -l hook_sqlite3_key.js
```

**hook_sqlite3_key.js**:
```javascript
var modules = Process.enumerateModules();
for (var i = 0; i < modules.length; i++) {
    var m = modules[i];
    if (m.name.indexOf("libWCDB") !== -1) {
        var fn = Module.findExportByName(m.name, "sqlite3_key");
        if (fn) {
            Interceptor.attach(fn, {
                onEnter: function(args) {
                    var len = args[2].toInt32();
                    var buf = Memory.readByteArray(args[1], len);
                    var arr = new Uint8Array(buf);
                    var hex = "";
                    for (var j = 0; j < arr.length; j++) {
                        hex += ("0" + arr[j].toString(16)).slice(-2);
                    }
                    console.log("[KEY] " + hex);
                }
            });
            console.log("[HOOK] sqlite3_key hooked in " + m.name);
        }
    }
}
```

### Step 4: 离线公式验证（备选）

如果 Frida 不方便，可用公式离线计算：

```python
import hashlib
imei = "1234567890ABCDEF"  # Android 10+ 默认IMEI
uin = "-185082944"         # 从 /data/data/com.tencent.mm/shared_prefs/ 获取
key = hashlib.md5((imei + uin).encode()).hexdigest()[:7]
print(f"Key: {key}")
```

注意：Android 10+ 限制 IMEI 访问，微信降级使用默认 IMEI `1234567890ABCDEF`。旧设备（Android 9-）用真实 IMEI（`getprop persist.radio.imei`）。

**已验证公式（2026-07-12, Mi8 + WeChat 8.0.76）**：
```python
imei = "1234567890ABCDEF"   # 微信看到的 IMEI
uin = "-185082944"          # 含负号
key = hashlib.md5((imei + uin).encode()).hexdigest()[:7]
# 结果: 0273023 → sqlcipher v4 + cipher_compatibility=1 → 解密成功
```

### Step 5: 编译 sqlcipher（Mac/Intel）

```bash
git clone https://github.com/sqlcipher/sqlcipher /tmp/sqlcipher
cd /tmp/sqlcipher
make -j4 \
  CFLAGS="-DSQLITE_HAS_CODEC -DSQLCIPHER_CRYPTO_OPENSSL -DSQLITE_EXTRA_INIT=sqlcipher_extra_init -DSQLITE_EXTRA_SHUTDOWN=sqlcipher_extra_shutdown -DSQLITE_TEMP_STORE=2 -I/usr/local/include" \
  LDFLAGS="-L/usr/local/lib -lcrypto" \
  sqlite3
# 编译产物: /tmp/sqlcipher/sqlite3
```

### Step 6: 解密数据库

```bash
/tmp/sqlcipher/sqlite3 /tmp/EnMicroMsg_encrypted.db <<'EOF'
PRAGMA key = '<7位密钥>';
PRAGMA cipher_compatibility = 1;
ATTACH DATABASE '/tmp/EnMicroMsg_decrypted.db' AS decrypted KEY '';
SELECT sqlcipher_export('decrypted');
DETACH DATABASE decrypted;
EOF
ls -lh /tmp/EnMicroMsg_decrypted.db
```

**关键参数**: `PRAGMA cipher_compatibility = 1` 启用 SQLCipher 1 兼容模式（kdf_iter=4000, cipher_use_hmac=OFF, page_size=1024）。不设此参数解密失败。  

**已验证的 sqlcipher**: `/tmp/sqlcipher/sqlite3`（v4.17.0 community），已编译好。  

**快速刷新数据**: 手机有新消息时，只需重新 pull + 上同个 key 重跑一遍解密（约10秒）：
```bash
adb exec-out "su -c 'cat .../EnMicroMsg.db'" > /tmp/EnMicroMsg_encrypted.db
# 然后同上解密命令
```

**已验证（Mi8 + WeChat 8.0.76, 2026-07-12）**：
```python
imei = "1234567890ABCDEF"   # 微信看到的默认 IMEI（非硬件 IMEI）
uin = "-185082944"          # 含负号
key = hashlib.md5((imei + uin).encode()).hexdigest()[:7]
# key = "0273023"
```

### Step 7: 查看数据

```bash
sqlite3 /tmp/EnMicroMsg_decrypted.db ".tables"
sqlite3 /tmp/EnMicroMsg_decrypted.db "SELECT datetime(createTime/1000,'unixepoch','+8 hours'), isSend, type, substr(content,1,80) FROM message WHERE type=1 LIMIT 10"
```

## message 表核心字段

| 字段 | 类型 | 说明 |
|------|------|------|
| msgId | INTEGER | 主键 |
| msgSvrId | INTEGER | 服务器消息ID |
| type | INT | 1=文本, 3=图片, 34=语音, 43=视频/红包, 47=表情, 49=公众号/链接, 285212721=文章分享 |
| isSend | INT | 1=发出的, 0=收到的 |
| createTime | INTEGER | 时间戳(毫秒, UTC+0) |
| talker | TEXT | 聊天对象ID |
| content | TEXT | 消息内容 |
| transContent | TEXT | 翻译/引用内容 |

- 群聊 `talker` 以 `@chatroom` 结尾
- 群聊中 content 格式：`<发送者wxid>:<实际内容>`

## 已知陷阱

**相关参考**：\n- `references/ios-to-android-wechat-migration.md` — iOS → Android 微信数据迁移流程\n- `references/wechat-title-extraction.md` — Playwright 批量提取公众号文章标题的方法\n- `references/automated-pull-workflow.md` — cron 定时拉取和 ADB 备用连接\n- `references/hindsight-import.md` — **解密后导入 Hindsight 的工作流**（Hindsight 是唯一的记忆系统，不要另建）\n- `scripts/pull_wechat.sh` — 自动拉取脚本（部署于 `~/.hermes/scripts/`）

**⚠️ 操作前必须先扫网络**：拿到"检查设备"类任务后，必须先 scan LAN 确认设备真实在线（`arp -a` / `ping -c1`），不要凭记忆假设。用户明确纠正过："要先判断网络上现有机器再判断怎么做"。

**⚠️ 拉库前必须先杀微信进程**：微信在运行时持续写入数据库。直接 pull 可能拉到半写的脏页，解密时报 `database disk image is malformed`。**每次拉库前先杀微信**：

**⚠️ 不要创建独立的记忆服务**：被用户严厉纠正过。所有提取的数据存入 **Hindsight**（http://127.0.0.1:8888），不要创建 memory_server.py / stash-memory 或任何独立记忆存储。Hindsight 是唯一的记忆系统。

**⚠️ `pull_wechat.sh` 自动拉取脚本**（v4，2026-07-17 更新）：使用统一 `adb-connect.sh` 做 ADB 目标检测，不再硬编码 IP。同时支持本地已解密 DB 作为离线备用：当 ADB 不可用时自动使用 `/tmp/Decrypted.db` 缓存数据，不会报错退出。

**⚠️ Cron 任务因模型名漂移跳过**：如果全局推理配置中的模型名被自动替换（如 `deepseek-v4-flash-free` → `oc/deepseek-v4-flash-free`），Cron 调度器会因"配置漂移保护"跳过任务。通过 `cronjob update` 固定任务的 `model` 和 `provider` 参数解决：
```
cronjob action=update job_id=<id> model={model:'oc/deepseek-v4-flash-free',provider:'opencode'}
```
```bash
adb shell "su -c 'killall -9 com.tencent.mm 2>/dev/null; sleep 2'"
adb pull /data/data/com.tencent.mm/MicroMsg/<hash>/EnMicroMsg.db /tmp/
```
如果已经拉了损坏的库，重拉一次即可，不需要换密钥。

**⚠️ sqlcipher 复杂查询报 "database disk image is malformed"**：即使 `PRAGMA key` + `SELECT count(*)` 正常，某些查询结构（尤其 `WHERE talker=` 字段条件、`ORDER BY ... DESC`、`datetime()` 转换）也可能触发 sqlcipher 编译 bug 而崩溃。这不是数据损坏。
**解决方案：用 Python subprocess 代替复杂 sqlcipher 查询**——sqlcipher 只做 ASC 顺序全量输出，Python 做过滤和排序：
```python
import subprocess
result = subprocess.run(['/tmp/sqlcipher/sqlite3', '/tmp/EnMicroMsg.db'],
    input=b"PRAGMA key='xxx';\nPRAGMA cipher_compatibility=1;\n.mode list\n.separator '\\t'\nSELECT createTime, type, isSend, substr(content,1,200) FROM message ORDER BY createTime ASC;\n",
    capture_output=True, timeout=30)
lines = result.stdout.decode().strip().split('\n')
# Python 层做条件过滤、逆序、时间转换
for line in lines[-30:]:
    parts = line.split('\\t')
```
这种模式避免在 sqlcipher 层做任何复杂条件运算，全部推到 Python 处理。

**⚠️ sqlcipher ATTACH+export 失败**：如果 `PRAGMA key` + `SELECT count(*)` 正常返回，但 `ATTACH DATABASE` + `sqlcipher_export()` 报 `database disk image is malformed`，说明是 sqlcipher 编译版本的 export 兼容性 bug。用 heredoc 直查替代：
```bash
/tmp/sqlcipher/sqlite3 /tmp/EnMicroMsg.db <<'EOF'
PRAGMA key = '0273023';
PRAGMA cipher_compatibility = 1;
SELECT datetime(createTime/1000,'unixepoch','+8 hours'), isSend, type, substr(content,1,500) FROM message ORDER BY createTime DESC LIMIT 30;
EOF
```
需要全量数据时，用 `.output` 输出为 CSV 再用 sqlite3 重建。

**⚠️ ADB offline 状态（RSA 授权被拒）**：`adb devices` 显示 `offline` 意味着 TCP 连接已建立但 RSA 密钥授权未通过。与"端口不通"或"守护进程挂死"有本质区别：

| 现象 | 原因 | 应对 |
|------|------|------|
| 空列表 | ADB server 未运行 | `adb kill-server; adb start-server` |
| `offline` | RSA 授权被拒 | 需手机端确认授权弹窗，或 USB 重连后重新配对 |
| TCP 能连无响应 | adbd 守护进程挂死 | `su -c stop/start adbd` 或 USB 插拔 |

**offline 状态无法通过自动化恢复**——`adb connect` 失败后 `adb disconnect` 再连仍然失败，因为授权缓存已被清除。唯一恢复路径：
1. **USB 直连**（最可靠）：插 USB 线 → 手机上确认 RSA 密钥弹窗 → 授权后设备状态变为 `device`
2. **手机侧操作**：开发者选项 → 撤销 ADB 授权 → 重新连接并确认弹窗

**⚠️ ADB 守护进程挂死检测**：端口 5555 开放（`nc -zv` 成功）但 ADB 协议无响应（TCP 能连但不发 CNXN 握手）。此状态不同于"端口关闭"或"拒绝连接"。修复：
```bash
# 在手机上重启 adbd
su -c stop adbd && su -c start adbd
# 或 USB 插拔触发 ADB 自启
```
USB 直连是可靠的 fallback——`adb devices` 显示 USB 设备后即可操作。

**⚠️ ADB 多设备冲突**：当 USB 设备 + 历史 TCP 离线连接同时存在时，`adb shell` 报 `more than one device/emulator`。用 `adb -s <serial>` 指定目标设备，或 `adb disconnect <offline_ip>:5555` 清理离线连接。

3. **Frida 版本匹配**：服务端和客户端版本必须一致（`frida --version` 检查）
4. **微信进程保护**：微信重启后要快速 attach，建议 kill → start → sleep(3) → attach
5. **ADB 端口转发**：每次 ADB 重连后要重新 `adb forward tcp:27042 tcp:27042`
6. **sqlcipher 编译慢**：`make -j4` 编译 sqlite3.c 这步最慢（3-5分钟），耐心等待
7. **cipher_compatibility**：缺失此参数会报 "file is not a database"
8. **数据库可能很少消息**：不是破解失败，账号本身没聊天记录。如需验证可查官方号 `weixin` 的欢迎消息
9. **sqlcipher 版本**：用上游 master（v4.x），早期版本不支持 `cipher_compatibility`
10. **IMEI 用默认值非硬件值**：Android 10+ 微信看到的是 `1234567890ABCDEF`，不是 `getprop persist.radio.imei`。公式不匹配时第一反应换默认 IMEI，不要以为是公式错了。
11. **UIN 含负号**：从 `auth_info_key_prefs.xml` 取的 `_auth_uin` 值带负号（如 `-185082944`），公式中保留负号。
12. **不查历史直接重头开始会被严厉纠正**：每次解密前必须 `session_search` 查历史 + `ls /tmp/` 查已解密库。
13. **外部文章链接不进 Hindsight 记忆层**：解密后提取的文章链接只列给用户看，不自动导入 Hindsight。用户选看 → 读 → 提炼洞察后才存。见上文"数据流向规则"。

## 数据流向规则（严格）⚠️

解密出文章链接后，必须按以下顺序处理，不能跳过：

```
解密 → 提取文章 → 列出给用户 → 用户选 → 读选定文章 → 提炼洞察 → 存 Hindsight
```

**规则一：文章链接不进记忆。**
从微信群提取的公众号文章链接不存入 Hindsight。文章是外部信息源，不是个人记忆。LLM 从标题抽实体关系纯属浪费 token。

**规则二：先展示，再操作。**
提取出的文章先列给用户问"要看哪篇"。等选择后再读内容。读后的有价值洞察才存 Hindsight。

**规则三：只存提炼，不存原始。**
读完后存的是判断/结论/洞察，不是原文或链接。

## 快速验证脚本

```python
import hashlib, sqlite3

# 离线计算密钥
imei = "1234567890ABCDEF"
uin = "-185082944"  
key = hashlib.md5((imei + uin).encode()).hexdigest()[:7]
print(f"Formula: MD5({imei}+{uin})[:7] = {key}")

# 验证解密库
conn = sqlite3.connect('/tmp/EnMicroMsg_decrypted.db')
c = conn.cursor()
c.execute("SELECT COUNT(*) FROM message")
print(f"Messages: {c.fetchone()[0]}")
c.execute("SELECT DISTINCT talker FROM message LIMIT 10")
for row in c.fetchall():
    print(f"  Talker: {row[0]}")
conn.close()
```
