# Self-Heal System Setup (2026-07-13)

Deployed a self-healing system for autonomous overnight operation.

## Script

`~/.hermes/scripts/self_heal.py` — Python script that checks all services
and auto-restarts any that are down. No LLM dependency, purely rule-based.

### What it checks:

1. **Browser-BC** (PID check `server.py`) → auto-restart via `nohup python3`
2. **OpenBridge** (PID check `openbridge.*daemon`) → auto-restart via `node`
3. **Session hygiene** (grep gateway.log for tokens > 120K) → POST to `/api/sessions/compact`
4. **火同学** ping 192.168.1.23 → log if unreachable
5. **金同学** ADB 192.168.1.26:5555 → auto-reconnect via `adb connect`
6. **水同学** ping 192.168.1.10 → log if unreachable

### Gateway notes

Gateway is managed by launchd (`ai.hermes.gateway.plist`, `KeepAlive=true`).
The self-heal script does NOT touch the gateway — cron job creation rejected
scripts containing `launchctl kickstart` to prevent restart loops (#30719).

### Cron job

- Name: `self-heal` (job_id: 697260300700)
- Schedule: `every 5m`
- Script: `self_heal.py`
- Mode: `no_agent=True` (no LLM overhead)
- Delivery: `local` (silent — doesn't notify user)

### Known limitations

- 火同学 SSH unreachable on 2026-07-12 night (ping works, SSH port not responding).
  Needs physical access to restart SSH daemon on 192.168.1.23.
- NVIDIA quota exhaustion (ResourceExhausted) is detected but auto-fix is limited
  to fallback provider chain already configured in Hermes.
- Session compression via API may not work if the gateway's hygiene agent is
  misconfigured (observed: "no session_db on the hygiene agent").
