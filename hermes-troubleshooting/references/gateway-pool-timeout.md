# Gateway Pool Timeout 诊断

## 症状

Gateway log 反复出现：
```
Pool timeout: All connections in the connection pool are occupied.
```

死亡循环：`Pool timeout → 10 retries → fatal error → gateway restart → reconnect → Pool timeout again`

## 根因排查

Pool timeout 不是 gateway 自身的问题，而是**下游网络链路慢**导致 HTTPX 连接池无法释放。

### 1. 检查代理响应时间

```bash
curl --proxy http://127.0.0.1:10808 -s -o /dev/null -w "time=%{time_total}s\n" -m 10 https://api.telegram.org/bot
```

- **< 3s**：正常
- **> 3s**：连接池会逐渐积累，最终耗尽
- **timeout**：代理不通

### 2. 检查代理进程

```bash
ps aux | grep -iE "sing-box|clash|v2ray|xray" | grep -v grep
```

多个代理实例同时运行可能冲突或端口争用。

### 3. 检查 gateway 配置的代理地址

`config.yaml` 中 `telegram.proxy` 的协议/端口必须与实际代理匹配：

```yaml
# ✅ 正确（需确认实际代理协议和端口）
telegram:
  proxy: http://192.168.1.8:10808

# ❌ 常见错误：端口或协议不匹配
# proxy: socks5://192.168.1.8:1080   # 如果实际代理是 http://:10808
```

### 4. 验证代理连通性（从目标设备）

```bash
# 无代理 → 超时（被墙）
curl -s -o /dev/null -w "code=%{http_code} time=%{time_total}s\n" -m 10 https://api.telegram.org/bot
# → code=000 time=10.0s

# 有代理 → 正常响应（404 = 没传 token，是预期结果）
curl -x http://192.168.1.8:10808 -s -o /dev/null -w "code=%{http_code} time=%{time_total}s\n" -m 15 https://api.telegram.org/bot
# → code=404 time=1.5-4s
```

## 修复

| 根因 | 操作 |
|------|------|
| 代理响应慢（>3s） | 代理线路问题，非 gateway bug。接受现状或换代理 |
| 代理已死 | 重启代理（sing-box/clash） |
| 代理地址配置错误 | 修正 config.yaml `telegram.proxy` |
| 端口冲突 | 停掉多余的 sing-box 实例 |
| **无需调整 connection pool size** | Pool timeout 是症状不是根因，调大 pool 只延缓不解决 |

## 特殊模式：代理瞬断 → 重连风暴 (区别于慢代理)

### 根因

代理（xray/sing-box）**短暂宕机后恢复**（不是持续慢）。PTB 的 `_handle_polling_network_error` 触发 10 次重试，但退避时间过长（5s/10s/20s/40s/60s/60s... = 435s 总睡眠），期间每次重试产生无法回收的半关闭连接，撑爆 httpx 连接池。

### 鉴别特征

日志模式与此前的"慢代理"不同：
```
18:21:21  RemoteProtocolError: Server disconnected    ← 代理挂了
18:21:21  attempt 1/10, reconnecting in 5s            ← 旧退避
18:21:29  attempt 2/10, reconnecting in 10s
18:21:39  attempt 3/10, reconnecting in 20s
...                                                    ← 重试期间无 pool occupied
18:26:59  Pool timeout: All connections occupied      ← 3 分钟后才爆池
18:26:59  Network error on send (attempt 1/3), retrying in 1s
```

关键判别：**错误类型是 `RemoteProtocolError`/`ConnectError`**（代理死了），不是 `PoolTimeout`（池满了）。Pool occupied 是继发性症状，出现在 10 次重试耗尽连接池之后。

### 修复方法（与慢代理不同）

慢代理的解决方案是修代理线路（不可 code fix）；代理瞬断的可通过优化适配器退避参数缓解：

**改动位置：** `plugins/platforms/telegram/adapter.py` → `_handle_polling_network_error()`

```python
# 旧参数
BASE_DELAY = 5     # 第一次等 5s
MAX_DELAY = 60     # 上限 60s
delay = min(BASE_DELAY * (2 ** (attempt - 1)), MAX_DELAY)
# 序列：5, 10, 20, 40, 60, 60, 60, 60, 60, 60 = 435s 总睡眠

# 新参数 (aggressive)
BASE_DELAY = 1     # 第一次立即重试
MAX_DELAY = 16     # 上限 16s
delay = 0 if attempt == 1 else min(BASE_DELAY * (2 ** (attempt - 2)), MAX_DELAY)
# 序列：0, 1, 2, 4, 8, 16, 16, 16, 16, 16 = 95s 总睡眠
```

**验证方法：** 手动 kill xray 进程 → 观察 gateway.log 中的退避序列 → 确认 pool occupied 不出现

```bash
# 1. 找 xray PID
XRAY_PID=$(lsof -i :10808 -sTCP:LISTEN | awk 'NR==2{print $2}')
# 2. kill
kill $XRAY_PID
# 3. 等 10s 后观察
tail -20 ~/.hermes/logs/gateway.log | grep -E "network error.*attempt|reconnect"
# 4. 恢复
/Users/macos/Library/Application\ Support/v2rayN/bin/xray/xray run -c config.json
# 5. 检查 pool occupied
grep -c "pool.*occupied\|Pool timeout" ~/.hermes/logs/gateway.log
```

### 注意事项

- **不要调大 pool size**（`max_connections` 已经是 512，足够）。根因是重试风暴占满连接，不是容量不够。
- **不要改 keepalive_expiry**（当前 2.0 秒已非常激进）。风暴中的连接不是 keepalive 管理的（处于 half-closed 状态）。
- **本修复不影响** 慢代理模式 — 当代理持续慢时退避再快也没用，pool occupied 依然会出现。

## 相关日志片段示例
