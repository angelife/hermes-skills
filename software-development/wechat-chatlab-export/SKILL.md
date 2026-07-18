---
name: wechat-chatlab-export
description: >-
  微信聊天记录解密导出 + ChatLab 分析全流程。
  覆盖 Android root 解密（首选）和 macOS 内存扫描（备选）。
  最终导出为 ChatLab 可读 JSON，用 AI 自动分析聊天规律、群活跃度、年度报告。
category: software-development
version: 3.0
---

# WeChat Chat Export → ChatLab Analysis

## Overview

```
WeChat DB (encrypted) → extract key → decrypt SQLCipher → JSON export → ChatLab import → AI analysis
```

## Prerequisites

- **Android**: Rooted device with ADB (TCP or USB), WeChat logged in
- **macOS**: WeChat v4.0.6（降级到此版本；3.8.x 太老不能登录）**或** v4.1+（需走 LLDB + PBKDF2 路线）
- Xcode Command Line Tools

## ⚠️ 封号风险声明

**内存扫描、进程注入、Frida Hook 等操作会被微信检测为"外挂"行为，有真实封案案例。**
- Issue #140 (ylytdeng/wechat-decrypt)：用户因使用内存扫描工具被微信封号
- **wcdb-key-tool 路线声称不会封号**（LLDB 只读一次寄存器，不修改程序行为，不接触网络）
- **推荐做法**：只对备用账号或测试设备操作，不在主登录账号上冒险
- **最安全的方案**：Android Root 路径（仅拉取 DB 文件 + MD5 公式解密，不触及进程内存）

---

## PATH A: Android Root (Preferred) ⭐

### Step 1: Connect & Verify

```bash
adb connect <device_ip>:5555    # TCP ADB
adb shell echo hello             # verify connection
```

**⚠️ ADB 多设备坑**：当有多个 ADB 连接（如 USB + 离线 TCP）时，`adb shell` 报 `more than one device/emulator`：

```bash
adb devices
# a6520fa3               device usb:20-2
# 192.168.0.171:5555     offline    ← 上一次的 TCP ADB 残留
# 用 -s 指定 USB 设备
adb -s <serial> shell ...
# 清理离线连接：
adb -s 192.168.0.171:5555 disconnect
```

### Step 2: Extract IMEI + UIN

```bash
# Get IMEI from build props
adb shell getprop persist.radio.imei | head -1

# Get UIN from WeChat prefs
adb shell cat /data/data/com.tencent.mm/shared_prefs/auth_info_key_prefs.xml | grep uin
# Look for: <int name="_auth_uin" value="-185082944" />
```

### Step 3: Calculate Key

```python
import hashlib
imei = '1234567890ABCDEF'  # ⚠️ Android 10+ 降级IMEI，非硬件IMEI
uin = '-185082944'          # from auth_info_key_prefs.xml，含负号
key = hashlib.md5((imei + uin).encode()).hexdigest()[:7]
# key = '0273023'
```

**⚠️ Key Formula Notes:**
- Standard (Android 10+ / LineageOS): `MD5("1234567890ABCDEF" + uin)[:7]`
  - Android 10+ 限制 IMEI 访问，微信降级使用默认 IMEI
  - 已验证于 WeChat 8.0.76 + LineageOS 22.2 (Mi8)
- Standard (Android 9-): `MD5(设备IMEI + UIN)[:7]`
- If `cipher_compatibility=1` fails, try these combos:
  - `MD5(IMEI + UIN_without_sign)[:7]` (strip leading `-`)
  - `MD5(android_id)[:7]` (from `settings get secure android_id`)
- 详细分析见 `references/android-8x-key-migration.md`

**🆕 Frida Hook (备选，当公式匹配失败时)**
```bash
# 需要 frida-tools + 手机端 frida-server
pip3 install frida-tools  # 大包，安装需 2-5 分钟
adb forward tcp:27042 tcp:27042
frida -U com.tencent.mm -l hook_sqlite3_key.js
```

### Step 4: Pull Database

```bash
adb shell "ls /data/data/com.tencent.mm/MicroMsg/*/"
adb pull /data/data/com.tencent.mm/MicroMsg/<hash>/EnMicroMsg.db /tmp/EnMicroMsg.db
```

### Step 5: Decrypt with sqlcipher（推荐：sqlcipher v4 一步到位）

```bash
# 1. 确保 sqlcipher v4 可用（从源码编译或 brew）
git clone https://github.com/sqlcipher/sqlcipher /tmp/sqlcipher 2>/dev/null || true
cd /tmp/sqlcipher && make -j4 sqlite3 CFLAGS="-DSQLITE_HAS_CODEC -DSQLCIPHER_CRYPTO_OPENSSL" LDFLAGS="-lcrypto"

# 2. 解密
/tmp/sqlcipher/sqlite3 /tmp/EnMicroMsg_encrypted.db <<'EOF'
PRAGMA key = '0273023';                      # 填入 Step 3 算出的 key
PRAGMA cipher_compatibility = 1;              # 关键！启用 SQLCipher 1 兼容
ATTACH DATABASE '/tmp/EnMicroMsg_decrypted.db' AS decrypted KEY '';
SELECT sqlcipher_export('decrypted');
DETACH DATABASE decrypted;
EOF
# 输出: /tmp/EnMicroMsg_decrypted.db (12-50MB 明文 SQLite)
# 若有 "table TablesVersion already exists" 警告 → 无害，忽略
```

### Step 6: 查看数据

---

## PATH B: macOS 内存扫描（v4.0.6 及更早，已验证可用）

### 前提条件

- macOS 微信降级到 **v4.0.6**
- 使用 [ylytdeng/wechat-decrypt](https://github.com/ylytdeng/wechat-decrypt)
- 需要 **sudo 权限**

```bash
# 1. 下载 WeChat 4.0.6
# 来源: zsbai/wechat-versions tag v4.0.6_20250723
# asset: WeChatMac-4.0.6.dmg (XZ压缩，需用 Python lzma 解压)
python3 -c "import lzma, shutil
with lzma.LZMAFile('WeChatMac-4.0.6.dmg') as fin:
    with open('WeChatMac-4.0.6.dmg_raw', 'wb') as fout:
        shutil.copyfileobj(fin, fout, length=16*1024*1024)"
hdiutil convert -format UDZO -o /tmp/WeChat.dmg /tmp/WeChatMac-4.0.6.dmg_raw
# 挂载安装

# 2. 编译 macOS 内存扫描器
cc -O2 -o /tmp/find_all_keys_macos /tmp/wechat-decrypt/find_all_keys_macos.c -framework Foundation

# 3. 签名 + 登录微信
sudo codesign --force --deep --sign - /Applications/WeChat.app
killall WeChat; open /Applications/WeChat.app
# 扫码登录

# 4. 提取密钥
sudo /tmp/find_all_keys_macos  # → ./all_keys.json

# 5. 解密数据库
python3 /tmp/wechat-decrypt/decrypt_db.py --key-file all_keys.json
```

---

## PATH C: macOS LLDB + PBKDF2（v4.1+，新方法）

**背景：** WeChat 4.1+ 不再在进程内存里缓存明文密钥，改用 passphrase + PBKDF2-SHA512 派生。所有基于 `x'<hex>'` 格式扫描的工具都失效。

**根本原因：** Issue #96 (ylytdeng/wechat-decrypt)
```
enc_key = PBKDF2-SHA512(passphrase, db_salt, iterations=256000, dklen=32)
```

**工具：** [TANGandXUE/wcdb-key-tool](https://github.com/TANGandXUE/wcdb-key-tool)
- 支持 macOS / Linux / Windows
- 单 Python 文件，零第三方依赖
- macOS 走 LLDB 断点捕获 passphrase
- 声称不会封号（只读一次寄存器）

### ⚠️ 已知坑

1. **macOS SIP 导致流程中断：** 脚本第 3 级（内存扫描）检测到 `task_for_pid` 失败后会抛 `SignatureInvalidError` 并 `sys.exit(1)`，**不会 fallthrough 到第 4 级（LLDB）**。需要手动跳过第 3 级——将第 3 级 `try/except` 块替换为直接跳转到第 4 级的 `print` + fallthrough 代码。

2. **DMCA 风险：** 微信数据库密钥提取项目有被腾讯 DMCA 下架的前科（[ycccccccy/wx_key](https://github.com/ycccccccy/wx_key) 代码全删，只剩 README）。有 1.8k star 但已无实际内容。如需获取代码，检查 fork 的 git history 或寻找替代项目。

3. **断点条件可能不匹配：** 脚本默认条件 `$rdx == 32` / `$x2 == 32` 过滤 passphrase 长度。如果微信传了不同长度，断点不会触发。可移除条件重试。

### 操作步骤

```bash
# 1. 下载工具
git clone https://github.com/TANGandXUE/wcdb-key-tool.git

# 2. 重签名微信（每次自动更新后可能需要重做）
sudo codesign --force --deep --sign - /Applications/WeChat.app
killall WeChat; open /Applications/WeChat.app

# 3. 提取密钥（首次需退出重登）
sudo python3 wcdb_key_tool_macos.py extract --decrypt
# 按提示：微信设置 → 退出登录 → 重新扫码登录
# 脚本自动 LLDB attach → 断点命中 → 读数 → detach → PBKDF2 → 解密

# 4. 后续只需解密（已有缓存的 passphrase）
sudo python3 wcdb_key_tool_macos.py decrypt
```

### macOS SIP 限制

- `task_for_pid` 在 SIP 开启时必然失败（`kr=5`）
- **即使以 root 运行也无法绕过 SIP 对 task_for_pid 的限制**（`osascript -e 'do shell script ... with administrator privileges'` 同样失败）
- wcdb-key-tool 脚本默认会在内存扫描失败后 fallback 到 LLDB
- LLDB 不需要 task_for_pid，但仍需 Root 权限
- 因此最终都需要 `sudo`，但不需要关 SIP

### 版本特异性：4.1.9 vs 4.1.10

**4.1.9 有特殊问题：** LLDB 断点不触发
- wcdb-key-tool 在 `CCKeyDerivationPBKDF` 上设置断点
- 4.1.9 可能仍使用旧式 raw key 缓存（不走 PBKDF2），因此断点从不命中
- 但 `task_for_pid` 又被 SIP 阻挡 → 两条路都走不通
- **结论：不要用 4.1.9**。要么 4.0.6（内存扫描），要么 4.1.10+（LLDB + PBKDF2）

---

## 版本兼容性总表

| 版本 | 密钥提取方式 | 登录状态 | 工具 | 备注 |
|------|-------------|---------|------|------|
| **v4.0.6** ✅ | 内存扫描 (raw key) | 可登录 | `find_all_keys_macos` + `decrypt_db.py` | 最稳定路线 |
| **v4.0.3.80** ✅ | 内存扫描 (raw key) | 可登录 | 同上 | 同上 |
| **v4.1.9** ⛔ | **双线阻塞** | 可登录 | 不可用 | LLDB 断点不触发（不走PBKDF2），SIP 又阻挡 task_for_pid。不要用此版本 |
| **≥v4.1.10** ⚠️ | LLDB + PBKDF2 派生 | 可登录 | `wcdb_key_tool_macos.py` | 脚本需先打补丁跳过第3级（SIP 导致 task_for_pid 失败） |
| **≤3.8.x** ❌ | N/A | 服务器拒绝登录 | N/A | 版本太老 |

降级来源：[zsbai/wechat-versions](https://github.com/zsbai/wechat-versions)（GitHub Releases，DMG 文件为 XZ 压缩）

**⚠️ DMG 下载 / 解压注意事项：**
- GitHub 和腾讯 CDN 提供的 `.dmg` 文件实际是 **XZ 压缩格式**（`file` 命令显示 `XZ compressed data`）
- 直接双击或 `hdiutil attach` 会失败
- 需先用 Python lzma 解压，再用 `hdiutil convert` 转换：
```python
# 解压
python3 -c "
import lzma, shutil
with lzma.LZMAFile('WeChatMac-<version>.dmg') as fin:
    with open('WeChatMac-<version>_raw.dmg', 'wb') as fout:
        shutil.copyfileobj(fin, fout, length=16*1024*1024)
"

---

## Step 3: Import into ChatLab

```bash
chatlab import ~/Desktop/张三/chat.json
chatlab sessions list
chatlab stats <session-id>
chatlab messages search --keyword "关键词" --session-id <id>
```

---

## ChatLab CLI Installation

```bash
export CXXFLAGS="-isysroot $(xcrun --show-sdk-path)"
export CFLAGS="-isysroot $(xcrun --show-sdk-path)"
npm install -g chatlab-cli
```

---

## Data Security

- All decryption runs **locally** (no cloud upload)
- Decrypted databases stored in `/tmp/` (auto-cleaned)
- AI analysis requires API key (optional)
