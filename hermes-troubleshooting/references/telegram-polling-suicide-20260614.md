# Session Reference: Telegram Polling Suicide Chain (2026-06-14)

**Date:** 2026-06-14
**Bot:** @sir_chan_bot (土, id 8743908333)
**Chat ID:** 780486548 (DM with angelife tse)
**Proxy in use:** http://127.0.0.1:10808 (auto-detected by httpx)

## Symptom User Reported

"你这边消息能过去 那边消息过不来啥意思" — outbound from me works, inbound from Telegram doesn't reach me.

## What Actually Happened

A 3-stage failure chain that surfaced as "messages don't arrive":

### Stage A — fd exhaustion (already documented in SKILL.md)
- `OSError: [Errno 24] Too many open files` in gateway log on session tmpfiles + kanban db lock + channel_directory tmp
- Cause: `launchctl maxfiles soft=256` for GUI LaunchAgents; 6+ CLOSE_WAIT sockets accumulated from prior httpx→proxy→telegram long polls
- This is fixed in SKILL.md (SoftResourceLimits in plist → 65536).

### Stage B — Telegram polling conflict (the new lesson)
- After the fix to Stage A, the NEW gateway process started polling but Telegram still held the OLD session's getUpdates connection for ~5 minutes
- Gateway retried 5 times (30s/40s/50s/60s = 180s total, well under the 5min Telegram expiry), gave up
- Cascade error: `Telegram polling could not recover after 5 retries (200s total wait) ... ` followed by `No connected messaging platforms remain. Shutting down gateway cleanly.`
- Exit code 0.

### Stage C — launchd didn't restart on clean exit (the trap)
- `KeepAlive.SuccessfulExit: false` in plist means exit 0 = no restart
- `log show --predicate 'process=="launchd"' --last 5m | grep hermes` showed `exited due to exit(0) ... service state: not running`
- Result: 6-minute silent outage (14:30 → 14:36) until I manually `launchctl bootstrap`

## User's Diagnostic Misdirection

User's complaint ("you can send, I can't") is NOT an asymmetric-communication
problem. The two scenarios look identical to the user but have different fixes:
- If outbound broken → token / proxy / network (this session, briefly)
- If inbound broken → polling / fd / launchd KeepAlive

Always check gateway log FIRST, not the user's mental model.

## Diagnostic Recipe Used (and What Worked)

```bash
# 1. Is the gateway even alive?
pgrep -fl "hermes_cli.main.*gateway"          # returned empty → Stage C confirmed

# 2. Why didn't launchd restart it?
log show --predicate 'process=="launchd"' --last 5m | grep hermes

# 3. Can Telegram even be reached RIGHT NOW? (proxy-aware!)
curl -sS -x http://127.0.0.1:10808 \
  https://api.telegram.org/bot$TOK/getMe

# 4. Are updates stuck on Telegram's side?
curl -sS -x http://127.0.0.1:10808 \
  https://api.telegram.org/bot$TOK/getWebhookInfo
# → url="", pending_update_count=0 → no stale messages

# 5. Is the gateway process actually using the proxy?
PID=$(pgrep -f "hermes_cli.main.*gateway" | head -1)
lsof -p $PID | grep -E "TCP.*ESTAB" | grep -v IPv6
# → Confirm at least one connection to 127.0.0.1:10808
```

This sequence took ~5 minutes to converge on the right diagnosis because I
initially tried `curl` without `-x` and got a false negative ("network fine")
that contradicted the gateway log. **Always start with proxy-aware commands.**

## Fixes Applied

1. `~/Library/LaunchAgents/ai.hermes.gateway.plist`:
   - Added `<key>SoftResourceLimits</key><dict><key>NumberOfFiles</key><integer>65536</integer></dict>` (Stage A)
   - Replaced `KeepAlive.{SuccessfulExit: false}` with `KeepAlive: true`
   - Added `<key>ThrottleInterval</key><integer>10</integer>` (Stage C)

2. Manually bootstrapped: `launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/ai.hermes.gateway.plist`

3. Verified recovery: `gateway.log` shows `Connected to Telegram (polling mode)` at 14:36:44 after the bootstrap.

## Takeaways Persisted in Skill

- Telegram polling conflicts can be triggered by fd exhaustion on the proxy chain,
  not just by token contention. Always netstat `-p tcp | grep <pid>` to count
  CLOSE_WAIT before declaring "token problem".
- The existing `scripts/telegram-gateway-diag.py` uses urllib which bypasses
  proxies — useless on this user's setup. Added
  `scripts/telegram-gateway-diag-proxied.py` as the canonical entry point.
- Don't trust `getMe` from a naive shell call. Pass `-x http://127.0.0.1:10808`
  (or whichever proxy is in `~/.hermes/.env` under `TELEGRAM_PROXY` / `HTTPS_PROXY`).
