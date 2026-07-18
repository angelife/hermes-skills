# launchd Runs Count as Crash-Loop Diagnostic (2026-06-23)

## Session Context

User asked if the Telegram bot was up. Initial response was "没跑" (not running), but the
gateway WAS running — PID 72406, connected to Telegram, since 11:00 AM. The user then
asked to "solve the auto-start problem because every time I type a command you start."

## Key Diagnostic Findings

### launchd `runs` Count

```bash
launchctl print gui/$(id -u)/ai.hermes.gateway | grep "runs"
# → runs = 7
```

This means launchd launched the gateway 7 times total — 6 restarts (crashes/kills) + 1
current running instance. Quick way to see if a launchd service is in a crash loop without
grepping logs.

### LastExitStatus = 15 (SIGTERM)

```bash
launchctl list ai.hermes.gateway | grep LastExitStatus
# → "LastExitStatus" = 15
```

Exit 15 = SIGTERM. This is the signal sent by `--replace` when a new gateway instance
replaces the old one, OR by `kill <PID>`. Not necessarily a crash — could be intentional
restart. Compare against log timestamps.

### Gateway Running with 1961 PoolTimeout Errors

```bash
grep -c "Pool timeout" ~/.hermes/logs/gateway.error.log
# → 1961
```

The existing skill treats PoolTimeout as a step toward `telegram_polling_conflict` →
gateway death. But 1961 PoolTimeouts in one session with the gateway still running shows
these are **outbound** PoolTimeouts (failed `send_message`) — **not** inbound polling
PoolTimeouts (which would kill the gateway).

Distinction:
- **Outbound PoolTimeout** → `send_message` fails → message lost, gateway survives
- **Inbound/polling PoolTimeout** → `getUpdates` fails for 5 consecutive retries → fatal
- Check gateway.log for `Fatal telegram adapter error (telegram_polling_conflict)` to
  distinguish; if absent, the PoolTimeouts are outbound-only

### Implication for Auto-Start

launchd was already correctly configured:
- `KeepAlive: true` (not the default `SuccessfulExit: false`)
- `SoftResourceLimits.NumberOfFiles: 65536`
- `ThrottleInterval: 10`

Despite these fixes, the gateway still restarted 6 times. The PoolTimeout root cause
is persistent (proxy, network, or Telegram API timeout pattern) and the existing fixes
didn't prevent it — they only prevented permanent death.

## Commands Used

```bash
# Check launchd service status
launchctl list ai.hermes.gateway
launchctl print gui/$(id -u)/ai.hermes.gateway  # runs, LastExitStatus, environment

# Check gateway process details
ps -o lstart,pid,command -p <PID>  # when the process actually started

# Quick error frequency
grep -c "Pool timeout" ~/.hermes/logs/gateway.error.log

# Log size (191K lines in error.log vs 6K in gateway.log = 30:1 noise ratio)
wc -l ~/.hermes/logs/gateway.error.log ~/.hermes/logs/gateway.log
```
