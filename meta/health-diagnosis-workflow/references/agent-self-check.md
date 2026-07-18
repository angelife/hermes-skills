# Agent Self-Check (自检)

## When to Use This Reference

The user says "你自检一下" / "你自己检查一下有什么问题" / "self-check" — asking the agent to examine its own health, not an external system. The distinction from the main skill: `health-diagnosis-workflow` diagnoses an external target ("is X working?"); this reference is for the agent turning the diagnosis inward.

## Multi-Level Approach

Self-check proceeds in layers, each narrowing the scope. Stop when you have a clear triage.

### Level 1: Agent Core

Check the agent's own configuration layer:

```bash
# Hermes config (provider, api keys, paths)
hermes config show

# Provider availability (the actual model endpoint)
curl -s -m 10 "https://<provider-base>/v1/chat/completions" \
  -H "Content-Type: application/json" \
  -d '{"model":"<current-model>","messages":[{"role":"user","content":"hi"}],"max_tokens":5}'

# Hindsight memory server health
curl -s -m 5 http://<hindsight-addr>:8888/health

# Gateway process
pgrep -fl hermes | head -10

# SOUL.md loaded (check identity anchoring)
head -5 ~/.hermes/SOUL.md

# Cron jobs
hermes cron list
```

### Level 2: Host System

The agent lives on a machine. If the host is unhealthy, the agent is slow or unreliable regardless of its own config.

```bash
# Disk
df -h /

# Memory pressure
vm_stat | head 5                              # macOS
# or: free -h                                 # Linux

# Swap usage
sysctl vm.swapusage                           # macOS

# Uptime + load
uptime

# Top CPU consumers
ps -eo pid,%cpu,%mem,comm -r | head 10

# Top memory consumers
ps -eo pid,%mem,comm -m | head 10

# Process count (warning if >500 on Mac, >300 on Linux)
ps aux | wc -l
```

### Level 3: Dependent Services

Check services the agent depends on (containers, gateways, proxies).

```bash
# Docker container status + resource usage
docker ps --format "table {{.ID}}\t{{.Image}}\t{{.Status}}\t{{.Names}}"
docker stats --no-stream

# OmniRoute or other gateways
curl -s -m 5 http://localhost:<port>/api/status 2>&1 | head -5

# Proxy (if used)
curl -s -m 5 --proxy <proxy-url> https://api.telegram.org/bot<token>/getMe
```

### Level 3.5: Hermes WebUI Dashboard

**2026-07-15 lesson:** The user discovered system issues by visiting the Hermes WebUI (`http://localhost:8787/`) and seeing multiple API endpoints returning 404. Before guessing about root causes of agent behavior issues, **check the WebUI first** — it surfaces frontend-backend mismatches, missing API routes, and SPA errors that agent-level checks won't catch.

Check which API endpoints the frontend expects vs what the backend provides:

```bash
# List available API routes from backend
grep -n "/api/" ~/hermes-webui/api/routes.py | grep def | head -20

# Test critical endpoints directly
for ep in providers tasks memory agent-profiles system spaces; do
  code=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8787/api/$ep)
  echo "/api/$ep -> $code"
done
# 200 = OK, 404 = frontend expects but backend missing
```

### Level 4: Root-Cause Drill-Down

When a process is consuming abnormal resources, trace it to its owner.

```bash
# PID → parent chain (find the app/container that owns the process)
ps -o pid,ppid,comm -p <pid>,<ppid>,<ppid-of-ppid>

# For Docker: the VM is PID 1 under Virtualization.framework
# Trace: high-CPU container → Docker VM → the app inside
docker stats <container-name>

# For unknown macOS daemons (/Applications/*):
cat /Applications/<App>.app/Contents/Info.plist | grep -A2 "CFBundleName\|CFBundleIdentifier"
```

### Level 5: Process Traceback (symptom → root cause)

When a process is pegged at >80% CPU, don't stop at killing it — trace back to what started it and why it stayed there. This prevents recurrence by identifying the config or integration that auto-starts it.

**Full chase pattern:**

1. Identify the top consumer: `ps -eo pid,%cpu,%mem,comm -r | head 5`
2. Get parent PID: `ps -o ppid= -p <pid>` — tells you **who started it**
3. Trace the parent chain: `ps -o pid,ppid,lstart,comm -p <pid>,<parent>,<grandparent>`
4. Check for daemonization (PPID=1): if parent is PID 1 (launchd), the process daemonized itself after fork. The *original* parent is still visible via the MCP/child subprocess that didn't daemonize. Find that subprocess owned by the original parent.
5. Check config/init scripts of the parent app: search for what triggers it (e.g. `inherit_mcp_toolsets` in Hermes config.yaml, MCP server entries)
6. Check macOS diagnostic reports for prior warnings:
   ```bash
   ls -la /Library/Logs/DiagnosticReports/<process-name>_*.diag 2>/dev/null
   ```
   If 3+ reports exist, macOS has been flagging this process for days. It's a known recurrence, not a one-off glitch.

**Real-world example (CuaDriver daemon, 2026-07-08):**

| Step | Action | Finding |
|---|---|---|
| 1 | `ps -r` top consumer | `cua-driver` PID 37941, 114-152% CPU, 0.7% mem |
| 2 | `ps -o ppid=` | PPID=1 (daemonized — original parent lost) |
| 3 | Find MCP subprocess | `cua-driver mcp` PID 33136, PPID=88344 (Hermes gateway) |
| 4 | Check Hermes config | `inherit_mcp_toolsets: true` → computer-use tool enabled → auto-spawns cua-driver |
| 5 | `ps -o lstart= -p 88344` | Hermes started Jul 6 — cua-daemon had been running 2+ days |
| 6 | macOS diag reports | 5 `cua-driver_*.cpu_resource.diag` from Jun 29 to Jul 6 |
| **Root cause** | Hermes MCP integration | computer-use tool auto-launches cua-driver mcp subprocess, which daemonizes to PPID=1 and never exits |

**When you find a daemonized process (PPID=1):**
- The .pid file (often at `~/Library/Caches/<prog>/<prog>.pid`) matches the daemon PID
- The original parent's MCP subprocess survives alongside the daemon
- Killing the daemon alone works — it won't auto-restart unless the parent respawns it
- To prevent recurrence: either (a) remove the parent's trigger config, or (b) disable the parent's integration with that toolset

## Common Findings (with diagnosis)

| Symptom | Likely Cause | Telltale |
|---|---|---|
| Load avg > 8 on Mac, idle < 30% | Docker VM + containers | `ps -r` shows `Virtualization.VirtualMachine` at top |
| One Docker container consuming >100% CPU | Container app stuck in loop / polling | `docker stats` confirms the specific container |
| System swap > 50% used | RAM overcommitted; identify via `ps -m` | `vm.swapusage` shows used / total |
| Unknown daemon with >80% CPU | Abnormally high for idle daemon | Check `Info.plist` for CFBundleIdentifier |
| `hermes config show` OK but provider 404 | `base_url` in config doesn't match API docs | curl the actual `/v1/models` endpoint of that provider |
| Gateway process alive but no Telegram replies | Event loop blocked (see `references/async-blocking-diagnosis.md`) | Timestamp gaps in gateway.log |

## Report Format for This User

When reporting self-check results, structure as:

1. **✅ 正常工作** — the things that are fine (table format)
2. **🔴 问题** — numbered, each with "是什么/根因/建议"
3. **🟡 次要** — notable but not urgent

One-liner summary at the top. The user reads the first sentence to decide if they care about the rest.

## Pitfalls

- [P1] **Don't report "everything is fine" when the host is dying**: agent config can be perfect but the machine can be thrashing. Always check host metrics.
- [P2] **Provider "Not Found" on `/v1/models` doesn't mean broken**: some providers don't expose that endpoint. Test with `/v1/chat/completions` instead for a definitive answer.
- [P3] **Gateway process running ≠ bot responding**: the gateway event loop can be blocked (sync operation) or the connection pool can be exhausted while the process appears healthy.
- [P4] **Don't assume swap usage alone is critical**: token-inference loads are bursty. Correlate with active process list and recent user activity to judge.
