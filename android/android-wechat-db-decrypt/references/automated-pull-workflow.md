# 微信数据库自动拉取流程

## 概述
通过 cron 定时任务自动拉取 Mi8 上的微信数据库，解密后检测新消息数。
脚本：`scripts/pull_wechat.sh`，部署于 `~/.hermes/scripts/pull_wechat.sh`。

## 依赖
- ADB 连通（USB 或 TCP）
- `/tmp/sqlcipher/sqlite3` 已编译（v4.x with cipher_compatibility）
- 微信密钥已知（见本 Skill SKILL.md Step 4）

## 执行流程
1. 检测 ADB 设备：USB 优先，TCP 备选
2. `adb exec-out su -c 'cat ...EnMicroMsg.db'` 拉取加密库
3. `PRAGMA key + cipher_compatibility + ATTACH + sqlcipher_export` 解密
4. 对比上次消息计数，输出差异
5. 复制解密库到 `/tmp/EnMicroMsg_decrypted_latest.db`

## cron job 配置
```bash
# 创建（每30分钟）
hermes cron create --schedule "every 30m" --name 微信数据自动拉取 \
  --script pull_wechat.sh --no-agent \
  --deliver origin

# 固定 model 避免全局配置漂移导致跳过
hermes cron update <job_id> --model oc/deepseek-v4-flash-free
```

## ADB 设备发现（USB 优先，TCP 备选）
脚本头部实现自动检测：
```bash
ADB_USB="a6520fa3"       # USB 串号
ADB_TCP="192.168.1.26:5555"  # TCP 地址

if adb devices 2>/dev/null | grep -q "$ADB_USB"; then
    ADB_TARGET="$ADB_USB"
elif adb connect "$ADB_TCP" 2>/dev/null | grep -q "connected"; then
    ADB_TARGET="$ADB_TCP"
else
    exit 1  # 设备不可达
fi
```

## 已知陷阱

- **拉库前必须杀微信进程**：`killall -9 com.tencent.mm` 防止脏页
- **ATTACH+export 可能失败**：sqlcipher 编译 bug 导致 `malformed` 错误。备选方案：直接 `PRAGMA key` 查询（`SELECT count(*)` 正常）
- **复杂 SQL 查询崩溃**：SQLCipher 在 `WHERE talker=`, `ORDER BY DESC`, `datetime()` 等复杂条件下可能崩溃。解决方案：用 `ORDER BY ASC` 全量输出 + Python 子进程做过滤/逆序
- **ADB 双模式**：USB 串号 `a6520fa3`，TCP `192.168.1.26:5555`
- **模型漂移**：全局 `model.default` 变更后 cron job 被跳过，需显式 `--model` 固定
- **ADB offline 状态**：脚本连续 2+ 天失败时，先检查 ADB 服务器是否运行（`adb kill-server` 看是否 `daemon not running`），再查设备状态。`adb devices` 挂死 → 服务器未运行；`adb devices` 显示 `offline` → RSA 密钥授权被拒，需 USB 连接重新授权。两种问题可能同时存在。

## ADB offline 专项诊断

**`adb devices` 显示 `offline` ≠ 设备不可达。** 此状态意味着 TCP 连接已建立但 RSA 密钥授权未被设备接受，与端口关闭/拒绝连接有本质区别。

### 三种故障状态区分

| `adb devices` 输出 | 含义 | 应对 |
|---|---|---|
| 空列表 | ADB server 未运行或没有设备 | `adb kill-server; adb start-server` |
| `x.x.x.x:5555 → offline` | TCP 连上但 RSA 授权被拒 | 需手机确认授权弹窗，或 USB 重连 |
| 命令挂死无输出 | 端口不通 | `ping` + `nc -zv x.x.x.x 5555` 确认 |

### offline 状态恢复路径

```
ping 设备        → 通                 → 网络层 OK
adb disconnect  → 可断开旧连接         → transport 级清理
adb connect     → "failed to connect" → 授权缓存已清除
```

**此状态无人干预无法恢复自动化。** 需要用户操作：
1. **USB 直连**（最可靠）：插 USB 线 → 手机上确认 RSA 密钥弹窗 → 授权写入 `~/.android/adbkey.pub`
2. **手机侧操作**：打开开发者选项 → 撤销 ADB 授权 → 重新连接并确认弹窗
3. **重启 adbd**（offline 时不可行 — `adb shell` 不可用）

### 子网不匹配提示

Mac 和手机在不同子网时（Mac 在 `192.168.1.0/24`，手机在 `192.168.2.0/24`），ARP 不在同一广播域：
```bash
ping 192.168.2.106          # 可能通（路由器跨子网路由）
arp -a | grep 192.168.2     # 可能无结果（跨子网）
adb connect 192.168.2.106   # 可能通但 offline
```
跨子网 ADB 授权稳定性更低。路由器重启、DHCP 续租都可能触发授权失效。

### 脚本自动化检测增强

当前 `pull_wechat.sh` 不区分 offline 和 not found。供后续维护参考的增强检测：

```bash
# 在 ADB 检测逻辑中加入 offline 专项判断
OFFLINE_CHECK=$(adb devices | grep "offline" | head -1)
if [ -n "$OFFLINE_CHECK" ]; then
    echo "$(date) ADB OFFLINE (needs RSA re-auth): $OFFLINE_CHECK" >> "$OUTPUT_DIR/wechat_cron.log"
    exit 1
fi
```

加入此检测后，日志能明确区分"设备不通"和"设备在但未授权"，减少排查时间。
