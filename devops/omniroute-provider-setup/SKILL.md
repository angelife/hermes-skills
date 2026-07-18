---
name: omniroute-provider-setup
title: OmniRoute Provider Setup
description: Complete guide for configuring custom providers, proxy rules, and combos in OmniRoute v3.8.x
version: 1.0
lastUpdated: 2026-07-13
---

# OmniRoute Provider Setup

Complete reference for setting up custom OpenAI-compatible providers in OmniRoute, configuring proxy rules, and creating combo fallback chains.

## Version Note

**CLI vs Server versions differ significantly.**

| Component | Version | Purpose |
|-----------|---------|---------|
| Server daemon | **v16.2.9** | 实际运行在 `localhost:20128` 的反向代理服务 |
| CLI tool | **v3.8.46** | `/usr/local/bin/omniroute` 命令行工具 |

Both are from the same install. The CLI (v3.x) is an older package that happens to share the binary name. The server (v16.x) is the actual proxy.

**Important:** The CLI may report Node.js compatibility warnings. The running server is unaffected. Always interact with the running server via its REST API (`localhost:20128`) or Dashboard (`http://localhost:20128/`) — NOT the CLI. The CLI's `keys add` etc. may fail for custom providers; use Dashboard API calls instead.

Currently exposed 344 models across 7+ providers (NVIDIA, OpenCode, Auggie, DuckDuckGo, Veo, etc.).

## Trigger

- Need to add a new AI provider (NVIDIA, OpenCode Zen, custom OpenAI-compatible API) to OmniRoute
- Provider keys are valid but not working through OmniRoute
- Proxy-related upstream failures in OmniRoute

## Architecture Overview

OmniRoute has two provider systems:

| System | Purpose | Storage | API |
|--------|---------|---------|-----|
| **Built-in providers** | OAuth / known API-key providers (OpenAI, Anthropic, NVIDIA, Groq, etc.) | Source code (`open-sse/config/providers/registry/`) | Dashboard → Add API Key |
| **Custom provider nodes** | OpenAI/Anthropic-compatible custom endpoints | `provider_nodes` SQLite table | `POST /api/provider-nodes` |

## Step 1: Verify Key Directly (Before OmniRoute Config)

Always confirm the key and endpoint work *before* configuring OmniRoute:

```bash
# OpenAI-compatible provider test
curl -s -w "\nHTTP %{http_code}, Time %{time_total}s\n" --max-time 15 \
  -H "Authorization: Bearer <API_KEY>" \
  -H "Content-Type: application/json" \
  -d '{"model": "<model-id>", "messages": [{"role": "user", "content": "hi"}], "max_tokens": 5}' \
  https://<provider-api-endpoint>/v1/chat/completions

# List models
curl -s --max-time 15 \
  -H "Authorization: Bearer <API_KEY>" \
  https://<provider-api-endpoint>/v1/models
```

**Known endpoints:**
- OpenCode Zen: `https://opencode.ai/zen/v1`
- NVIDIA NIM: `https://integrate.api.nvidia.com/v1` (works from China *without proxy*)
- Standard OpenAI-compatible: `https://api.openai.com/v1`

## Step 2: Add Custom OpenAI-Compatible Provider Node

For providers NOT in OmniRoute's built-in catalog (e.g., OpenCode Zen):

```bash
# 1. Log into Dashboard
curl -s -c /tmp/omniroute_cookies.txt -X POST http://localhost:20128/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"password":"<DASHBOARD_PASSWORD>"}'

# 2. Create provider node
curl -s -b /tmp/omniroute_cookies.txt -X POST http://localhost:20128/api/provider-nodes \
  -H "Content-Type: application/json" \
  -d '{
    "type": "openai-compatible",
    "name": "<Display Name>",
    "prefix": "<provider-prefix>",
    "baseUrl": "https://<api-endpoint>/v1",
    "apiType": "chat",
    "chatPath": "/v1/chat/completions",
    "modelsPath": "/v1/models"
  }'
```

**Required fields:**
- `type`: `"openai-compatible"` or `"anthropic-compatible"` (NOT `"openai"`)
- `prefix`: short slug used in model IDs (e.g., `opencode-zen` → `opencode-zen/deepseek-v4-flash-free`)
- `baseUrl`: API base URL (e.g., `https://opencode.ai/zen/v1`)

## Step 3: Add API Key for the Provider

```bash
# Through Dashboard API — works for ALL provider types (built-in + custom)
curl -s -b /tmp/omniroute_cookies.txt -X POST http://localhost:20128/api/providers \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "<prefix-from-step-2>",
    "authType": "apikey",
    "name": "<Connection Name>",
    "apiKey": "<ACTUAL_API_KEY>"
  }'
```

**Important:** The CLI command `omniroute keys add <provider> <key>` does NOT work for custom provider nodes — it only works for built-in providers. Use the Dashboard API instead.

## Step 4: Proxy Configuration

### Problem
OmniRoute's `undici`-based ProxyFetch may fail with certain HTTP/SOCKS5 proxies (`request_signal_aborted` error). Some providers (NVIDIA) work **directly** from some regions.

### Solution: Set/Unset Global Proxy

```bash
# Set global proxy
curl -s -b /tmp/omniroute_cookies.txt -X PUT http://localhost:20128/api/settings/proxy \
  -H "Content-Type: application/json" \
  -d '{"level": "global", "proxy": {"type":"http","host":"<ip>","port":<port>}}'

# Clear global proxy
curl -s -b /tmp/omniroute_cookies.txt -X PUT http://localhost:20128/api/settings/proxy \
  -H "Content-Type: application/json" \
  -d '{"level": "global", "proxy": null}'
```

### Proxy Compatibility Check
```bash
# Test SOCKS5
curl -s -x socks5://127.0.0.1:10808 https://httpbin.org/ip

# Test HTTP CONNECT
curl -s -x http://127.0.0.1:10808 https://httpbin.org/ip
```

### Known Proxy Issues
- **`request_signal_aborted`** from `ProxyFetch` → try switching between `http` and `socks5` proxy types, or clear global proxy
- **Env vars don't help**: OmniRoute uses its own ProxyFetch system, not Node.js native proxy resolution
- **Some providers don't need proxy** from China: NVIDIA NIM (`integrate.api.nvidia.com`) works direct

## Step 5: Create Combo (Fallback Chain)

```bash
curl -s -b /tmp/omniroute_cookies.txt -X POST http://localhost:20128/api/combos \
  -H "Content-Type: application/json" \
  -d '{
    "name": "<combo-name>",
    "strategy": "priority",
    "models": [
      {"model": "oc/deepseek-v4-flash-free"},
      {"model": "opencode-zen/deepseek-v4-flash-free"},
      {"model": "nvidia/deepseek-ai/deepseek-v4-flash"}
    ]
  }'
```

Set as default combo:
```bash
sqlite3 ~/.omniroute/storage.sqlite "UPDATE key_value SET value='\"<combo-name>\"' WHERE key='activeComboId';"
```

## Step 6: Test the Combo

```bash
curl -s -w "\nHTTP %{http_code}\n" --max-time 30 http://localhost:20128/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model": "<combo-name>", "messages": [{"role": "user", "content": "Say hi in 2 words"}], "max_tokens": 10}'
```

Check response header `x-omniroute-provider` to see which model in the combo was used.

## Cleanup

Remove dead/expired provider connections:
```bash
# Via SQLite (direct)
sqlite3 ~/.omniroute/storage.sqlite "DELETE FROM provider_connections WHERE provider='<provider>' AND test_status='expired';"
```

List all connections:
```bash
curl -s -b /tmp/omniroute_cookies.txt http://localhost:20128/api/providers | python3 -m json.tool
```

## Dashboard Password Reset

If the dashboard password is lost:
```bash
# 1. Generate a bcrypt hash
export PATH=/Users/macos/.n/bin:$PATH && node -e "
const b = require('/Users/macos/.n/lib/node_modules/omniroute/node_modules/bcryptjs');
console.log(b.hashSync('new-password', 12));
"

# 2. Update in database
sqlite3 ~/.omniroute/storage.sqlite "UPDATE key_value SET value='\"<hash>\"' WHERE key='password';"

# 3. Or disable login requirement
sqlite3 ~/.omniroute/storage.sqlite "UPDATE key_value SET value='false' WHERE key='requireLogin';"
```

## Troubleshooting

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| `[401]: Missing API key` | Provider is OAuth-based but you added API key | Create custom provider node with `openai-compatible` type |
| `[401]: Incorrect API key` | Key expired/wrong for the target API | Verify key with direct curl, re-add with correct one |
| `request_signal_aborted` | OmniRoute undici proxy failure | Switch proxy type or set provider to direct (null proxy) |
| `ResourceExhausted` / rate limits | Free tier quota exceeded | Add fallback models in combo for failover |
| `timeout` after 30s+ | Proxy blocking or provider unreachable | Test direct curl, check proxy compatibility |
| CLI `keys add` fails with "Unknown provider" | Custom provider not in catalog | Use Dashboard API `POST /api/providers` instead |
| Combo not showing in `/v1/models` | Not set as active default | Set `activeComboId` in key_value table |
