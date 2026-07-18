# Cron Watchdog Pattern — Keep Gateway Alive Without launchd

## When to use

- Gateway runs inside Termux (Android) — no launchd/systemd
- Gateway runs in Docker but s6 supervision is unreliable
- You want a lightweight "check + restart" loop without a full init system

## How it works

1. A **no_agent=True script** is placed at `~/.hermes/scripts/` on the Mac
2. A **Hermes cron job** runs the script every N minutes
3. The script uses ADB (or any check mechanism) to verify the gateway is alive
4. If dead, the script restarts it; if alive, it reports "OK" (silent, no output)

## The Script

Place at `~/.hermes/scripts/phone-gateway-watchdog.sh`:

```bash
#!/bin/bash
# Check if phone gateway is alive. If dead, restart via ADB.
PHONE="8a765553"
HERMES_DIR="/data/data/com.termux/files/home/.hermes"

ALIVE=$(adb -s "$PHONE" shell "run-as com.termux sh -c 'pgrep -f \"hermes gateway run\"' 2>/dev/null")

if [ -z "$ALIVE" ]; then
    echo "[watchdog] $(date) Gateway not running. Restarting..."
    adb -s "$PHONE" shell "run-as com.termux sh -c '
        cd $HERMES_DIR
        set -a
        . ./.env 2>/dev/null
        set +a
        nohup ./hermes-agent/venv/bin/hermes gateway run >> ./logs/gateway.log 2>&1 &
        echo \"Restarted: PID \$!\"
    '"
else
    # Silent when alive — no output = no alert
    :
fi
```

Note: The script produces output ONLY when it restarts. Empty stdout means "all good" — the cron scheduler stays silent.

## Cron Job Setup

```bash
hermes cron create \
  --name "phone-gateway-watchdog" \
  --schedule "*/10 * * * *" \
  --script phone-gateway-watchdog.sh \
  --no-agent
```

- `--no-agent`: skip the LLM, just run the script and deliver stdout
- `--script`: the script name in ~/.hermes/scripts/
- Schedule: `*/10 * * * *` = every 10 minutes
- `repeat` defaults to "forever" for recurring schedules
- `deliver` stays as default ("local" = no delivery) because an alive gateway is silent

## Verification

```bash
# Check next run time
hermes cron list | grep watchdog

# Check last run status
hermes cron list | grep watchdog
# last_status: "ok" means script ran successfully (may be silent — that's OK)
```

## Pitfalls

- **`repeat: once` trap**: The `once in 10m` human-friendly schedule format may result in `repeat: once` (one-shot). Always use cron syntax (`*/10 * * * *`) for recurring schedules. Verify `repeat: forever` in the cron job output.
- **ADB device enumeration**: If multiple ADB devices are attached, the script MUST use `adb -s <serial>`. Use `adb devices` to list available serials.
- **Script writes to stderr**: The script's output is what the cron scheduler delivers. If the script writes to stderr, Hermes may interpret it as a failure. Keep error handling inside the script.
- **PPID=1**: A nohup'd gateway has parent PID 1 (init), meaning it outlives the ADB session and the parent shell. This is the desired behaviour for background persistence.
