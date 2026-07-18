# Session Reference: no_agent watchdog validation (2026-07-04)

This file records a durable verification pattern for Hermes cron watchdog jobs that were converted from agent mode to `no_agent=True`, plus two related Hermes runtime guardrails discovered in the same session.

---

## 1) `last_status=ok` is not sufficient verification

After converting a watchdog cron to `no_agent=True`:

- `cron last_status=ok` only means the script exited 0
- It does **not** mean the script actually inspected the expected log content
- It does **not** mean no LLM provider calls were made

Without evidence, the valid states should be recorded as:
- `configured` — code/prompt looks correct
- `runtime-validated` — proven under real/logical execution
- `not-runtime-verified` — still needs traffic or control test

Never conflate `ok` with `runtime-validated`.

---

## 2) Required minimum verification set for no_agent watchdog

Use all three checks together.

### a) Behavioral control test
1. Run the script against an unmodified log → record baseline output/decision
2. Append a unique synthetic marker to the watched log, e.g. `[STEP3.5-TEST]`
3. Run the script again → confirm its output/decision differs from baseline
4. Remove the synthetic marker after testing

This proves the script reads dynamic content rather than hardcoding or exiting silently.

### b) Negative LLM-call evidence
During or immediately after the manual run, grep the Hermes gateway error log for provider-routed entries such as `provider=`.

- If the test window shows zero provider-routed entries, that is positive evidence the LLM fallback path was not hit
- Do **not** infer "no LLM call" from `agent.log` silence alone
  - Silence may mean "this execution path was never exercised"
  - Silence is not equivalent to "executed path, skipped LLM"

### c) Cron wiring check
Inspect `~/.hermes/cron/jobs.json` directly and confirm:
- `no_agent=true`
- `script=watchdog_no_agent.sh`
- `prompt` is empty or absent
- There is no parallel older watchdog entry still bound to an LLM model path

---

## 3) Config change without traffic is not runtime validation

If the only known caller of a config value is removed from active traffic, then changing the config does **not** constitute runtime verification.

Record the state as:
- `configuration-correct`
- `not-yet-runtime-verified`

If the config becomes logically unused indefinitely, treat that also as a config-drift risk worth a separate `/discovery`.

---

## 4) Do not double-patch PID locks

Modern Hermes already has duplicate-instance protection stronger than a manual shell PIDFILE:

- `gateway.run.start_gateway()` duplicate-instance guard
- `gateway.status.acquire_gateway_runtime_lock()` via `fcntl.flock(..., LOCK_EX | LOCK_NB)`
- `gateway.pid` with `pid + start_time` for PID-reuse protection
- `remove_pid_file()` scoped cleanup on shutdown/replace paths

Do **not** add a second shell-wrapper PIDFILE around `launchctl unload/load` or a wrapper script around this.
Doing so creates cleanup-race and kill-the-good-instance risks that are worse than the original defect.

If duplicate-start prevention is ever needed, patch `gateway.status` / `gateway.run`, not shell wrappers.

---

## 5) Observability gaps are first-class findings

When investigating fallback/routing problems, if Hermes logs lack reliable per-line timestamps, do **not** manufacture time-window matches from adjacent shell output or inferred block position.

Record the finding explicitly: `verification blocked by missing per-line timestamps`.

Then pivot to independent evidence channels:
- service-side request counters / `/metrics`
- request-id-enriched request logs
- explicit instrumentation hook in the caller

Do not weaken acceptance criteria to fit the evidence.
