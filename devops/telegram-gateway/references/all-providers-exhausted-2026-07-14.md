# All Providers Exhausted — Response Timeout (2026-07-14)

Empirical observation of a distinct silent-bot failure mode.

## Session Summary

User reported Telegram bot not replying (gateway process alive, polling working).

## Diagnostic Evidence

**gateway.log timeline:**
```
23:25:57  inbound message (user sends link)
23:26:38  inbound message ("可以")
23:33:39  inbound message (another link)
23:34:18  inbound message (correction)
23:45:09  inbound message (long standing-goal continuation)
23:45:32  start_polling() timed out — connection pool may be wedged (attempt 1/10)
23:47:04  Fatal telegram adapter error — Restarting gateway
23:47:14  Connected to Telegram (polling mode) — reconnect OK
23:49:51  Send failed: Not connected — trying plain-text fallback  ← 4.5min after reconnect
00:14:53  Send failed: Not connected — trying plain-text fallback  ← 27min after inbound
00:15:23  Send failed: Not connected — trying plain-text fallback  ← another retry
```

**gateway.error.log pattern:**
```
OmniRoute (primary):    429 Rate limit exceeded, oc/deepseek-v4-flash-free
NVIDIA (key 1):         503 ResourceExhausted: Worker local total request limit reached (48/48)
NVIDIA-backup (key 2):  503 ResourceExhausted: All workers are busy, please retry later
NVIDIA-backup-2 (key 3):503 ResourceExhausted: Worker local total request limit reached (48/48)
NVIDIA (key 1) retry 2: 503 ResourceExhausted: Worker local total request limit reached (161/48)
```

**Root cause chain:**
1. OmniRoute free tier model `oc/deepseek-v4-flash-free` rate limited (common at peak hours)
2. Fallback chain tries all 3 NVIDIA keys → all 3 show 48/48 workers fully occupied
3. Each provider gets 3 retries with exponential backoff (2s/5s/10s)
4. Total wall time per intent: ~15-30 minutes of retries
5. By the time a response is generated, Telegram long-polling timeout has expired
6. Gateway auto-restarted at 23:47 but the upstream was still exhausted → restart changed nothing
7. Responses that finally completed hit `Send failed: Not connected` because the polling connection was mid-reconnect

## Fix Applied

Switched default model from `oc/deepseek-v4-flash-free` to `ddgw/gpt-5-mini` (DuckDuckGo free tier, tool_calling supported):

```bash
hermes config set model.default ddgw/gpt-5-mini
launchctl stop ai.hermes.gateway
sleep 3
launchctl start ai.hermes.gateway
```

Gateway reconnected at 01:07:50.

## Key Insight

This failure mode looks like a pool/gateway issue (`Send failed: Not connected`, `Pool timeout: All connections in the connection pool are occupied`) but the root cause is **upstream model exhaustion**, not proxy instability or pool config. The `Send failed: Not connected` is a SECONDARY symptom caused by the 15-30 minute response delay.

**Diagnostic heuristic:** Compare timestamps of last `inbound message` and first `Send failed: Not connected` in gateway.log. If delta > 10 minutes, suspect upstream exhaustion, not gateway/pool issue.