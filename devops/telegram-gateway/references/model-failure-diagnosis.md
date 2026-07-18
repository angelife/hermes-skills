# Upstream Model Failure Diagnosis

## Scenario
Telegram bot is connected (shows "Connected to Telegram") and receives inbound messages but does not respond.

## Root Cause Chain
proxy (127.0.0.1:10808) → httpx connection pool hang → poll heartbeat timeout → gateway appears dead
OR
gateway alive → upstream model API returns 429/400/ConnectionError → fallback chain also dead → bot can't produce responses

## Diagnostic Sequence
```
# 1. Is gateway alive?
launchctl list | grep gateway          # PID > 0 = alive, - = dead
pgrep -f gateway                        # alternative

# 2. Is it connected to Telegram?
tail -20 ~/.hermes/logs/gateway.log | grep -E "Connected|inbound|response"

# 3. Check upstream model errors (most common cause of "no response")
tail -20 ~/.hermes/logs/gateway.error.log | grep -E "429|RateLimit|ConnectionError|BadRequest"

# 4. What model is configured?
grep "default:" ~/.hermes/config.yaml | head -1

# 5. Test the preferred model directly before switching
curl -s --max-time 10 https://opencode.ai/zen/v1/models -H "Authorization: Bearer test"
```

## Fix: Change Gateway Default Model

1. Edit `~/.hermes/config.yaml`:
   ```yaml
   model:
     default: <working-model-name>
   ```

2. Restart gateway (must be full stop+start, not kickstart):
   ```bash
   launchctl stop ai.hermes.gateway
   sleep 2
   launchctl start ai.hermes.gateway
   sleep 15
   ```

3. Verify:
   ```bash
   launchctl list | grep gateway        # should show PID > 0
   tail -5 ~/.hermes/logs/gateway.log   # should show "Connected to Telegram"
   ```

## Pitfalls

- **Do NOT trust historical error logs alone** — a provider that showed 125+ errors 2 hours ago may be working now. Always test live before deciding.
- **Ask or test the user's preferred model first** — if they normally use `deepseek-v4-flash-free`, test that one; don't switch to a different model without evidence the preferred one is actually dead.
- **After changing config.yaml, gateway MUST be restarted** — model changes are read at startup only.
- **High loadavg (>50) can cause launchctl to SIGKILL the new process** — if restart fails with exit code -9 and load is high, wait a few seconds and retry.
- `launchctl kickstart -kp` does NOT reload config; use stop + sleep + start instead.
- **Proxy-induced hang vs. model failure are different symptoms**: proxy hang → heartbeat timeout in gateway.log; model failure → 429/ConnectionError in gateway.error.log.
