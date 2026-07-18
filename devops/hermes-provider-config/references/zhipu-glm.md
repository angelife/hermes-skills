# 智谱 GLM (Zhipu) — Hermes Provider Reference

## Overview

智谱 AI (bigmodel.cn) provides OpenAI-compatible LLM APIs. The **GLM-4-Flash** model is permanently free with generous rate limits, making it the best default provider for Chinese cloud VPS deployments where Hermes needs a working, no-cost, fully-compatible API.

## Quick Start

```bash
# Configure via Hermes CLI
hermes config set providers.zhipu.base_url https://open.bigmodel.cn/api/paas/v4/
hermes config set providers.zhipu.api_key "your_api_key_here"
hermes config set providers.zhipu.timeout 120
hermes config set providers.zhipu.max_tokens 8192

# Set as default
hermes config set model.default GLM-4-Flash
hermes config set model.provider zhipu

# Verify
hermes chat -q "Hello" -m GLM-4-Flash --provider zhipu
```

## API Format

- **Base URL:** `https://open.bigmodel.cn/api/paas/v4/`
- **Auth:** `Bearer <api_key>` (standard OpenAI format)
- **Models endpoint:** `GET /api/paas/v4/models` (returns list of paid models; free models may not appear but still work)
- **Chat completions:** `POST /api/paas/v4/chat/completions` (standard format)

## Free Model: GLM-4-Flash

| Property | Value |
|----------|-------|
| Model ID | `GLM-4-Flash` |
| Context | 128K tokens |
| Cost | **永久免费 (permanently free)** |
| Tool calls | ✅ Supported |
| Hermes compatible | ✅ Full native support |

**Important:** GLM-4-Flash may NOT appear in the `/api/paas/v4/models` endpoint response (which only lists paid models like `glm-4.5`, `glm-5`, `glm-5.1`, `glm-5.2`). This is normal — the model is still callable. Always test directly with a chat completions call.

## Vision Model: glm-4v

| Property | Value |
|----------|-------|
| Model ID | `glm-4v` |
| Cost | Depends on key tier (not permanently free) |
| Vision input | ✅ Base64 image, URL |
| Input format | OpenAI-compatible `content: [{type:"text"...},{type:"image_url"...}]` |
| Best for | `auxiliary.vision` provider in Hermes config |

**Available models list** (returned by `/v4/models` endpoint with valid key) — confirmed models as of 2026-07:
- `glm-4.5`, `glm-4.5-air`
- `glm-4.6`
- `glm-4.7`
- `glm-5`, `glm-5-turbo`, `glm-5.1`, `glm-5.2`
- `glm-4v` (vision, may not appear in model list but works when called directly)

### Configure as auxiliary.vision

```yaml
auxiliary:
  vision:
    provider: zhipu
    model: glm-4v
    base_url: ''      # inherit from provider
    api_key: ''       # inherit from provider
    timeout: 120
```

The `base_url` and `api_key` are inherited from the `providers.zhipu` settings — leave them empty.

## Verification

```bash
# Direct API test — text model
curl -s https://open.bigmodel.cn/api/paas/v4/chat/completions \
  -H "Authorization: Bearer $ZHIPU_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"GLM-4-Flash","messages":[{"role":"user","content":"say OK"}],"max_tokens":10}'

# Direct API test — vision model (base64 image)
curl -s -X POST https://open.bigmodel.cn/api/paas/v4/chat/completions \
  -H "Authorization: Bearer $ZHIPU_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"glm-4v","messages":[{"role":"user","content":[{"type":"text","text":"描述这张图"},{"type":"image_url","image_url":{"url":"data:image/jpeg;base64,..."}}]}],"max_tokens":300}'

# Hermes test
hermes chat -q "say OK" -m GLM-4-Flash --provider zhipu --quiet
```

## Pitfalls

1. **Free model hidden from listing** — GLM-4-Flash works but won't appear in `/v4/models`. Don't assume it's unavailable.
2. **glm-4v hidden from listing** — Same as GLM-4-Flash: may not appear in `/v4/models` but still works when called directly.
3. **Free trial ≠ permanent** — GLM-4-Flash IS permanently free, but other models (GLM-5, glm-4.5-air) have limited trial credits. Check the console for current status.
4. **From inside China** — bigmodel.cn is fully reachable from domestic networks (tested ✅ from Huawei Cloud AI Shell, Beijing).
5. **No proxy needed** — direct HTTP connections work from within mainland China.
6. **`hermes config set` is slow** — commands can take 10-20s to complete on this machine. Use `timeout 25 hermes config set ...` to avoid premature timeout.