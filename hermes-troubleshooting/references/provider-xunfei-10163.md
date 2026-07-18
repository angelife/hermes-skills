# Xunfei API 10163 — RequestParamsError:Invalid Params

## Symptom
Gateway logs or cron job logs show repeated:
```
code: 10163, msg: RequestParamsError:Invalid Params
```
for Xunfei models like `xopqwen36v35b`.

## Root Cause
Xunfei's API endpoint (`https://maas-api.cn-huabei-1.xf-yun.com/v2`) does **not support** the OpenAI-format `tools`/`function_calling` parameter. When Hermes sends a request with `tools` (standard in agent-mode sessions and cron jobs), Xunfei rejects it with 10163.

Direct curl test **without** `tools` works:
```bash
curl -s -X POST "https://maas-api.cn-huabei-1.xf-yun.com/v2/chat/completions" \
  -H "Authorization: Bearer $XUNFEI_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"xopqwen36v35b","messages":[{"role":"user","content":"Hi"}],"max_tokens":10}'
```

## Implications
- Xunfei is **not suitable** for agent-mode tasks using tool/function calling.
- Works fine for basic chat / direct API calls without `tools`.
- Cron watchdog jobs and agent workflows must use a different model.

## Fix: Pin Cron Jobs to Compatible Models
When a `gateway-watchdog` cron job fails with provider errors:
1. Check which model the job uses: `hermes cron list`
2. If using Xunfei, update to a model that supports function calling:
   ```bash
   hermes cron update <job_id> --model @cf/qwen/qwen3-30b-a3b-fp8 --provider cloudflare-workers-ai
   ```
3. Recommended watchdog models:
   - `@cf/qwen/qwen3-30b-a3b-fp8` (Cloudflare Workers AI)
   - `deepseek-v4-flash-free` (OpenCode Zen free)
   - Any OpenAI-compatible model that supports `tools` parameter

## Verification
After update, check the job's next run will use the correct model:
```bash
hermes cron list | grep -A5 "gateway-watchdog"
```
Expected: `Model: @cf/qwen/qwen3-30b-a3b-fp8` (or chosen model)
