# Hermes Gateway Async 架构参考

## 概述

网关主消息处理循环是 asyncio event loop（`gateway/run.py`），但单次 agent 对话（包括 LLM API 调用、工具执行、上下文压缩）是**同步阻塞**的，运行在**线程池**中。理解两者的边界是诊断"bot 是否卡死"类问题的关键。

## 核心调用链

```
_handle_message_with_agent()          [async, L9584]
  → await self._run_agent()           [async, L10341]
    → await self._run_agent_inner()   [async, L15267]
      → def run_sync()                [sync,  L16112]
          → agent.run_conversation()  [L16942]
            → build_turn_context()    ← 压缩在此发生
      → asyncio.ensure_future(
            self._run_in_executor_with_context(run_sync)
          )                           [L17437-17438]
      → response = await _executor_task
```

**关键层：** `_run_agent_inner` 的 docstring (L15292) 准确声明"在 thread pool 中运行，不阻塞 event loop"——代码确实如此。

## 线程池隔离

`_run_in_executor_with_context()` (L13548):

```python
async def _run_in_executor_with_context(self, func, *args):
    loop = asyncio.get_running_loop()
    ctx = copy_context()                  # 保留 contextvars
    return await loop.run_in_executor(
        self._get_executor(),             # 10-worker, "hermes-gateway"
        ctx.run, func, *args,
    )
```

- Executor: `ThreadPoolExecutor(max_workers=10, thread_name_prefix="hermes-gateway")` (L13570-13574)
- `copy_context()` 保留 contextvars 跨线程

## 回调跨线程安全

所有 agent 回调从 worker 线程桥接回 event loop 的方式：

| 回调 | 位置 | 安全模式 |
|------|------|----------|
| `status_callback` | L16077 | `safe_schedule_threadsafe(coro, loop)` |
| `notice_callback` | L16468 | `safe_schedule_threadsafe(coro, loop)` |
| `event_callback` | L16485 | `safe_schedule_threadsafe(coro, loop)` |
| `stream_delta_callback` | L16259 | `_stream_consumer.on_delta(text)` 设计为跨线程 |
| `progress_callback` | L15510 | `progress_queue.put()` — Queue 线程安全 |

## API Server（REST API）路径

`gateway/platforms/api_server.py` (L3780-3825):

```python
def _run():
    agent = self._create_agent(...)
    result = agent.run_conversation(...)
    return result, usage

return await loop.run_in_executor(None, _run)
```

同样将 `run_conversation` 投递到线程池，不阻塞 event loop。

## 常见诊断陷阱

### ❌ 陷阱："同步函数在 async 函数里调用 → 阻塞 event loop"

这是本参考最核心要预防的误判。有人看到：

```python
async def _run_agent_inner(...):
    ...
    result = agent.run_conversation(...)   # sync def!
```

就断定"run_conversation 阻塞 event loop"。但没看到 `run_conversation` 在 `run_sync()` 闭包内，而 `run_sync()` 被 `_run_in_executor_with_context` 包裹。

### ✅ 正确诊断流程

证明"X 阻塞 event loop"需要**完整追踪到 event loop 级别**：

1. 找到 X 的**函数定义** → `sync def` / `async def`
2. 找到 X 的**调用点** → 看上一层函数
3. 继续向上追踪，直到遇到**async 边界**（`event_loop.run_until_complete` / `await` / `await loop.run_in_executor` / `asyncio.ensure_future`）
4. 如果所有调用路径都经过 `run_in_executor` → X **不阻塞** event loop。阻塞的是线程池线程。

对于 gateway/run.py：

```
agent.run_conversation()         sync
  → run_sync()                   sync closure
    → _run_in_executor_with_context()  await  ← 线程池边界在此
      → _run_agent_inner()       async
        → _run_agent()           async
          → _handle_message_with_agent()  async
```

### 🔍 如何验证是否真的阻塞

在压缩发生期间模拟并发请求：

```python
# 终端 A：触发压缩（大上下文消息）
# 终端 B：curl http://localhost:8080/health 或另一平台发消息
# 如果 B 在 A 压缩完成之前无响应 → 确实阻塞
# 如果 B 在 A 压缩期间正常 → 已在线程池隔离
```

## 文件引用

- `gateway/run.py` L13548-13557: `_run_in_executor_with_context`
- `gateway/run.py` L13559-13576: `_get_executor` (10 worker pool)
- `gateway/run.py` L15267-17438: `_run_agent_inner` → `run_sync` → executor
- `gateway/run.py` L16077-16110: `_status_callback_sync` (thread-safe bridge)
- `gateway/platforms/api_server.py` L3780-3825: API server 线程池隔离
