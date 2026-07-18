# Parallel Cascade Failure: fd → Docker → Proxy (2026-06-22)

## Sequence of Events

1. User: "机器人又罢工了"
2. Gateway state: `retrying`, Telegram connect timed out after 30s
3. **Step 1: fd exhaustion** — `ulimit -n` showed 256, gateway had 200+ FDs
   ```bash
   lsof -p <PID> | wc -l          # 221 (close to 256 limit)
   lsof -p <PID> | awk '{print $NF}' | sort | uniq -c | sort -rn | head -3
   # Result: most FDs were (CLOSED) — stale descriptors
   ```
   Fix: created `/Library/LaunchDaemons/limit.maxfiles.plist` → `sudo launchctl load -w`
   Killed gateway PID → auto-restarted. Telegram connected.

4. **First recurrence** (~5 min later): "机器人又罢工了"
   Gateway was `retrying` again.
   Checks:
   - fd limit now 4096 ✅
   - `docker ps --timeout 3` HUNG (hard timeout)
   - `ps aux | grep "Docker"` showed com.docker.backend alive but unresponsive

   Fix: `killall -9 "Docker Desktop"; killall -9 com.docker.backend; open -a Docker`
   Docker came back after ~15s. Containers auto-restarted.

5. **Second recurrence**: Telegram still `retrying`
   Now the proxy was also degraded. `lsof -i :10808` showed:
   - xray (PID 8286) running, LISTENING
   - 20+ connections in ESTABLISHED (from Chrome, etc.)
   - Gateway→proxy connections all in CLOSED state
   - Gateway log showed: `Proxy detected; passing explicitly to HTTPXRequest: http://127.0.0.1:10808`
   
   The proxy (xray/sing-box managed by v2rayN) was running but couldn't serve
   the gateway. Restarting the gateway alone didn't fix this — the proxy's
   own connection pool was degraded.

   **Fix was not clear.** The session ended before recovery confirmed.

## Root Cause Chain

```
macOS fd limit (256 default)
  └─ gateway process hits fd max
      ├─ httpx pool can't open new connections → Telegram polling times out
      ├─ Docker socket I/O blocks → daemon appears hung
      └─ Gateway→proxy (xray:10808) connections orphaned in CLOSE_WAIT
          └─ proxy connection pool fills with stale entries
              └─ even after gateway restart, proxy can't serve new connections
```

## Diagnostic Fingerprints

| Failure | Signal | Key Command |
|---------|--------|-------------|
| FD exhaustion | lsof count near 256 | `lsof -p <PID> \| wc -l` |
| FD exhaustion | Most entries (CLOSED) | `lsof -p <PID> \| awk '{print $NF}' \| sort \| uniq -c \| sort -rn \| head -5` |
| Docker hung | `docker ps` timeout 3s | `docker ps --timeout 3` |
| Docker hung | Docker Desktop processes alive | `ps aux \| grep -E 'com.docker\\|Docker Desktop' \| grep -v grep` |
| Proxy degraded | Gateway log shows proxy | `grep -i proxy ~/.hermes/logs/gateway.log \| tail -5` |
| Proxy degraded | CLOSED/CLOSE_WAIT on :10808 | `lsof -i :10808 \| grep -v LISTEN \| grep -c 'CLOSED\\|WAIT'` |

## Lessons

- **Fix order matters.** When fd exhaustion is confirmed, also check Docker
  and proxy concurrently — don't wait for the user to report again.
- **Restarting the gateway after fd fix does NOT fix proxy degradation.**
  Proxy (xray/sing-box) must be restarted independently when its connection
  pool is stale.
- **A "connected then retrying" pattern in under 5 minutes is NOT a new problem.**
  It's the next layer of the cascade. Don't restart triage from Step 1.
- **The proxy is invisible in normal operation.** Gateway log just says
  "Connected to Telegram (polling mode)" without mentioning the proxy.
  Only when it fails does the proxy log line appear.
- **Docker Desktop restart also restarts xray/sing-box.** If v2rayN is running
  with "start on launch", Docker restart doesn't touch it. You may need
  to restart v2rayN separately or kill xray PID and let v2rayN respawn it.

## Quick Cascade Recovery (all-in-one)

```bash
# 1. Fix root cause first
sudo launchctl limit maxfiles 4096 unlimited

# 2. Kill all 3 failing systems simultaneously
killall -9 "Docker Desktop" 2>/dev/null
killall -9 com.docker.backend 2>/dev/null
kill $(pgrep -f "hermes_cli.main.*gateway") 2>/dev/null
kill $(lsof -ti :10808 -s | grep LISTEN) 2>/dev/null   # kill xray proxy

# 3. Wait for auto-restarts
sleep 3

# 4. Start Docker (auto-starts containers, may auto-start v2rayN proxy)
open -a Docker

# 5. Wait and verify
for i in $(seq 1 30); do
  state=$(cat ~/.hermes/gateway_state.json 2>/dev/null | python3 -c "import sys,json; print(json.load(sys.stdin).get('platforms',{}).get('telegram',{}).get('state',''))" 2>/dev/null)
  if [ "$state" = "connected" ]; then echo "Gateway OK (${i}s)"; break; fi
  sleep 2
done
```
