# Telegram Gateway — Dual Pool Architecture & Real-Time Snapshot (2026-07-01)

## Context

Verified during 2026-07-01 session: gateway restarted, then post-restart pool state was observed over 20+ minutes. The user requested a structured root-cause summary suitable for forwarding to a more powerful AI for deeper diagnosis.

## Two Completely Separate Connection Pools

| Pool | Library | Purpose | Observed Behavior | Log Source |
|------|---------|---------|-------------------|------------|
| **aiohttp** | aiohttp.client | SOCKS5 proxy transport (底层代理通道) | Never exceeds 1-2 connections, always healthy | `agent.log` — `connections: ['deque([...])']` lines |
| **httpx** | httpx → httpcore (via PTB HTTPXRequest) | Telegram API calls (getUpdates, sendMessage, editMessageText) | The one that fills up → Pool timeout | `gateway.log` — `Pool timeout: All connections in the connection pool are occupied` |

**Key finding:** aiohttp pool is **never** the bottleneck. All 4,217 Pool timeout errors were httpx. The log dump pattern confirms aiohttp always reports exactly 1 connection.

## Real-Time Pool Snapshot from Logs

The gateway log contains automatic aiohttp pool dumps:

```
connections: ['deque([(<aiohttp.client_proto.ResponseHandler object at 0x2d743dc50>, 185327.666239451)])']
```

**How to read:**
- Number of ResponseHandler objects = live connections in pool
- The float after the comma = timestamp (monotonic clock seconds) when connection was last used
- Only 1 connection visible = pool idle/healthy
- >1 connection visible = concurrent activity
- No dedicated httpx pool dump available from current code — httpx state is internal to PTB's request objects

## Historical Statistics (full log lifetime)

```
Pool timeout (httpx):        4,217 occurrences
SOCKS5-related errors:         599 occurrences
SSL/handshake failures:        220 occurrences
```

Correlation: Pool timeout is the dominant failure mode (~80% of Telegram errors). SOCKS5 errors and SSL failures are less frequent but tend to precede pool timeout bursts.

## Verify Pool Health on a Running Gateway

```bash
# 1. Last state snapshot
cat ~/.hermes/gateway_state.json

# 2. Pool timeout count since last restart
grep -c "Pool timeout" ~/.hermes/logs/gateway.log

# 3. aiohttp pool snapshot (should show 1 connection when idle)
grep "connections:" ~/.hermes/logs/agent.log | tail -3

# 4. httpx pool cannot be directly observed without code instrumentation
#    Proxy: check how many TCP connections to SOCKS5 proxy exist
netstat -an | grep 10808 | grep -c ESTABLISHED
```

## Live Pool Inspection via lsof (2026-07-01 session)

While httpx pool internals aren't directly observable, **OS-level TCP connections** are:

```bash
lsof -p <gateway_pid> -iTCP -sTCP:ESTABLISHED
```

**Observed state 31 minutes after restart** (PID 63416, Telegram only, no concurrent heavy load):

| Target | Count | Expected | Delta |
|--------|-------|----------|-------|
| Telegram API (104.19.149.161) | 11 | 2-3 | +8-9 zombie |
| xray proxy (localhost:10808) | 21 | 2-3 | +18-19 zombie |
| **Total ESTABLISHED** | **~32** | **~3-4** | **~8x overshoot** |

**Interpretation:** In 31 minutes, ~32 connections accumulated when only 2-3 should suffice (1 long-poll + 1-2 send). The excess are zombie connections — httpcore returned them to the pool as "idle" but they're actually dead. Each new request creates a fresh TCP connection instead of reusing a pool slot, because the pool thinks its slots are occupied by "idle" connections that won't respond.

**Rate of accumulation:** ~1 zombie/minute. At this rate, a pool_size=64 fills in ~60 minutes of runtime. This aligns with observed ~1-2 hours between restarts.

**Practical diagnostic:**
```bash
# Quick zombie estimate — if >>3, accumulation is happening
lsof -p <gateway_pid> -iTCP -sTCP:ESTABLISHED | grep -c "104.19.149.161"
lsof -p <gateway_pid> -iTCP -sTCP:ESTABLISHED | grep -c ":10808"
```

## Diagnostic Shortcuts

**When bot receives messages but doesn't reply (like 2026-07-01):**
1. Check `gateway_state.json` → `active_agents > 0` means a session is holding resources
2. Check `grep "Pool timeout" gateway.log | tail -5` → httpx pool full
3. The aiohttp pool (deque lines) will still show 1 connection → definitely httpx-only problem

## Open Questions (for Higher-AI Diagnosis)

1. **Why 64 connections (httpx pool_size) fill up sequentially?** 64 is large for a bot with 1-2 concurrent users. Sequential filling suggests connections are acquired but never returned (connection leak), not a concurrency spike.
2. **Is there an async task that acquires a httpx connection then awaits a long-running upstream model call?** If yes, the connection is held idle during the entire AI response time (~5-30s). Multiple concurrent sessions × slow model = rapid pool exhaustion.
3. **Does PTB's HTTPXRequest maintain its own internal queue/retry?** Pool timeout implies the pool's `max_connections` semaphore is blocking. Understanding whether PTB queues internally or immediately fails would determine if increasing pool_size just delays the same leak.
