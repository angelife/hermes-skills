# Restart Loop → NO_PROXY Fix — 2026-07-14

## Pattern

User reported "检查一下telegram机器人 没回复了" three times in ~40 minutes.

| # | Time | Symptom | Action | Result |
|---|------|---------|--------|--------|
| 1 | ~17:36 | Pool timeout, connection pool wedged | Restart gateway via kill + launchctl auto-restart | Bot reconnected, processed 1 message |
| 2 | ~18:14 | Same pool timeout pattern 7 min later | Same restart | Same result |
| 3 | ~18:27 | Same again | Added `NO_PROXY=api.telegram.org,localhost,127.0.0.1` to `.env` + restart | Permanent fix |

## Root Cause

- SOCKS5 proxy at `127.0.0.1:10808` (auto-detected by Gateway via macOS `scutil --proxy`)
- Proxy latency jitter → PTB long-poll heartbeat timeout → `_send_path_degraded = True` → all sends short-circuited
- Restart clears the flag but the proxy itself is still unstable → same failure within ~7 min
- `NO_PROXY=api.telegram.org` bypasses the proxy for Telegram API traffic (direct connection works from this network)

## Diagnostic Logs

Key log excerpt (pool timeout pattern):
```
Pool timeout: All connections in the connection pool are occupied
Polling heartbeat probe failed ()
start_polling() timed out — connection pool may be wedged
10 retries exhausted → Restarting gateway
Reconnected successfully → 7 min later → same cycle
```

## Fix Applied

```
echo "NO_PROXY=api.telegram.org,localhost,127.0.0.1" >> ~/.hermes/.env
```

## Lesson

When pool timeout recurs within minutes of a restart, **do not restart again**. The immediate question is: is the NO_PROXY bypass present? This is a faster path to resolution than repeating the restart cycle.
