# Self-Heal Cron Pattern (no_agent + Service Check)

Concrete implementation of a watchdog cron job that checks and restarts services without LLM overhead. Runs every 5 minutes via `no_agent=True`.

## Architecture

```
cron job (every 5m, no_agent=True)
  └─→ ~/.hermes/scripts/self_heal.py
        ├── check Browser-BC   (restart if down)
        ├── check OpenBridge   (restart if down)
        ├── check Session size (POST /compact if >120K tokens)
        ├── check 金同学 ADB   (adb reconnect if disconnected)
        ├── check 火同学 ping  (log only — needs physical access)
        └── check 水同学 ping  (log only — may be offline)
```

## Script pattern

```python
#!/usr/bin/env python3
"""Self-healing watchdog — runs every 5 minutes, no agent."""

import os, subprocess, re, time

def run(cmd, timeout=10):
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return r.returncode, r.stdout.strip(), r.stderr.strip()
    except subprocess.TimeoutExpired:
        return -1, "", "timeout"

def check_service(name, check_cmd, start_cmd):
    rc, out, _ = run(check_cmd)
    count = int(out.strip())
    if count == 0:
        print(f"[{name}] ❌ down, restarting...")
        run(start_cmd)
        time.sleep(3)
        rc2, out2, _ = run(check_cmd)
        print(f"[{name}] ✅ restarted" if int(out2.strip()) > 0 else f"[{name}] ❌ restart failed")
    else:
        print(f"[{name}] ✅ ok")

# Service checks
check_service("Browser-BC",
    "ps aux | grep 'server.py' | grep -v grep | wc -l",
    "cd ~/Browser-BC && nohup python3 server/server.py > /dev/null 2>&1 &")

check_service("OpenBridge",
    "ps aux | grep 'openbridge.*daemon' | grep -v grep | wc -l",
    "cd ~/.openbridge/repo && node packages/daemon/dist/cli/index.js serve > /dev/null 2>&1 &")
```

## Session Hygiene Check

When a gateway-compressed session still exceeds 120K tokens, the gateway's own hygiene can't always fix it (no session_db on the hygiene agent). A cron-based fallback:

```python
gw_log = os.path.expanduser("~/.hermes/logs/gateway.log")
if os.path.exists(gw_log):
    with open(gw_log) as f:
        lines = f.readlines()
    for line in lines[-100:]:
        if "hygiene" in line.lower() and "tokens" in line:
            import re
            m = re.search(r'(\d+)[,]?(\d*) tokens', line)
            if m:
                tokens = int(m.group(1) + (m.group(2) or ""))
                if tokens > 120000:
                    print(f"⚠️ Session at {tokens:,} tokens → triggering compact")
                    subprocess.run(
                        "curl -s -X POST http://127.0.0.1:8642/api/sessions/compact "
                        "-H 'Content-Type: application/json' -d '{}' > /dev/null 2>&1",
                        shell=True)
```

## Cron Creation

```bash
hermes cron create --schedule "every 5m" --name self-heal \
  --deliver local --no-agent --script self_heal.py
```

## Pitfalls

- **Gateway lifecycle commands are blocked** (#30719): cron jobs cannot contain `launchctl kickstart/start/stop`. The gateway is managed by launchd (`KeepAlive=true`) — don't try to restart it from a cron job.
- **no_agent mode means no LLM**: the script must be fully deterministic. No decisions, no analysis — just check + restart + log.
- **deliver=local**: output goes to file, not the user's chat. Use this for routine checks so the user isn't spammed.
- **self-heal scripts can mask problems**: a script that auto-restarts a crashing service every 5 minutes will keep the service "up" on paper while it crashes repeatedly. Add a crash counter or alert on rapid restart cycles (e.g., `if count > 5 restarts in 30 min: switch deliver to origin`).
