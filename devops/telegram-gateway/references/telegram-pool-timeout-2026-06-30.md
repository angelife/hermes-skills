# Telegram Pool Timeout — Session Log 2026-06-30

Verified findings from troubleshooting bot silence.

## Root Cause (Verified)

**Upstream model 429 → pool exhaustion.** Not SOCKS5吞RST.

Log timeline (2026-06-30):

```
22:42:09 Pool timeout + 6x RateLimitError 429 (upstream AI model, NOT Telegram API)
22:48:35 Polling heartbeat probe failed → reconnect storm
22:48:50–22:54:05 Pool timeout on every send/edit attempt
```

Confirmed: `gateway.error.log` shows RateLimitError 429 from AI provider at same moment pool timeout first appeared.

## What Was NOT Verified

"SOCKS5吞RST" — no tcpdump, no CLOSE_WAIT observation. Plausible mechanism but unconfirmed on this chain. Do not present as fact.

## What WAS Confirmed

1. **146 ESTABLISHED connections to 10808** (netstat). Alone this does not prove dead connections — ESTABLISHED is TCP state, not liveness. Must correlate with pool_timeout log events.

2. **PTB already separates polling and general pools** — `_request[0]` (getUpdates) and `_request[1]` (send/edit) are independent. The cascade observed (send exhaustion → polling reconnect storm) is not from pool sharing but from Bot instance state corruption after prolonged send failure.

3. **Watchdog cron `gateway-watchdog`** had wrong provider `cloudflare-workers-ai` (non-existent). Fixed to `opencode-zen-free/@cf/qwen/qwen3-30b-a3b-fp8`.

## Diagnostic Commands Run

```bash
# 1. Check for dead connections on proxy
netstat -an | grep 10808 | grep -c ESTABLISHED

# 2. Correlate pool timeout with 429 events
grep -i "pool timeout\|429" /Users/macos/.hermes/logs/gateway.log | tail -50

# 3. Check error log (upstream model failures)
tail -30 /Users/macos/.hermes/logs/gateway.error.log

# 4. Verify gateway connected
tail -5 /Users/macos/.hermes/logs/gateway.log
```

## Three Fix Directions (assessed against actual code)

| Direction | Applicable | Reason |
|-----------|-----------|--------|
| 方向一: 429时不占连接retry | ⚠️ Need Hermes layer code review | Gateway uses PTB's httpx; retry logic likely in Hermes agent session loop |
| 方向二: 隔离polling/send池 | ✅ Already done by PTB | `_request[0]` and `_request[1]` already separate |
| 方向三: 断路器/主动退避 | ✅ Cleanest fix | Block new requests for 10-30s after upstream 429, don't queue them |

## Config Values — Provenance Note

Any numeric config values (pool size, keepalive expiry, timeouts) cited in skill must state source. This session's values in SKILL.md were from skill memory, not independently verified on this machine. When updating, label as "推测值，建议验证" rather than "生产验证过".