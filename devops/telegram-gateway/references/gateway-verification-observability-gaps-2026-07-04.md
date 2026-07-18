# Gateway Observability Gaps Observed 2026-07-04

These are blocking gaps encountered during Hermes Gateway root-cause and fix verification. Current, not historical.

- **Hermes fallback/routing logs lack stable request identity and row-leading timestamps.**  
  `agent.conversation_loop` failure lines reliably contain `provider/base_url/model/summary`, but timestamps are placed on preceding continuation lines, not on the match itself. This makes time-window proof impossible across Hermes and upstream services.
- **`localhost:3001` failures cannot be attributed to a specific test window.**  
  Freellmapi logs from container/docker showed `[Health] Check complete.` only; no request log endpoint, no `/metrics`, no JSON access log. No evidence density for timestamp cross-checks.
- **`@cf/qwen/qwen3-30b-a3b-fp8` in this install is deprecated by workflow.**  
  After watchdog was converted to `no_agent` script, current config has no live caller for this provider. Hardcoding `default_max_tokens=28000` in plugins is fine as a protective ceiling, but the value is no longer runtime-validated.
- **Duplicate-start prevention exists already.**  
  `gateway/run.py:start_gateway` uses duplicate-instance guard + `gateway/status.py` runtime lock/scoped locks. No additional shell-level PID wrapper needed.
- **`--replace` semantics:** planned takeover path, not bypass. It writes a takeover marker, SIGTERMs the existing pid, waits up to 10s, force-kills if needed, removes pid/lock metadata, then proceeds. Safe.
- **Verification pattern for `no_agent` cron:** baseline run, inject known bad keyword, rerun, diff behavior. Required because `exit 0` alone is weak evidence.

## Suggested minimal observability fix DO NOT BLOCK ON NOW

Add monotonic request start timestamp and short `request_id` to the LLM call emission line in `agent.conversation_loop`. Keep it local, do not rewrite Hermes logging. This closes 90% of the current tracing gap without Prometheus/ELK.

## Config state checked 2026-07-04

- `config.yaml` syntax: OK
- `fallback_providers`: `freellmapi`, `nvidia/z-ai/glm-5.1`, `nvidia/deepseek-ai/deepseek-v4-flash`
- `gateway.pid` owner: launchd `ai.hermes.gateway` service
- `gateway-watchdog` cron job id: `da2b5692cb9b` -> `watchdog_no_agent.sh`, `no_agent=true`
- Modified plugin files:
  - `plugins/model-providers/qwen-oauth/__init__.py:79` default_max_tokens=`28000`
  - `plugins/model-providers/custom/__init__.py:71` default_max_tokens=`28000`