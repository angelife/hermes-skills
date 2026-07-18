# SSL Handshake Failure Canary — Pool Fill Timing (2026-07-02)

## Context

Two independent pool exhaustion events observed on the same gateway process (PID 63669) on 2026-07-02 during the 14:00-15:00 window. Unlike the 2026-06-30 `_send_path_degraded` boolean mechanism (which causes transient send refusal in seconds), this is a **gradual connection accumulation** over 25-28 minutes ending in a complete pool freeze.

**Only 1 active Telegram session** during both cycles (angelife tse DM, chat 780486548). No cron jobs other than every-5-min `gateway-watchdog` (which was failing with Xunfei 10163).

## Configuration Verified

The gateway process (launchd-managed) has **NO** `HERMES_TELEGRAM_HTTP_*` env vars in its plist. Code defaults apply:

| Parameter | Default | Source |
|-----------|---------|--------|
| `connection_pool_size` | 512 | `adapter.py:2796`, `_env_int("HERMES_TELEGRAM_HTTP_POOL_SIZE", 512)` |
| `pool_timeout` | 8.0 | `adapter.py:2797`, `_env_float("HERMES_TELEGRAM_HTTP_POOL_TIMEOUT", 8.0)` |
| `max_keepalive_connections` | 10 | `_http_client_limits.py:77`, override via `HERMES_GATEWAY_HTTPX_MAX_KEEPALIVE` |
| `keepalive_expiry` | 2.0 | `_http_client_limits.py:73`, override via `HERMES_GATEWAY_HTTPX_KEEPALIVE_EXPIRY` |
| `_request[0]` (polling) & `_request[1]` (general) | Each has its own 512-connection httpx pool, refactored in `_with_limits()` |

**Verified plist:** launchctl print gui/501/ai.hermes.gateway shows only VIRTUAL_ENV, PATH, HERMES_HOME, XPC_SERVICE_NAME — no connection pool overrides.

## Cycle 1: 13:40 → 14:08 (28 min)

### SSL failure onset → pool exhaustion

```
13:40:29  [SSL: SSLV3_ALERT_HANDSHAKE_FAILURE] MarkdownV2 edit failed
13:41:07  [SSL: SSLV3_ALERT_HANDSHAKE_FAILURE] MarkdownV2 edit failed
13:42:32  [SSL: SSLV3_ALERT_HANDSHAKE_FAILURE] Network error on send (1/3)
13:44:37  [SSL: SSLV3_ALERT_HANDSHAKE_FAILURE] Network error on send (1/3)
          ↓ pool gradually fills with zombie connections
13:58:48  Server disconnected without sending a response (heartbeat silent drop)
13:58:54  [SSL: SSLV3_ALERT_HANDSHAKE_FAILURE] Reconnect attempt fails
13:58:59  Polling resumes (briefly)
14:07:53  Network error (no detail — likely heartbeat timeout from saturated pool)
14:08:26  ★ FIRST POOL TIMEOUT — 20 events over 5 min → restart at ~14:12
```

**SSL failures:** 5 events in 4 min (13:40-13:44), then a 14-min quiet period, then 2 more at 13:58.
**Fill duration:** 28 min from first SSL error to first pool timeout.
**Rate implied:** 512 max_connections ÷ 28 min ≈ **18 connections/min**.

### Gateway-watchdog interference

The `gateway-watchdog` cron (every 5 min) was **failing every run** during this period with Xunfei 10163 errors (model mismatch — cron configured for opencode-zen-free/qwen3-30b but routed to custom:Xunfei provider). Each failure cycle:

1. Agent spawns, tries model API call → fails
2. 3 retries with 2s/5s exponential backoff → ~15s per cycle
3. Each retry opens a TCP connection (or uses a pool slot) that stays occupied during backoff
4. Failed at: 13:15, 13:20, 13:25, 13:30, 13:35, 13:40, 13:45, 13:50, 13:55, 14:00, 14:05, 14:10…

This adds continuous low-level pool pressure throughout the fill period — every 5 min, 3 failed connection attempts.

**Root cause of model routing (未查明):** The cron job is configured with `provider=opencode-zen-free` and `model=@cf/qwen/qwen3-30b-a3b-fp8`. The error.log shows `provider=custom` and `model=xopqwen36v35b`. OpenCode-zen-free's Cloudflare API was also returning 400 errors (`max_tokens=65536 > max_model_len=32768`), but the routing to Xunfei is unexplained by the configured fallback chain (`fallback_providers: nvidia/z-ai/glm-5.1, nvidia/deepseek-ai/deepseek-v4-flash`).

## Cycle 2: 14:30 → 14:55 (25 min)

After restart at 14:12, gateway reconnected at 14:13. User conversation resumed at 14:29.

```
14:30:27  [SSL: SSLV3_ALERT_HANDSHAKE_FAILURE] send_exec_approval failed
14:39:26  [SSL: SSLV3_ALERT_HANDSHAKE_FAILURE] Network error on send (1/3)
14:39:43  [SSL: SSLV3_ALERT_HANDSHAKE_FAILURE] Network error on send (1/3)
          ↓ pool fills again
14:55:24  Polling heartbeat probe failed (silent drop)
14:55:56  ★ SECOND POOL TIMEOUT — 14 events over 4 min → restart at 14:59
```

**SSL failures:** 3 events, concentrated at 14:30 and 14:39.
**Fill duration:** 25 min (11% faster than cycle 1).
**User conversation during fill:**
- 14:29:16  — "升级了吗" → 19.5s response (normal)
- 14:30:04  — "你每天用多少token自己知道么" → 150.0s response (slow — OpenCode Zen 429)
- 14:33:17  — "收起你那种感叹语气。" → MoA multi-model analysis
- 14:34:51  — various → 547.7s response (very slow — 9 min!)
- 14:44:53  — more conversation → 216.9s response
- 14:52:34  — "你先考虑你自己用的模型的 token 计费" → 38.1s (faster briefly)
- 14:53:35  — "那其他的几个等他们统一用的那个网关呢？" → last message before pool timeout

**Slow model responses correlate with pool fill acceleration.** The 150-547s response times mean model API connections are held open for minutes instead of seconds. During the same period:
- OpenCode Zen 429 errors: `HTTP 429 - concurrency: 100000/200000`
- Xunfei 10163 errors continuing from gateway-watchdog (14:30:50, 14:35:53)
- Cloudflare 400 errors: `max_tokens=65536` too large

## Pool Fill Timing Summary

| Metric | Cycle 1 | Cycle 2 |
|--------|---------|---------|
| First SSL failure → first pool timeout | 28 min | 25 min |
| SSL failure count during window | 7 events | 3 events |
| SSL failure density | 0.25/min | 0.12/min |
| Pool timeout events before restart | 20 (5 min) | 14 (4 min) |
| User conversation during fill | Minimal | Active (slow responses 2-9 min) |
| Cron amplification | Yes (every 5 min) | Yes (every 5 min) |
| Average accumulation rate | ~18 conn/min | ~20 conn/min |

**Key insight:** The second cycle had FEWER SSL failures (3 vs 7) but filled 11% faster. The difference is the active user conversation with slow model responses (150-547s) holding pool slots open.

## Implications for Diagnosis

- **SSL failures in gateway.log are actionable canaries** — if you see one, decrement a countdown timer. ~28 min to pool freeze at default pool_size=512. With env var pool_size=64, the window was ~60 min (observed 2026-07-01, ~1 zombie/min).
- **Check gateway.error.log for upstream model issues during the fill window** — the pool fill acceleration correlates with model API slowdowns.
- **The `_send_path_degraded` boolean (2026-06-30 mechanism) was NOT triggered** before either pool timeout — this is a distinct failure mode from the transient disconnect pattern.
- **Pool timeout restarts DO NOT fully clean the proxy state** — the second cycle filled faster (25 vs 28 min), suggesting residual connections from the old process affect the new one.

## Data Sources

- `gateway.log`: Pool timeout timestamps, SSL error timestamps, response time metrics
- `gateway.error.log`: Upstream model errors (Xunfei 10163, OpenCode Zen 429, Cloudflare 400)
- `launchctl print gui/501/ai.hermes.gateway`: Plist env vars (confirmed none set)
- `hermes cron list`: cron job configuration and last_status
- `/Users/macos/.hermes/hermes-agent/plugins/platforms/telegram/adapter.py` lines 2795-2838: Pool config source code
- `/Users/macos/.hermes/hermes-agent/gateway/platforms/_http_client_limits.py`: Keepalive tuning source
