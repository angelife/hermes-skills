# Chroot Debugging Session — 2026-07-07

## Devices
- 金 (Mi8): LineageOS 22.2, Hermes v0.18.0, chroot Debian 12 bookworm
- 水 (Mi6): LineageOS 22.1, Hermes v0.18.0, chroot Debian 12 bookworm

## Symptom
Gateway would not start on either Android device. `pgrep -af hermes` returned nothing.
Initial assumption: Hermes config or environment broken.

## Root Cause (Water)
`nohup` was not installed in the chroot environment. Every prior attempt used
`nohup ... &` which silently failed with `/bin/bash: line 1: nohup: command not found`.
The error was invisible because stderr was redirected to a log file that was never read.

## Root Cause (Gold)
Gateway was ACTUALLY running (PID 7277) the whole time, but:
- `pgrep` was not available in chroot
- `ps aux` from host showed the process but was not checked correctly
- `gateway_state.json` was missing because the gateway was started manually
- The `--replace` flag was not used initially, causing "Another gateway instance already running" errors

## Correct Startup Sequence

```bash
# MUST source .env with export flag:
adb -s $DEVICE shell "su 0 -c 'chroot /data/local/tmp/chroot/debian /bin/bash -c \
  \"cd /root/.hermes && set -a && source .env && set +a && \
   /path/to/hermes/venv/bin/hermes gateway run --replace\"'"

# Check status AFTER starting:
adb -s $DEVICE shell "su 0 -c 'chroot /data/local/tmp/chroot/debian /bin/bash -c \
  \"cd /root/.hermes && set -a && source .env && set +a && \
   /path/to/hermes/venv/bin/hermes gateway status\"'"

# Cross-check from host:
adb -s $DEVICE shell "ps -ef | grep -i hermes | grep -v grep"
```

## Key Commands That Work in Minimal Chroot
- `/bin/bash -c "command"` — always available
- `ls` — file listing
- `cat` — read files
- `echo` / `printf` — write output
- `env` — show environment (may be empty if .env not sourced)

## Commands NOT Available
- `nohup` — use `&` or `exec` instead
- `curl` / `wget` — test network from ADB host
- `ping` — same
- `python3` — ditto
- `pgrep` — scan /proc manually: `ls /proc/*/cmdline`
- `ldd` — check dynamic libs from host with `readelf -d`
- `timeout` — use `sleep & kill` pattern
- `ps` — available from host side: `adb shell ps`
