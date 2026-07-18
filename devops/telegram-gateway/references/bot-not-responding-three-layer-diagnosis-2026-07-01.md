# 三步诊断法：机器人"不回话"的精确根因定位

## 背景

用户多次反馈"很多时候不回话"（土同学 Telegram bot）。之前的旧诊断假设是"压缩阻塞主 event loop"，但被后续代码验证推翻。本参考记录了正确的三阶段诊断法。

## 诊断流程

收到"不回话"报告时，按以下层次逐一排查。**每一层必须先排除才能进入下一层。**

### 第1层：是否 event loop 被同步阻塞？（快速排除）

**检查点**：`run_conversation` 是否已经跑在线程池里。

**代码验证**：`gateway/run.py` 中，`_run_agent_inner` 定义 `run_sync()` 闭包（L16112-L17184），通过 `self._run_in_executor_with_context(run_sync)` 调用（L17437-17438）。`run_sync()` 内部包含 `agent.run_conversation()` 调用（L16942）。

**API Server 路径**：`api_server.py:3823` 同样用 `loop.run_in_executor(None, _run)` 包裹了 `run_conversation`。

**本环境结论**：✅ 已在线程池隔离。**排除。**

**重要**：不要只看 L16942 一行就推断"这是在 async 函数里直接同步调用"——要追溯完整的闭包和外层调用链。`run_sync()` = 线程池边界。

### 第2层：线程池是否被打满？（10-worker 池）

**检查点**：压缩/对话高峰时有多少会话同时活跃。

**验证方法**：从 `agent.log` 提取压缩开始/结束时间戳，按分钟计算并发 session 数：

```bash
# 简易版 — 检查高峰期并发
grep "context compression" ~/.hermes/logs/agent.log | \
  awk '{print $1,$2,$(NF-1),$NF}' | \
  head -50
```

**本环境数据**（全时段扫描）：
- 最大并发：3 sessions（peak 时段 13:25 和 15:55）
- 线程池配置：`ThreadPoolExecutor(max_workers=10)`
- 结论：**最高只用 3/10 = 30%**。排除。

### 第3层：HTTP 连接池是否耗尽？（Telegram httpx pool）

这是真正的根因。**查到这一层时，要分辨是偶发还是系统性问题。**

**症状**：`gateway.log` 中出现 51 次以上 `"Pool timeout: All connections in the connection pool are occupied"`。

**触发链（本环境实测）**：

```
xray 代理 (127.0.0.1:10808) 瞬断
  → Polling heartbeat probe failed（gateway.log 见 empty error）
  → PTB 自动重试 1/10, 2/10, ..., 10/10
  → 重连风暴产生大量半关闭连接 (CLOSE_WAIT)
  → httpx 连接池被占满 → "all connections are occupied"
  → gateway 既收不到新消息也发不出去 → "不回话"
  → 10 次耗尽 → gateway 重启 Telegram 适配器
  → 重启期间 (30-60s) 全部消息丢失
```

**本环境数据**：
- `"connection pool are occupied"` 总出现次数：**51 次**
- 导致 Telegram 适配器完全重启的次数：**4 次**（5 小时内）
- 每次重启造成的"不回话"时间：**30-77 秒**
- Pool timeout 与压缩高耗时间高度相关（但不因果）：8 次 timeout 落在 920s 压缩窗口内，15 次在 744s 窗口内，4 次在 555s 窗口内

**诊断命令**：

```bash
# 1. 检查 pool timeout 总数
grep -c "connection pool are occupied" ~/.hermes/logs/gateway.log

# 2. 检查是否触发了 gateway 重启
grep "Restarting gateway" ~/.hermes/logs/gateway.log

# 3. 检查压缩和 timeout 的时间相关性
# 先找 agent.log 中压缩事件，再查 gateway.log 中 pool timeout 是否落在同一窗口
grep "connection pool" ~/.hermes/logs/gateway.log | awk '{print $1,$2}' | head -5
grep "context compression started" ~/.hermes/logs/agent.log | awk '{print $1,$2}' | head -5

# 4. 检查代理健康
grep "Proxy detected\|Proxy\|heartbeat probe failed" ~/.hermes/logs/gateway.log | tail -10
```

## 关键经验

1. **不要过早下结论**。旧的"压缩阻塞 event loop"假设完全错误——代码确实已在线程池中隔离。表面症状（压缩期间不回话）有不同机制（HTTP 连接池耗尽）。
2. **三层诊断的顺序是固定的**：event loop → 线程池 → HTTP 连接池。每一层都需要实测数据排除才能进入下一层。
3. **xray 代理是单点故障**。所有流量（Telegram API、LLM 压缩、cron 任务）共同经过 `127.0.0.1:10808`。代理压力大或瞬断时，Telegram 连接池最先出问题。压缩只是加剧者，不是根因。
4. **压缩不阻塞 event loop，但可能加剧连接池压力**。压缩调用会经过同一个 xray 代理发出大量 HTTP 请求到 LLM API，增加代理负担。如果代理本身不稳定，这些请求可能触发更频繁的连接池耗尽。
5. **最终恢复依赖 gateway 重启**。Telegram 适配器在 10 次失败后触发 `Restarting gateway`，然后通过 `_drain_polling_connections` + 重新初始化 httpx client 恢复。这个重启本身意味着 30-60s 不可用。

## 遗留疑点

- xray 代理瞬断的根因是什么？（超出 gateway 日志范围，需要 xray 端日志）
- 压缩期间并发 LLM 调用是否显著增加了 xray 代理负载？（需要代理端连接计数）
- `_send_path_degraded` boolean flag 的耦合模式是否在后续版本中修复？（见核心参考：dual-pool analysis）
