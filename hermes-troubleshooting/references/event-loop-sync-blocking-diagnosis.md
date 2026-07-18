# 诊断 Event-Loop 同步阻塞（Hermes Gateway）

## 触发场景

async event loop 上运行的 gateway/agent，在某个操作期间全线卡死——所有平台（Telegram/Discord/Slack）同时无响应。

典型症状：
- 压缩/总结/上下文整理期间 gateway 无法收发任何消息
- 其他会话的消息排队不处理
- 单次操作耗时 20-30s 时整条线卡死

## 诊断链路（四层递进）

### 第 1 层：确认阻塞发生在主 Event Loop

```
# 在调用点插入时间戳日志
import time
logger.warning("BEFORE blocking call: %.3f", time.time())
result = blocking_call()
logger.warning("AFTER blocking call: %.3f", time.time())
```

如果在 `async def` 函数里没有 `await`、没有 `asyncio.to_thread`、没有 `run_in_executor`，那就是直接阻塞 event loop 的。**不要假设 async def 里的 sync 调用会自动跑在 executor 里。**

### 第 2 层：追溯 Sync 调用链入口

找到第一层 sync 调用点：

```
# 从 event loop 入口反向追溯
gateway/run.py → _handle_message_with_agent (async def)
  → _run_agent (async def, await)
    → _run_agent_inner (async def)
      → agent.run_conversation(...)  # ← SYNC DIRECT CALL
```

关键判断：
- 外层函数是 `async def` 还是 `def`？
  - `def`（同步函数）：只有被 `run_in_executor` 包裹时才会脱离 event loop
  - `async def` 但内部直接调了 sync 函数（无 await 包装）：**仍然阻塞 event loop**
- **文档注释不能当依靠**：`"This is run in a thread pool"` 只是说明意图，实际要看 `run_in_executor` 或 `asyncio.to_thread` 是否存在

### 第 3 层：追溯完整调用链到最底层 HTTP 调用

从入口逐级展开到最底层：

```
入口 sync function
  → intermediate sync func
    → deeper sync func
      → call_llm / httpx API call  # 真正的同步 HTTP 请求
```

每层都必须看完整——不要只看入口。

### 第 4 层：找代码库里已有的解耦模式

同个项目里可能有既存的解法。搜索三类模式：

```python
# 模式 A: loop.run_in_executor (async 环境可用)
result = await asyncio.get_running_loop().run_in_executor(
    None, lambda: blocking_func(...))

# 模式 B: daemon thread + join 轮询（sync 环境可用，支持中断）
t = threading.Thread(target=_call, daemon=True)  # _interruptible_api_call 模式
t.start()
while t.is_alive():
    t.join(timeout=0.3)
    if interrupt_requested: ...

# 模式 C: asyncio.to_thread (Py 3.9+, 需 async def 环境)
result = await asyncio.to_thread(blocking_func, ...)
```

优先级：现有模式 > asyncio.to_thread > 自建 thread。

## 改动原则

### Backup 先行
```bash
cp target.py target.py.bak
```

### 改动面最小
只在最外层调用点做线程隔离，**不改下层链**——`compress_context` / `call_llm` 内部不动。

### 验证要求
1. 构造接近阈值的上下文触发压缩
2. 压缩进行中从另一个会话发消息，验证不排队
3. 记录前后 event loop 响应延迟（实测数字，不是估算）

## Hermes Agent 已知阻塞链

```
gateway event loop
  → _handle_message_with_agent          # async def
    → _run_agent                        # async def (await)
      → _run_agent_inner                # async def
        → agent.run_conversation(...)   # SYNC (gateway/run.py:16942)
          → build_turn_context          # sync def (turn_context.py:119)
            → agent._compress_context   # sync (L384-390)
              → compress_context        # sync (conversation_compression.py:314)
                → ContextCompressor().compress  # sync (context_compressor.py:2372)
                  → call_llm             # sync (auxiliary_client.py:5622)
                    → httpx/requests     # 同步 HTTP → 阻塞 event loop
```

### 代码库已有 run_in_executor 先例

`gateway/run.py:10045-10052` 已在 hygiene agent 段使用：

```python
loop = asyncio.get_running_loop()
_compressed, _ = await loop.run_in_executor(
    None,
    lambda: _hyg_agent._compress_context(_hyg_msgs, ""),
)
```

主干路径（preflight compression, L384-390 in turn_context.py）**未使用**此模式。

### _interruptible_api_call 的边界

`chat_completion_helpers.py:154` 用 daemon thread + 300ms join 轮询解救**主 API 调用**，但不覆盖压缩路径。压缩路径是独立调用链，需要自己的线程隔离。
