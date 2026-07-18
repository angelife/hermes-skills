# Cloudflare Workers AI — Hermes Configuration Reference

## Quick Setup
1. Account API Token (cfat_): Cloudflare Dashboard → Cloud icon → Account → More → API Tokens → "Edit Cloudflare Workers AI"
2. Account ID: Workers & Pages dashboard → "Account Details" section
3. Store in ~/.hermes/.env: `CLOUDFLARE_API_KEY=*** `providers:` block (near top of config.yaml) — appears in /model
```yaml
providers:
  cloudflare-workers-ai:
    base_url: "https://api.cloudflare.com/client/v4/accounts/{ACCOUNT_ID}/ai"
    api_key: ${CLOUDFLARE_API_KEY}
    timeout: 120
    max_tokens: 8192
```

**Pitfall (CRITICAL — verified 2026-07-01 by tracing `runtime_provider.py` on the running Hermes source):** Older wording in this file said `base_url` changed from `/ai/v1` to `/ai` in 2026. That is WRONG for Hermes OpenAI-compatible chat clients (`opencode-zen-free`, `cloudflare-workers-ai` as chat provider). Hermes' custom-provider branch passes `base_url` verbatim to the OpenAI client and only the client appends `/chat/completions` — there is **no auto-`/v1` injection in Hermes code** (the `/v1`-strip happens only for Anthropic-Messages mode and `opencode-zen`/`opencode-go`.)

Result: with `api_mode = chat_completions` (the default), the configured `base_url` MUST end in `/ai/v1` so the final POST becomes `…/ai/v1/chat/completions`. Without `/v1`, Hermes POSTs `…/ai/chat/completions` and Cloudflare returns 7003 "No route for that URI". The `/ai`-only path works only for the **native REST** `…/ai/run/{model}` style (curl tests), not for Hermes chat.

Working config:
```yaml
providers:
  opencode-zen-free:
    base_url: https://api.cloudflare.com/client/v4/accounts/{ACCOUNT_ID}/ai/v1
    api_key: ${CLOUDFLARE_API_KEY}
    timeout: 120
    max_tokens: 8192
```

Verification recipe:
```bash
ACCT={ACCOUNT_ID}
curl -s -o /dev/null -w "%{http_code}\n" -X POST \
  "https://api.cloudflare.com/client/v4/accounts/${ACCT}/ai/v1/chat/completions" \
  -H "Authorization: Bearer $CLOUDFLARE_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"@cf/qwen/qwen3-30b-a3b-fp8","messages":[{"role":"user","content":"hi"}],"max_tokens":10}'
```
Expected: `200`. Then restart gateway (from outside the running gateway process), then trigger one real cron (e.g. `gateway-watchdog` run-now) to confirm a real chat-completions delivery, not just a curl probe.

### `custom_providers:` block — for @cloudflare-workers-ai mention
```yaml
custom_providers:
  cloudflare-workers-ai:
    type: openai-api
    base_url: "https://api.cloudflare.com/client/v4/accounts/{ACCOUNT_ID}/ai"
    api_key: ${CLOUDFLARE_API_KEY}
    timeout: 120
    max_tokens: 8192
    models:
      - "@cf/qwen/qwen3-30b-a3b-fp8"
      - "@cf/qwen/qwq-32b"
      - "@cf/qwen/qwen2.5-coder-32b-instruct"
      - "@cf/ibm-granite/granite-4.0-h-micro"
```

## Verification
```bash
# Test API directly
# NOTE: Use /ai/run/{model} not /ai/v1/run/{model} — API path changed in 2026
curl -X POST https://api.cloudflare.com/client/v4/accounts/{ACCOUNT_ID}/ai/run/@cf/qwen/qwen3-30b-a3b-fp8 \
  -H "Authorization: Bearer *** \
  -H "Content-Type: application/json" \
  -d '{"model":"@cf/qwen/qwen3-30b-a3b-fp8","messages":[{"role":"user","content":"hi"}]}'

# Then restart gateway
hermes gateway restart
```

## Free Tier Models
| Model | Cost (Neurons/1M tokens) | Best for |
|-------|-------------------------|----------|
| @cf/qwen/qwen3-30b-a3b-fp8 | 4,625/30,475 | General chat, Chinese |
| @cf/ibm-granite/granite-4.0-h-micro | 1,542/10,158 | Ultra-light |
| @cf/qwen/qwq-32b | 60,000/90,909 | Reasoning |
| @cf/qwen/qwen2.5-coder-32b-instruct | 60,000/90,909 | Code |

## Deprecated Models (DO NOT USE)
- @cf/meta/llama-3.1-8b-instruct — 404 returned
- @cf/google/gemma-3-12b-it — access denied on free
- @cf/mistral/mistral-small-3.1-24b-instruct — model not found

## Pitfalls
- Must use **Account API Token** (cfat_), not User API Token (cfut_)
- Must add to BOTH `providers:` AND `custom_providers:` for full functionality
- Never `cat >> config.yaml` with a new `providers:` block — it overwrites existing providers
- Use `hermes gateway restart` after changes (not from inside gateway process)
- Gateway cannot restart itself — run from separate shell
- Token has 10,000 Neurons/day free reset at 00:00 UTC
