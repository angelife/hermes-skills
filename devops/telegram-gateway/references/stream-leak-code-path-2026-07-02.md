# TCP Stream Leak on TLS Handshake Failure (2026-07-02)

## Code Path Trace

```
PTB HTTPXRequest.do_request()
  → httpx.AsyncClient.request() → send()
    → _send_single_request()
      → transport.handle_async_request()
        → AsyncConnectionPool.handle_async_request()
          → _assign_requests_to_connections()
          → connection.handle_async_request()
            → AsyncSocks5Connection.handle_async_request()
```

## Key Code (`httpcore/_async/socks_proxy.py`)

```python
async def handle_async_request(self, request):
    async with self._connect_lock:
        if self._connection is None:
            try:
                stream = await connect_tcp(...)           # (1) TCP连xray
                await _init_socks5_connection(...)         # (2) SOCKS5握手
                stream = await stream.start_tls(...)       # (3) ★ TLS握手 ★
                self._connection = AsyncHTTP11Connection(  # (4) 仅正常路径到达
                    ..., stream=stream,
                )
            except Exception as exc:
                self._connect_failed = True                # (5) 设失败标志
                # ⚠️ stream 未关闭，TCP socket 泄漏
                raise exc                                  # (6)
```

## 泄漏点: 第 294-295 行, `raise exc` 前缺少 `await stream.aclose()`

当 TLS 握手失败:
- `stream` (TCP 连接至 xray 127.0.0.1:10808) 在 (1) 建立, (2) SOCKS5 完成
- (3) `start_tls` 抛出 `SSLV3_ALERT_HANDSHAKE_FAILURE`
- (5) `self._connect_failed = True`
- (6) `raise exc` — 但 `stream` 从未被 `aclose()`, **TCP socket 泄漏**

## 池槽 ≠ TCP: 两个不同的释放域

| 资源 | 释放结果 | 原因 |
|---|---|---|
| **httpx 池槽** | ✅ 正确释放 | `AsyncConnectionPool.handle_async_request()` 的 `except BaseException` 处理器调用 `_assign_requests_to_connections()`, 通过 `is_closed()` (返回 True: `_connect_failed=True` 且 `_connection=None`) 将连接从池移除 |
| **到 xray 的 TCP socket** | ❌ 泄漏 | `stream` 对象出作用域但未 `aclose()`, TCP 连接在 xray 端保持 CLOSE_WAIT, Python GC 回收时机不确定 |

## 级联路径: TCP 泄漏 → 池槽被占满

```
xray proxy 不稳 → TLS handshake 失败 → stream 不 aclose, TCP 漏掉
→ xray 积累半开连接
→ xray 处理新连接变慢
→ 每个新连接持池槽更久
→ 512 池槽被慢速连接占满 (~28 分钟)
→ PoolTimeout
```

**实证:** 2026-07-02 两轮周期均印证约 28 分钟从首次 SSL 失败到 PoolTimeout.
- 第一轮: 13:40 SSL 失败 → 14:08 PoolTimeout (28 min)
- 第二轮: 重启后 14:30 SSL 失败 → 14:55 PoolTimeout (25 min)

有且仅有的泄漏根因是 httpcore 代码第 294 行 `except Exception` 块
未关闭 TCP stream. 所有其他异常路径(已建连后 TLS 错误 → `_response_closed → aclose`)
均正确关闭.

## 修复方案

在 `httpcore/_async/socks_proxy.py`, `AsyncSocks5Connection.handle_async_request()`,
第 294 行 `except Exception` 块内, `raise exc` 前添加:

```python
except Exception as exc:
    self._connect_failed = True
    if stream is not None:
        await stream.aclose()
    raise exc
```

注意: `stream` 在 `try` 块中第 231 行赋值 (`connect_tcp` 成功), 所以 `except` 块中
`stream` 已存在. 但 `connect_tcp` 本身也可能抛出异常, 此时 `stream` 未赋值,
需加 `if stream is not None` 保护.
