---
name: hermes-cron-design
description: Design self-maintaining Hermes cron jobs — log retention, phased rollouts with auto-transition, state tracking, safety valves. Prevents cron jobs from becoming secondary bloat points.
version: 1.0.0
author: Hermes Agent
tags:
  - cron
  - automation
  - self-maintaining
  - mechanism-lockin
  - memory-audit
---

# Hermes Cron Design

## Core Principle

**A cron job is not finished when it does its primary job. It's finished when it doesn't create a secondary maintenance problem.**

Every cron job that writes output (logs, reports, state files) creates a new resource that must itself be managed. Design for that from day one.

---

## Three Design Rules

### 1. Log Retention (mandatory)

Every cron job that writes files must delete old files on every run. Never create a log directory that grows unbounded.

```bash
find ~/.hermes/cron/output/ -name '<prefix>-*.txt' -mtime +30 -delete
```

Run this **before** writing the new log so the job never sees its own past output as a problem to solve.

**Default retention period:** 30 days unless the user specifies otherwise.

### 2. Phased Rollout with State File

When a cron job has destructive potential (delete/modify operations), ship it with a **phased rollout**:

| Phase | Behavior | Description |
|-------|----------|-------------|
| `observation` | Read + classify + report only | Writes logs, never modifies target |
| `execution` | Read + classify + execute | Performs deletions/modifications |

**State file pattern:** `~/.hermes/cron/<job-name>-state.json`

```json
{"phase": "observation", "day": 0, "last_day_with_issues": null, "pause_on_error": false}
```

### 3. Auto-Transition (NOT human-approval-based)

Do NOT design the observation→execution transition as "wait for user to check logs and approve." This recreates the exact failure mode: if the user forgets, the job stays in observation forever, wasting tokens and never delivering value.

**Correct pattern — time-based with safety valve:**

| Mechanism | Description |
|-----------|-------------|
| Timer | Fixed observation window (typically 7 days) |
| Day counter | State file tracks `day` value, increments each run |
| Auto-switch | At day 7, if `pause_on_error` is false, transition to execution |
| Safety valve | If the agent detects issues it's uncertain about for 7+ consecutive runs, set `pause_on_error: true` to freeze the phase |

**Key principle:** Default = trust. The job transitions unless the agent flags a reason not to.

**Enabling re-review after pause:** If `pause_on_error` is set, the safety valve froze the phase. To resume, the state file must be manually examined — alert the user via deliver='origin' instead of 'local'.

---

## State File Format (Recommended)

```json
{
  "phase": "observation",
  "day": 0,
  "last_day_with_issues": null,
  "pause_on_error": false,
  "pause_reason": null
}
```

Each run:
1. Read state file (create defaults if missing)
2. Increment day
3. Run primary task
4. Check for issues the agent can't confidently resolve
5. If issues exist for 7+ consecutive days → set `pause_on_error: true`
6. If day >= threshold (7) and no pause → auto-transition phase to `execution`
7. Write updated state file

---

## Delivery Strategy

| Mode | When | User impact |
|------|------|-------------|
| `deliver='local'` | Observation phase, routine execution | Silent — output goes to log file only |
| `deliver='origin'` | Safety valve triggered, manual intervention needed | Message appears in chat |

Don't deliver routine reports to the user during observation phase. They said "I'll spot-check logs" — deliver to files, not chat. Only escalate to chat when the job itself can't make progress.

## no_agent Pattern for Watchdog / Healthcheck Jobs

For deterministic, rule-based cron jobs (process health checks, service restart, log
threshold monitoring), prefer `no_agent=True`. This avoids LLM overhead, token cost,
and model-specific limits.

### When to use no_agent

| Use case | Example | Agent needed? |
|----------|---------|--------------|
| Service health check | "is process running + restart if not" | No — use `no_agent=True` |
| Log threshold monitor | "count pool timeout lines in last 10 min" | No — use `no_agent=True` |
| Session hygiene | "grep tokens > 120K, POST to API" | No — use `no_agent=True` |
| Semantic log analysis | "classify error patterns" | Yes — use agent |
| Decision with context | "should I rotate this key" | Yes — use agent |

### Setup

```bash
hermes cron create --schedule "every 5m" --name my-job \
  --deliver local --no-agent --script my_script.py
```

Script lives in `~/.hermes/scripts/`. Filename must be relative to that directory.
Output is delivered according to `--deliver` setting (stdout of script = message body).

### Pitfall: Gateway Lifecycle Commands Blocked

Cron jobs containing `launchctl kickstart`, `launchctl start/stop`, or any gateway
lifecycle command are **blocked at creation time** (#30719). This prevents
agent-driven SIGTERM-respawn loops under launchd/systemd supervision.

**Fix for gateway health:** Since launchd already has `KeepAlive=true`, you don't
need to restart the gateway from a cron job. If the gateway crashes, launchd handles
it. If you still need gateway monitoring, use a separate no_agent watchdog that
checks process liveness and alerts (without attempting restart).

### Verification

Test the script standalone first, then create the cron. Verify the cron ran by:

```bash
hermes cron list | grep "last_status"
```

---

## When to Use This Skill

- Creating any cron job that:
  - Writes output files (log, report, snapshot)
  - Has destructive potential (delete, modify, execute)
  - Goes through a phased rollout
  - The user might forget to monitor

- Reviewing existing cron jobs that:
  - Have growing output directories
  - Are stuck in a setup/observation phase with no auto-transition
  - Depend on the user remembering to check something

---

## Known Patterns

### Memory Audit (canonical example)
See `references/hermes-memory-audit.md` for the full memory-specific implementation.

### Self-Heal Watchdog (no_agent example)
See `references/self-heal-pattern.md` for a concrete no_agent watchdog that checks and restarts services, shrinks bloated sessions, and monitors team agents — all without LLM overhead. Every 5 minutes, deterministic script only.

### Generic pattern template
```yaml
(name of job):
  schedule: "0 3 * * *"
  deliver: local
  prompt: |
    ## Phase 1: Log retention
    Delete logs >30 days old.
    
    ## Phase 2: State check
    Read state file ~/.hermes/cron/<job>-state.json.
    Create defaults if missing.
    Increment day.
    
    ## Phase 3: Primary task
    (your task here)
    
    ## Phase 4: Phase management
    If phase=observation and day>=7 and no pause_on_error:
      → switch to execution mode this run
    If phase=observation and unresolved issue for 7+ days:
      → set pause_on_error, change deliver to origin
      → notify user
    
    Write updated state file.
```

---

## Pitfalls

- **Log files become the next audit target.** If you write audit logs without a retention policy, in 3 months the logs themselves will be flagged by the very resource monitor you're trying to protect. Delete old logs on every run.
- **Auto-transition on human approval is not auto.** If the transition depends on the user "checking logs and telling the job to switch", it will stay in observation forever because the user has other priorities. Use a timer, not a permission.
- **Safety valve must not fire on minor issues.** The threshold for `pause_on_error` should be high — the agent should only pause if it encounters the SAME unresolvable flag for 7+ consecutive runs. Minor format warnings or single-item uncertainties should not pause.
- **State file must have a clear initial state.** If the state file doesn't exist on first run, the job must create it with `day: 0` and `phase: observation`. Never assume the initial phase is `execution`.

- **Global model drift will silently disable cron jobs.** When a cron job is created without an explicit `model` pin (using the global `model.default`), and that global model later changes (e.g. `deepseek-v4-flash-free` → `grok-4.5`), the scheduler **skips the job** to prevent unintended spend. Message: `Skipped to prevent unintended spend: global inference config drifted… (model A -> B), and this job is unpinned`. 详见 `references/model-drift-pin.md`。

  **用户偏好（2026-07-17）：「有啥用啥、不挑食」** — 不要停任务等免费模型；钉到**当前可用模型**继续跑。给人解释：防误花跳过，不是业务挂了。

  Fix:
  ```
  cronjob action=update job_id=<id> model={"model":"<当前可用>"}
  ```
  provider 可省略（会钉当前 provider）。`hermes cron update` 不存在，用 `cronjob` 工具。

  Prevention: LLM agent 类 cron 创建时就 pin model；`no_agent=True` 脚本不受影响。
  - `deliver='origin'`：跳过会推错误摘要
  - `deliver='local'`：静默跳过，更难发现

---

## Self-Heal on Script Missing

A cron job that loses its script must **not silently do nothing**. The most common failure pattern in agent-run cron jobs:

1. The script lives at `~/.hermes/scripts/<name>.py` (the cron's `prompt` references this path)
2. On a later run, the file is missing (deleted during cleanup, symlink broken, skill updated but copy not refreshed, `~/.hermes/scripts/` directory doesn't exist)
3. The agent tries `terminal` → empty output → returns `[SILENT]` → the job is dead but no one knows

This is a **class-level problem**: the agent hits a missing file with terminal-only tooling, gets no output, and concludes "nothing to report." It should self-heal instead.

### Self-heal protocol for cron agents

| Step | Tool | Action | On failure |
|------|------|--------|------------|
| 1 | `search_files` | Check if `~/.hermes/scripts/<name>.py` exists | → step 2 |
| 2a | `skill_view` | Find authoritative source (the skill that owns this script) | → step 4 |
| 2b | `write_file` | Restore script from skill content | → step 4 on failure |
| 3 | `terminal` (background) | Run the restored script, process wait for output | Normal flow |
| 4 | Report | **障碍汇报** — write_file also failed, this cron can't self-heal | Not [SILENT] |

### Concrete example (WeChat monitor)

See `wechat-group-analysis` → "Cron 自修复" subsection for the live implementation.

### Embedding in each cron skill

Each cron job's governing skill should have a dedicated "自修复" subsection that:
- Names the specific script path and its source skill
- Lists exact `skill_view` + `write_file` commands
- Explicitly forbids `[SILENT]` when the script is missing

### Pitfall

`write_file` may fail in cron contexts with permission issues. In that case the agent **must** report the obstacle — don't drop silently. A bricked cron job is a bug that needs user attention, not a routine "no new messages."

### Pitfall: Empty Script (0 bytes) vs Missing Script

A script that **exists but is empty (0 bytes)** is a distinct failure mode from a missing script. The 04:18 WeChat monitor cron (2026-07-19) demonstrated this: `wechat-group-monitor.py` existed at the expected path but was 0 bytes. The agent spent **10+ tool calls** (search_files, read_file, terminal ls, execute_code) trying to find it before concluding it was empty.

**Correct response to an empty script (0 bytes):**

| Attempt | Action | If fails |
|---------|--------|----------|
| 1 | `terminal` — run the script | empty output → step 2 |
| 2 | `read_file` — check if file has content | 0 bytes → step 3 |
| 3 | Report: "Script exists but is empty (0 bytes). Cannot execute." → `[SILENT]` or report as appropriate | Done |

**Do NOT** continue to search_files, execute_code, or multiple terminal ls calls after step 2 confirms the file is empty. The answer is already known at step 2.

### Pitfall: Empty Script (0 bytes) vs Missing Script

A script that **exists but is empty (0 bytes)** is a distinct failure mode from a missing script. The 04:18 WeChat monitor cron (2026-07-19) demonstrated this: `wechat-group-monitor.py` existed at the expected path but was 0 bytes. The agent spent **10+ tool calls** (search_files, read_file, terminal ls, execute_code) trying to find it before concluding it was empty.

**Correct response to an empty script (0 bytes):**

| Attempt | Action | If fails |
|---------|--------|----------|
| 1 | `terminal` — run the script | empty output → step 2 |
| 2 | `read_file` — check if file has content | 0 bytes → step 3 |
| 3 | Report: "Script exists but is empty (0 bytes). Cannot execute." → `[SILENT]` or report as appropriate | Done |

**Do NOT** continue to search_files, execute_code, or multiple terminal ls calls after step 2 confirms the file is empty. The answer is already known at step 2.

### Pitfall: Over-investigation in Cron Jobs

When a cron job's script returns empty output or doesn't exist, limit investigation to **3 tool calls maximum** before reporting the result:

| Attempt | Action | If fails |
|---------|--------|----------|
| 1 | `terminal` — run the script | empty output → step 2 |
| 2 | `read_file` — check if file exists and has content | missing/empty → step 3 |
| 3 | Report: "Script missing/empty at <path>. Cannot execute." → `[SILENT]` or report | Done |

**Do NOT** continue to search_files, execute_code, or multiple terminal ls calls after step 2 confirms the file is missing or empty. The answer is already known at step 2. The 04:18 WeChat monitor cron (2026-07-19) demonstrated this failure: 10+ tool calls to confirm a 0-byte script.

### Pitfall: Empty Script (0 bytes) vs Missing Script

A script that **exists but is empty (0 bytes)** is a distinct failure mode from a missing script. The 04:18 WeChat monitor cron (2026-07-19) demonstrated this: `wechat-group-monitor.py` existed at the expected path but was 0 bytes. The agent spent **10+ tool calls** (search_files, read_file, terminal ls, execute_code) trying to find it before concluding it was empty.

**Correct response to an empty script (0 bytes):**

| Attempt | Action | If fails |
|---------|--------|----------|
| 1 | `terminal` — run the script | empty output → step 2 |
| 2 | `read_file` — check if file has content | 0 bytes → step 3 |
| 3 | Report: "Script exists but is empty (0 bytes). Cannot execute." → `[SILENT]` or report as appropriate | Done |

**Do NOT** continue to search_files, execute_code, or multiple terminal ls calls after step 2 confirms the file is empty. The answer is already known at step 2.

---

## Session Journal

- Created 2026-07-03 after user correction on memory audit cron job design: (a) log retention was missing, (b) auto-transition was dependent on user approval, which is same behavioral-failure pattern as the memory issue we were solving.
- User's key insight: every cron job that monitors something must monitor its own outputs too. "Log file bloat" is the same class of problem as "memory bloat" — a secondary maintenance burden the job itself creates.
- User's correction on auto-transition: "定一个明确、非模糊的退出条件" — timer-based, not human-approval-based. Default is trust.
