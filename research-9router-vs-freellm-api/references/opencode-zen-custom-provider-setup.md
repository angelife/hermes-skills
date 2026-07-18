# OpenCode Zen Custom Provider Setup in OmniRoute

## Date
2026-07-08

## Problem
Three OpenCode Zen API keys were injected into OmniRoute v3.8.46 via `POST /api/providers` with `provider: "opencode"`. The built-in `opencode` provider uses **OAuth** authentication, not API keys. All requests returned `401 Missing API key` with log message `Using opencode account: noauth...` — the API keys were silently ignored.

## Root Cause
The `opencode` provider in OmniRoute's built-in registry uses OAuth device code flow. API keys stored in `provider_connections` with `provider='opencode'` are never picked up by the OAuth-based executor.

## Fix: Custom OpenAI-Compatible Provider

### Step 1: Register provider node

```bash
curl -c /tmp/omniroute_cookies.txt -X POST http://localhost:20128/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"password":"1234567890"}'

curl -s -b /tmp/omniroute_cookies.txt -X POST http://localhost:20128/api/provider-nodes \
  -H "Content-Type: application/json" \
  -d '{
    "type": "openai-compatible",
    "name": "OpenCode Zen",
    "prefix": "opencode-zen",
    "baseUrl": "https://opencode.ai/zen/v1",
    "apiType": "chat",
    "chatPath": "/v1/chat/completions",
    "modelsPath": "/v1/models"
  }'
```

### Step 2: Add API Keys

```bash
curl -s -b /tmp/omniroute_cookies.txt -X POST http://localhost:20128/api/providers \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "opencode-zen",
    "authType": "apikey",
    "name": "OC Zen Main",
    "apiKey": "sk-..."
  }'
```

### Step 3: Verify

```bash
# Check models
curl -s http://localhost:20128/v1/models | python3 -c "import json,sys;d=json.load(sys.stdin);[print(m['id']) for m in d['data'] if 'opencode-zen' in m['id']]"

# Test call
curl -s -w '\nHTTP %{http_code}\n' --max-time 30 http://localhost:20128/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"opencode-zen/deepseek-v4-flash-free","messages":[{"role":"user","content":"hi"}],"max_tokens":5}'
```

## Free Models Verified

All returned `"cost":"0"` in response:

| Model ID | Status |
|----------|--------|
| `deepseek-v4-flash-free` | ✅ HTTP 200 |
| `mimo-v2.5-free` | ✅ HTTP 200 |
| `hy3-free` | ✅ HTTP 200 |
| `nemotron-3-ultra-free` | ✅ HTTP 200 |
| `north-mini-code-free` | ✅ HTTP 200 |

Paid models (e.g. `deepseek-v4-flash`) return `CreditsError: No payment method. Add a payment method here: https://opencode.ai/workspace/.../billing`

## Keys Used

From `/Users/macos/key.txt`:
```
sk-wgf4Dm1tJF89NqrwWab3YPT5NMKhbsplx8WEkjfySfsEFUv6H4vk2e92vdJJuNhq
sk-AnUsGieZDVWcI1CScI7GIlNuTPwtF42dvhUinLFL5l2VTZppFf7Kc1TN5rKcwb7q
sk-N7llEyCy08vYUZFRYaHDEx1PH2D3PkZS5ZMK3GstQzPYH5zdwggLAw19rEXmoQXz
```

## Related

- `research-9router-vs-freellm-api` skill → section "Custom OpenAI-Compatible Providers via provider_nodes API"
- Pitfall #21: OAuth-based providers ignore stored API keys
