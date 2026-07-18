# Gateway "Not Connected" Sends — Diagnostic Pattern

## Introduction

When the gateway logs show `Send failed: Not connected` but polling appears to work, this is a **send-path-specific degradation** — not a general network failure.

## Layer Separation

The gateway's Telegram adapter uses two httpx client pools:

| Path | Function | Can work independently? |
|------|----------|----------------------|
| **Polling** | `getUpdates` long-poll (receiving) | ✅ Yes |
| **Send** | `sendMessage`, `editMessageText`, etc. | ✅ Yes |
| **Heartbeat** | periodic `getMe` check | ✅ Yes |

A SOCKS5 TLS handshake failure (`SSLV3_ALERT_HANDSHAKE_FAILURE`) can degrade the **send pool** while leaving polling intact. The adapter marks itself "Not connected" for sends but keeps polling normally.

## Evidence pattern in logs

```
20:34:25  [Telegram] Telegram network error: Server disconnected without sending a response.
20:34:25  [Telegram] reconnecting in 0s.
20:34:30  [Telegram] Telegram polling resumed after network error (attempt 1)
                                          ↑ polling recovered
20:38:22  [Telegram] Send failed: Not connected — trying plain-text fallback
20:38:22  [Telegram] Fallback send also failed: Not connected
                                          ↑ send path still broken
```

Additionally, a newer error variant was observed (2026-07-02):
```
[Telegram] Send failed (attempt 1/2, retrying in 2.7s): send_path_degraded
[Telegram] Send failed (attempt 2/2, retrying in 4.3s): send_path_degraded
[Telegram] Send failed: Not connected — trying plain-text fallback
```

`send_path_degraded` is a distinct state: the adapter's send-path health check has explicitly marked the channel as degraded (not just "connection pool is full"). The retry ladder runs 2 attempts before falling back to "Not connected". This is a stronger signal than pool timeout — it means the adapter's rate-limited retry count on the send path has been exhausted.

Key insight: "polling resumed" ≠ full connectivity. Sends continue failing. Even a full polling reconnect at the Telegram adapter level does NOT reset the send path state — only a gateway restart does.

## Cheapest Diagnostic: `hermes send`

`hermes send` bypasses the gateway entirely — reads credentials from `.env`, calls Telegram API directly via the configured proxy.

```bash
# List available targets
hermes send --list

# Structured test (preferred — returns JSON with message_id)
hermes send --to "telegram:<chat_name_or_id>" "test" --json
```

The `--json` flag returns a structured response including `message_id` (confirms delivery to Telegram server):

```json
{"success": true, "platform": "telegram", "chat_id": "780486548", "message_id": "7569", "mirrored": true}
```

### Interpretation Matrix

| `hermes send` | Gateway sends | Diagnosis | Action |
|-------------|--------------|-----------|--------|
| ✅ sent | ❌ Not connected | **Network/proxy OK.** Problem is gateway's internal adapter state machine. | Restart gateway |
| ❌ fails | ❌ Not connected | **Network/proxy down.** SOCKS5, xray, or TLS problem. | Fix proxy first |
| ✅ sent | ✅ works | Everything fine. No action. | — |

## Fix

Restart gateway via launchctl to reset adapter state + both httpx connection pools:

```bash
launchctl unload ~/Library/LaunchAgents/ai.hermes.gateway.plist
sleep 3
launchctl load ~/Library/LaunchAgents/ai.hermes.gateway.plist
```

## Chronic Recurrence

If the pattern recurs every 30-60 minutes, root cause is **SOCKS5 TLS jitter → httpx connection pool gradual exhaustion** (≈18 dead connections per minute until pool saturates at ~512).

### Chronic fix options (discuss with user)

1. **Switch proxy protocol** — SOCKS5 over HTTPS proxy (CONNECT method) may be more stable than SOCKS5
2. **Tune httpx pool** — increase `connection_pool_size` from 512 to 1024, decrease `keepalive_expiry` to 1.0s, increase `max_keepalive_connections` — delays but doesn't prevent exhaustion
3. **Watchdog sensitivity** — make gateway-watchdog detect this earlier (before pool fully saturates)

## Related: Gateway-Watchdog Cron False Positive

The gateway-watchdog cron can report `status: error` due to a completely unrelated cause:

```
RuntimeError: Context length exceeded (314 tokens). Cannot compress further.
```

This is a **cron prompt size issue**, not a gateway issue. The cron's model (`@cf/qwen/qwen3-30b-a3b-fp8`, 32768 max_tokens) can't fit the accumulated system instructions. The agent never reaches the log-grep logic.

**Diagnostic**: Check cron scheduler errors, not gateway logs:

```bash
grep "cron.*failed" ~/.hermes/logs/errors.log | tail -5
```

**Rule**: When a watchdog cron reports "error" but the gateway process is alive and gateway logs show no recent pool timeouts, check the cron errors.log first.
