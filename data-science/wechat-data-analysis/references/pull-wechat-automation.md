# 微信自动拉取与文章分析流水线

## 概述

定时通过 ADB 从已 Root 的 Android 设备拉取微信 EnMicroMsg.db，解密后检测新消息，发现新分享的公众号文章后自动提取内容并分析。

## 架构

```
cron (每30min) → pull_wechat.sh → 检测新增 → 有? → 提取文章URL → 浏览器读取 → 整理输出
                                  ↓ 无新增
                              安静退出
```

## pull_wechat.sh 脚本

位置：`~/.hermes/scripts/pull_wechat.sh`

### ADB 连接策略（已解决 USB/TCP 双模式）

脚本自动检测两种 ADB 连接方式，USB 优先：

```bash
# USB 串号（插线时）
ADB_USB="a6520fa3"

# TCP 地址（远程时）
ADB_TCP="192.168.1.26:5555"

# 自动选择
if adb devices | grep -q "$ADB_USB"; then
    ADB_TARGET="$ADB_USB"        # USB 优先
elif adb connect "$ADB_TCP" | grep -q "connected"; then
    ADB_TARGET="$ADB_TCP"        # TCP 兜底
else
    exit 1                       # 都不可达
fi
```

### ADB 连接可靠性（多模型建议汇总）

2026-07-14 会话中手机只有蜂窝数据+VPN、无 WiFi 的场景下反复掉线，咨询了 ChatGPT/Gemini/Claude 后汇总方案。

#### 根本原因

| 原因 | 诊断 |
|------|------|
| ADB TCP "假开放" | ADB TCP 端口 5555 可用端口扫描检测到打开，但无 CNXN 握手响应（`adb connect` 返回 `offline` 而非 `device`） |
| USB 总线挂起 | Mac 熄屏/休眠后 USB 总线可能重置，设备从 `device` 变为 `offline` |
| ADB 授权自动撤销 | LineageOS 开发者选项中有 "Auto revoke ADB authorizations"，超时无交互后撤销 |
| adb server 僵死 | Mac 端 adb 进程长期运行后可能卡死，无法响应新连接 |
| 手机无 WiFi | 仅蜂窝数据+VPN 时，TCP ADB 走公网 IP 不可控，VPN 隧道 IP 固定但 Cron 不感知 |

#### 自愈核心逻辑（建议加到 pull_wechat.sh）

ChatGPT 推荐的梯度重试模式（三模型共识）：

```bash
# --- ADB 自愈核心逻辑 ---
MAX_RETRY=3
RETRY_DELAY=3
attempt=0

while [ $attempt -lt $MAX_RETRY ]; do
    adb -s "$ADB_TARGET" wait-for-device 2>/dev/null
    STATE=$(adb devices 2>/dev/null | grep "$ADB_TARGET" | awk '{print $2}')
    if [ "$STATE" = "device" ]; then
        break  # 健康
    fi
    echo "[WARN] ADB state=$STATE, attempt $((attempt+1))/$MAX_RETRY"
    adb kill-server 2>/dev/null
    sleep $RETRY_DELAY
    adb start-server 2>/dev/null
    sleep $RETRY_DELAY
    attempt=$((attempt+1))
done

if [ "$STATE" != "device" ]; then
    exit 1  # 三次后放弃
fi
```

Claude 特别指出：**flock 防重叠**，cron 环境下同一个脚本可能在上次执行尚未结束时再次触发（ADB 是全局锁，两个实例抢占会互相干扰）：

```bash
LOCKFILE="/tmp/wechat_pull.lock"
(
    flock -n 200 || { echo "skip: prior run still active"; exit 0; }
    # ... pull logic ...
) 200>"$LOCKFILE"
```

#### Android 侧优化

| 设置 | 命令 | 效果 |
|------|------|------|
| 充电不休眠 | `adb shell settings put global stay_on_while_plugged_in 2` | USB 供电时不让设备深度休眠打断 ADB |
| 关 ADB 超时 | 开发者选项中关闭 "Auto revoke ADB authorizations"（LineageOS 名称可能有差异） | 防止长时间无交互后台撤销授权 |
| ADB root | `adb root`（需要 LOS eng build 或 Magisk + adbd Extra） | 避免 su 每次都要提权 |

#### USB 持久化方案

当手机只有蜂窝数据+VPN、无 WiFi，而 Mac 需要稳定 ADB 时，最佳实践：

**方案 C（推荐）：USB 只做初始化 + watchdog 保活 + 脚本自愈**
- USB 负责首次连接
- 脚本内嵌 kill-server → start-server → wait 自愈循环
- Mac 端加 `caffeinate -i` 防止 USB 总线挂起

**方案 B（进阶）：手机主动 SSH 隧道**
```
手机端（Termux）→ ssh -R 5555:localhost:5555 macos@mac-ip
Mac 端直接连接 localhost:5555
```
无需 USB，但依赖手机网络到 Mac 可达。

**launchd 替代 cron**（Claude 建议）：cron 对 USB/IOKit 的权限继承不如 launchd。如果掉线频繁，转 plist：

```xml
<!-- ~/Library/LaunchAgents/com.user.wechat-pull.plist -->
<key>KeepAlive</key>
<true/>
<key>ThrottleInterval</key>
<integer>1800</integer>
```

### 解密方式

使用预编译的 sqlcipher 二进制 `/tmp/sqlcipher/sqlite3`：

```bash
PRAGMA key = '0273023';
PRAGMA cipher_compatibility = 1;
```

**已知问题：** 用 `ATTACH DATABASE` 方式解密时会报 `database disk image is malformed`。解决：直接在加密 DB 上执行 `SELECT COUNT(*)` 等简单查询可正常返回，但 `WHERE talker=` 子句和 `ORDER BY DESC` 也会触发此错误。建议用 Python 脚本处理复杂查询。

### 数据库加密密钥提取

密钥是 `MD5(IMEI + UIN)[:7]`：
```
IMEI = 1234567890ABCDEF (Mi8 固定值)
UIN  = 从 /data/data/com.tencent.mm/shared_prefs/ 获取
KEY  = MD5("1234567890ABCDEF" + uin)[:7]  # 当前: 0273023
```

## 文章分析工作流

### 提取最新分享的公众号文章

```bash
/tmp/sqlcipher/sqlite3 /tmp/EnMicroMsg_v5.db "PRAGMA key='0273023'; PRAGMA cipher_compatibility=1; SELECT createTime, type, isSend, substr(content,1,200) FROM message WHERE createTime > ${CUTOFF} ORDER BY createTime ASC;"
```

用 Python 脚本解析 type=49 的 XML content，提取 `<title>` 和 `<url>`：

```python
import re
# 提取标题
if '<title>' in content:
    title = content.split('<title>')[1].split('</title>')[0]
# 提取 URL
url_match = re.search(r'<url>(https?://mp\\.weixin\\.qq\\.com[^<]+)', content)
```

### 文章价值判断

从公众号文章提取可用思路时，关注：

1. **直接可用的工具/项目** — CowAgent, agentmemory, Hyper-Extract 等
2. **可复用的架构思路** — LLM Wiki 四层结构、四层记忆架构
3. **用户自己微信里写的观点** — 优先于文章本身

### 输出格式

结构化输出，按方向分组，每个方向带：
- 名称 + 一句话说明
- 对你项目的意义
- 预估工时

## 定时任务

```bash
# 每 30 分钟拉取一次
cronjob action=update job_id=32dcc6602315 \
  schedule="every 30m" \
  script="pull_wechat.sh"
```

模型需固定（防配置漂移）：
```bash
cronjob action=update job_id=32dcc6602315 \
  model='{"model":"oc/deepseek-v4-flash-free","provider":"opencode"}'
```

## 限制

- Mi8 微信被杀后无法拉取 → 需要看门狗保活
- 解密 db 在某些查询下会报 `malformed` → 改用 Python 脚本替代复杂 SQL
- iLink bot 不可用于群聊 → DM 是唯一可靠通道
- ADB TCP "假开放" — 端口可达但不一定可连接，脚本内需做 state 校验而非仅端口检测
- 无 WiFi 场景需要自愈逻辑而非纯 TCP 依赖
