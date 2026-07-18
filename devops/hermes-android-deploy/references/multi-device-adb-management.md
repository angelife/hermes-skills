# Multi-Device ADB Management (Hermes Android Chroot)

## The Device Identification Problem

When managing multiple Android Hermes gateways via ADB, the **biggest pitfall is confusing which ADB serial belongs to which device/role**.

In this installation, two Android phones (Mi6/水同学 and Mi8/金同学) are managed via ADB. ADB serials are opaque (`ca00a222`, `192.168.1.26:5555`) and don't tell you which device is which.

### Wrong: assuming you can remember the mapping

The agent will naturally form a mental model like "ca00a222 = Mi8" — but this is often **wrong** and you'll discover the error only after writing configs/soul files to the wrong device and seeing contradictory output.

### Correct: read `bot_token` from chroot config.yaml

The definitive way to identify a device:

```bash
adb -s <SERIAL> shell su 0 -c "chroot /data/local/tmp/chroot/debian /bin/cat /root/.hermes/config.yaml | /bin/head -20"
```

Then match the `bot_token:` value against your token inventory:

| Token (prefix) | Bot | Device | Element |
|---------------|-----|--------|---------|
| `8743263149:` | `@masterchan19840907_bot` | Mi6 | 水 (Water) |
| `8858037161:` | `@peterchan90_bot` | Mi8 | 金 (Metal) |

**Do this BEFORE writing any files.** Cross-reference every time you switch devices.

### Secondary identification signals

- `model.default` value (Mi6 uses `agnes-1.5-flash`, Mi8 uses `agnes-2.0-flash`)
- System time (`date` output — should be current)
- `tail gateway.log` for startup timestamps

## Comprehensive Health Check Pattern

For a full health check of any chroot Hermes gateway, run these probes:

```bash
# 1. System time
adb -s <SERIAL> shell su 0 -c "chroot /data/local/tmp/chroot/debian /bin/date"

# 2. Gateway process running
adb -s <SERIAL> shell su 0 -c "chroot /data/local/tmp/chroot/debian /bin/ps aux" | grep hermes

# 3. SOUL.md identity (first 3 lines)
adb -s <SERIAL> shell su 0 -c "chroot /data/local/tmp/chroot/debian /bin/head -3 /root/.hermes/SOUL.md"

# 4. Recent gateway log (any errors?)
adb -s <SERIAL> shell su 0 -c "chroot /data/local/tmp/chroot/debian /bin/tail -30 /root/.hermes/logs/gateway.log"

# 5. Model working? (last response record)
adb -s <SERIAL> shell su 0 -c "chroot /data/local/tmp/chroot/debian /bin/grep 'response ready' /root/.hermes/logs/gateway.log"

# 6. 401/403 errors?
adb -s <SERIAL> shell su 0 -c "chroot /data/local/tmp/chroot/debian /bin/grep -E '401|403|5[0-9][0-9]' /root/.hermes/logs/agent.log"

# 7. Memory
adb -s <SERIAL> shell su 0 -c "chroot /data/local/tmp/chroot/debian /bin/free -m"

# 8. Disk
adb -s <SERIAL> shell su 0 -c "chroot /data/local/tmp/chroot/debian /bin/df -h /"
```

**Verification hierarchy**:
1. `process running` ≠ `bot working` (known discipline from diagnostic-discipline.md)
2. `no 401 errors` ≠ `model responding` (check gateway.log for actual `response ready` entries)
3. `response ready` log ≠ `Telegram reply delivered` (check actual Telegram chat)

## Multi-Line Command Limitation in Chroot

Inside nested `adb shell su 0 -c "chroot ... /bin/bash -c '...'"`, multi-line scripts with `&&` and pipes often fail because the inner `-c` receives truncated input. The shell's `-c` flag only takes the first line of multi-line heredocs.

### Symptoms

```bash
adb -s <SERIAL> shell su 0 -c "chroot /data/local/tmp/chroot/debian /bin/bash -c '
echo first
echo second
echo third
'"
# Output: only "first", rest is lost or shell error
```

### Fix: write a temp script, then execute

```bash
# Build script locally
cat > /tmp/check_all.sh << 'SCRIPT'
echo "=== time ===" && /bin/date
echo "=== gateway ===" && /bin/ps aux | /bin/grep hermes
echo "=== memory ===" && /bin/free -m
SCRIPT

# Push to device
adb push /tmp/check_all.sh /data/local/tmp/

# Execute inside chroot (2-step: copy then run)
adb shell su 0 -c "cp /data/local/tmp/check_all.sh /data/local/tmp/chroot/debian/tmp/ \
  && chroot /data/local/tmp/chroot/debian /bin/bash /tmp/check_all.sh"
```

### Alternative: Python inside chroot for complex logic

When you need field extraction, URL requests, or JSON parsing, write a standalone Python script, push via ADB, then execute:

```bash
# This bypasses all shell nesting issues
adb push /tmp/probe.py /data/local/tmp/
adb shell su 0 -c "cp /data/local/tmp/probe.py /data/local/tmp/chroot/debian/tmp/ \
  && chroot /data/local/tmp/chroot/debian /usr/bin/python3 /tmp/probe.py"
```

## Gateway Log Anatomy

Typical healthy gateway log looks like:

```
2026-07-07 10:19:49,173 INFO hermes... [Telegram] set_my_commands OK for scope BotCommandScopeAllPrivateChats (60 cmds)
2026-07-07 10:19:49,173 INFO hermes... [Telegram] set_my_commands OK for scope BotCommandScopeAllGroupChats (60 cmds)
2026-07-07 10:19:53,022 INFO gateway.run: kanban dispatcher: embedded in gateway (interval=60.0s)
2026-07-07 10:23:22,013 INFO ... Lazy-registered 60 commands for forum chat -1003926068725
2026-07-07 10:23:22,207 INFO ... Flushing text batch agent:main:telegram:group:-1003926068725:6832
2026-07-07 10:23:22,302 INFO gateway.run: inbound message: platform=telegram user=... msg='...'
2026-07-07 10:24:58,432 INFO gateway.run: response ready: platform=telegram chat=-1003926068725 time=96.1s api_calls=1 response=478 chars
2026-07-07 10:24:58,758 INFO ... Sending response (478 chars) to -1003926068725
```

**Red flags**:
- `Connection error` repeated — proxy/network issue
- `401 Unauthorized` — auth problem (check config.yaml `api_key` + `set -a` in startup)
- `Conflict: terminated by other getUpdates request` — dual instance (missing `--replace` flag)
- `certificate verify failed` — system time issue (check `date`)

## Device-Specific Quirks

| Device | Time zone | Known issue | 
|--------|-----------|-------------|
| Mi6 (ca00a222) | CST (UTC+8) | Time may drift; check with `date` periodically |
| Mi8 (192.168.1.26:5555) | UTC | Default timezone may be UTC not CST; check with `date` vs `date -u` |
