# Xunfei 10163: Tools/Function Calling Incompatibility

Session: 2026-06-29 — Gateway stopped, watchdog cron failing with Xunfei 10163

## Symptoms

- `hermes gateway status` shows "installed but stopped" (LastExitStatus=9)
- `hermes cron list` shows `gateway-watchdog` job last_run status = `error: RuntimeError: Xunfei request failed with Sid: ... code: 10163, msg: RequestParamsError:Invalid Params`
- Gateway error.log shows repeated 10163 errors for every cron cycle (every 5 min)
- `curl` directly against Xunfei API works fine (no tools param)

## Root Cause

Xunfei's API (`maas-api.cn-huabei-1.xf-yun.com/v2`) is **format-compatible with OpenAI chat completions but does NOT support the `tools`/function calling parameter**. When Hermes sends a request with `tools` (as it does for any agent needing tool access — reading files, running commands), Xunfei returns:

```
code: 10163, msg: RequestParamsError:Invalid Params
```

Official Xunfei error code definition: 10163 = "请求引擎的参数异常" (request engine parameter anomaly).

Direct curl without `tools` works and returns a normal completion — proving the model and key are valid.

## Fix

Override the cron job's model to one that supports function calling:

```bash
hermes cron update <job-id> \
  --model cloudflare-workers-ai/@cf/qwen/qwen3-30b-a3b-fp8
```

Or for no-agent (script-only) watchdog jobs, switch to `no_agent=true` mode so no LLM is involved.

## Verification

After fix:
- `hermes cron list` shows next run scheduled, no error
- Gateway log shows clean cycles
- Xunfei still works for plain chat (just not for tool-using agents)

## Affected Components

Any Hermes cron job or agent that:
1. Uses Xunfei as its model
2. And has tool-using prompts (terminal, file read, web search, etc.)

This includes the built-in `gateway-watchdog` cron job when default model is Xunfei.
