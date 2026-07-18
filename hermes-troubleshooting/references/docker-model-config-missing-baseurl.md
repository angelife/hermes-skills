# Docker Model Config: Missing `base_url` Causes Silent Provider Fallback

## Symptom

A Docker-based Hermes agent (金/木 etc.) shows "running" (container up, gateway connected to Telegram) but NEVER successfully responds to messages. Gateway logs show provider errors (HTTP 402/401/403) from a **different provider** than the one declared in `model.provider`.

Example: config says `provider: opencode-zen` but gateway logs show `HTTP 402 Insufficient Balance` from `api.deepseek.com`.

## Root Cause

The `model:` section declares a provider but omits `base_url` and/or `api_mode`:

```yaml
# ❌ BROKEN — missing base_url and api_mode
model:
  default: deepseek-v4-flash-free
  provider: opencode-zen
```

Without `base_url` and `api_mode`, Hermes has no route to the declared provider. It falls through to the **model name's default provider** (`deepseek-v4-flash-free` → DeepSeek API). If DeepSeek has no balance/expired key, the error logged is a DeepSeek error — not an opencode-zen error — leading to wild-goose chases.

## Fix

Add the missing fields under `model:`:

```yaml
# ✅ WORKING — complete model config
model:
  default: deepseek-v4-flash-free
  provider: opencode-zen
  base_url: https://opencode.ai/zen/v1
  api_mode: chat_completions
```

Additionally, configure a working fallback provider:

```yaml
fallback_providers:
- xunfei   # must exist in providers: section with valid api_key
```

## Diagnosis

```bash
# 1. Check the model section — is base_url missing?
docker exec <container> grep -A5 '^model:' /opt/data/config.yaml

# 2. What errors is the gateway actually seeing?
docker exec <container> cat /opt/data/logs/gateways/<profile>/current
# Look for HTTP 401/402/403 — trace WHICH provider returned it

# 3. Test the DECLARED provider endpoint directly
docker exec <container> curl -s https://opencode.ai/zen/v1/models | head -3
# Expected: {"object":"list","data":[...]}
# If this fails, the provider endpoint is unreachable

# 4. Test the ACTUAL model name's default provider
# If base_url is missing, Hermes may resolve the model name against DeepSeek's API
# Check: is there a DEEPSEEK_API_KEY in .env? Does it have balance?
docker exec <container> cat /opt/data/.env | grep DEEPSEEK
```

## Real-World Example (2026-06-21)

Agent: 金同学 (gold profile, Docker container `hermes-gold`)
Config: `provider: opencode-zen` without `base_url` or `api_mode`
Result: Requests silently routed to DeepSeek API → `HTTP 402 Insufficient Balance` (DeepSeek account: -0.12 CNY)
Fix: Added `base_url: https://opencode.ai/zen/v1` and `api_mode: chat_completions` to model section; container restart.
Verification: `curl` from container to opencode-zen returned 200 with model list including `deepseek-v4-flash-free`.

## Prevention

Always verify the full model config after creating or cloning a Docker-based Hermes agent:

```bash
docker exec <container> grep -B1 -A5 '^model:' /opt/data/config.yaml \
  | grep -E 'default|provider|base_url|api_mode'
```

All four fields should be present. Missing `base_url` is the most common silent failure in multi-agent Docker deployments.
