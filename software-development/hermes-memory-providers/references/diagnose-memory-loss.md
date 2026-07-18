# Diagnose Memory Loss in Running Hermes Agent

Use this flow when an agent (土/金/木/火/水, or any Hermes instance) reports
losing its shared memory — suddenly can't recall past conversations, answers as
if no context exists.

## Phase 1: Config Check (Surface Layer)

```bash
# 1a. Check memory.provider in config
grep -A5 "^memory:" $HERMES_HOME/config.yaml | grep provider
# Expected: "provider: hindsight"
# Trap:    "provider: ''"   (empty string = not enabled)
# Trap:    "provider: null" (YAML null = same as empty)

# 1b. Check delegation.provider (common side-effect of sed overflow)
grep -A5 "^delegation:" $HERMES_HOME/config.yaml | grep provider
# Expected: "provider: ''"   (must be empty)
# Trap:    "provider: hindsight"  (will break sub-task delegation)

# 1c. Check environment vars
grep HINDSIGHT_API_KEY $HERMES_HOME/.env
grep HINDSIGHT_API_URL $HERMES_HOME/.env
```

## Phase 2: Provider Initialization File

```bash
# Check hindsight/config.json — THIS FILE IS REQUIRED, not optional
ls -la $HERMES_HOME/hindsight/config.json

# If missing: provider loads into memory but is_available() returns False
#               because it can't determine mode/URL/bank_id
#               Defaults to cloud mode + default cloud URL if absent
```

## Phase 3: Process Runtime

```bash
# 3a. Find running gateway PID
ps aux | grep "hermes.*gateway" | grep -v grep

# 3b. Check process environment (verify env vars are actually loaded)
cat /proc/<PID>/environ 2>/dev/null | tr '\0' '\n' | grep -i "hindsight\|HERMES_HOME"

# 3c. Check actual runtime provider status
hermes memory status
# Expected: Provider: hindsight — hindsight ... ← active
# Broken:   Provider: (none — built-in only)
```

## Phase 4: Gateway Logs

```bash
# Check startup timestamp — confirms config was loaded after any fix
tail -20 $HERMES_HOME/logs/gateways/<profile>/current

# Key signals:
# "Started gateway" line → compare timestamp to when config was last edited
# Error/warning lines about hindsight config
```

## Phase 5: Provider Init Code Trace (deep)

When phases 1–4 all look correct but provider is still inactive, trace the
initialization path in the Hermes source:

1. **`agent/agent_init.py` ~L1160-1210** — `MemoryManager.__init__`
   reads `mem_config.get("provider")` from parsed config.

2. **`agent/memory_manager.py` ~L320-383** — `MemoryManager.add_provider()`
   calls `provider.is_available()` — if False, provider is **not stored**.

3. **`plugins/memory/hindsight/__init__.py` ~L671-692** — `is_available()`
   performs an import check. Returns True if hindsight-client can be imported.

4. **`plugins/memory/hindsight/__init__.py` ~L1152-1250** — `initialize()`
   calls `_load_config()` which reads `$HERMES_HOME/hindsight/config.json`.
   If file missing: defaults to `mode=cloud`, `api_url=https://api.hindsight.vectorize.io`
   → connection to local service fails → `is_available()` returns False downstream.

## Phase 6: Fix Verification

After any fix, confirm ALL three layers:

```bash
# Layer A — config correct?
grep -A5 "^memory:" $HERMES_HOME/config.yaml

# Layer B — init file exists?
ls -la $HERMES_HOME/hindsight/config.json

# Layer C — runtime active? (must restart gateway first!)
hermes memory status | grep -i "provider\|hindsight\|active"
```

## Root Cause Quick Reference

| Symptom | Likely Root Cause | Fix |
|---------|-------------------|-----|
| `memory.provider: ''` | Never set, or sed overflow cleared it | `hermes config set memory.provider hindsight` |
| `memory.provider: null` | Config template default | `hermes config set memory.provider hindsight` |
| `hindsight/config.json` missing | New container / upgrade rebuild | Create file with correct mode/URL/bank_id |
| Config correct but runtime broken | Gateway not restarted after fix | Restart gateway (see pitfall #9) |
| `hermes shim` shows inactive, `venv` shows active | Shim-vs-venv env discrepancy | s6 uses venv path; trust that, ignore shim |
| `delegation.provider: hindsight` | sed overflow caught both delegation and memory | Fix delegation block only (see sed pitfall) |

## Docker Container Specifics

| Item | Host Path | Docker Path |
|------|-----------|-------------|
| HERMES_HOME | `~/.hermes/` | `/opt/data/` |
| Hindsight API URL | `http://localhost:8888` | `http://host.docker.internal:8888` |
| `hindsight/config.json` | `~/.hermes/hindsight/config.json` | `/opt/data/hindsight/config.json` |
| Gateway status cmd | `hermes memory status` | `docker exec <name> hermes memory status` |
| Gateway restart cmd | `hermes gateway restart` | `docker exec <name> hermes -p <profile> gateway run --replace` |
| Gateway logs | `~/.hermes/logs/gateways/` | `/opt/data/logs/gateways/<profile>/current` |

## Shim vs Venv Discrepancy

s6-managed gateways run via `/opt/hermes/.venv/bin/hermes` (direct venv path).
The `/opt/hermes/bin/hermes` shim wrapper may show different `memory status`
results due to environment differences between the shim and the venv context.

**Rule**: trust the venv path result (used by the actual running process).
If `hermes memory status` via shim shows "Provider: (none)" but the venv path
shows "Provider: hindsight ← active", the gateway is working correctly.
