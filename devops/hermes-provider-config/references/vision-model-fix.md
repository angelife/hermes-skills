# Vision Model Configuration Repair

## Problem

The `vision:` block in `config.yaml` specifies a model for the `vision_analyze` tool. This model can go stale (provider deprecation, key expiration, OmniRoute route change). When broken, `vision_analyze` returns:

```
Error code: 400 - {'error': {'message': "Unable to determine provider for model '<stale-model>'. Use a provider/model prefix..."}}
```

Or rate-limit errors (429) that persist even after waiting.

## Diagnosis

```bash
# Check current vision config
grep -A5 'vision:' ~/.hermes/config.yaml

# List available vision models via OmniRoute
curl -s http://localhost:20128/v1/models | python3 -c "
import sys, json
d = json.load(sys.stdin)
for m in d['data']:
    caps = m.get('capabilities', {})
    if caps.get('vision', False):
        is_free = 'free' in m['id'].lower()
        print(f'{\"✅\" if is_free else \"💰\"} {m[\"id\"]}')
"
```

## Verified Working Free Vision Models (OmniRoute)

| Model ID | Provider | Notes |
|----------|----------|-------|
| `oc/mimo-v2.5-free` | OmniRoute (opencode-zen) | vision, 1M context, free ✅ |
| `opencode-zen/mimo-v2.5-free` | OmniRoute (opencode-zen) | same model, different alias |
| `ddgw/gpt-4o-mini` | OmniRoute (duckduckgo) | vision, 128K context |
| `ddgw/claude-3-5-haiku-20241022` | OmniRoute (duckduckgo) | vision, 200K context |

**⚠️ Known issue (2026-07-14):** `oc/mimo-v2.5-free` returns persistent 429 ("Rate limit exceeded") even after 10+ second cooldowns. This is an upstream rate limit on the opencode-zen free tier, not a transient error. Use NVIDIA direct (see below) as a reliable fallback.

## Verified Working Vision Models (NVIDIA Direct)

When OmniRoute vision models are rate-limited, use NVIDIA API directly. Three vision-capable models confirmed:

| Model ID | Notes |
|----------|-------|
| `meta/llama-3.2-11b-vision-instruct` | ✅ Fast, works well, good Chinese OCR |
| `meta/llama-3.2-90b-vision-instruct` | Higher quality, slower |
| `microsoft/phi-3-vision-128k-instruct` | Alternative option |

### Direct call via curl

```bash
NVKEY=$(grep '^NVIDIA_API_KEY=' ~/.hermes/.env | cut -d= -f2-)

B64=$(python3 -c "
import base64
with open('/path/to/image.jpg', 'rb') as f:
    print(base64.b64encode(f.read()).decode())
")

curl -s -X POST "https://integrate.api.nvidia.com/v1/chat/completions" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${NVKEY}" \
  -d "{
    \"model\": \"meta/llama-3.2-11b-vision-instruct\",
    \"messages\": [{\"role\":\"user\",\"content\":[{\"type\":\"text\",\"text\":\"描述这张图\"},{\"type\":\"image_url\",\"image_url\":{\"url\":\"data:image/jpeg;base64,${B64}\"}}]}],
    \"max_tokens\": 300,
    \"temperature\": 0.3
  }"
```

**Important:** NVIDIA API requires `data:image/jpeg;base64,...` format for local files. `file://` URLs are NOT supported.

## Verified Vision Model: Zhipu glm-4v (Standalone Provider)

When OmniRoute and NVIDIA both struggle, set up a dedicated Zhipu provider with `glm-4v` for vision.

### Add Zhipu provider

```bash
hermes config set providers.zhipu.base_url https://open.bigmodel.cn/api/paas/v4
hermes config set providers.zhipu.api_key "your_api_key_here"
hermes config set providers.zhipu.timeout 120
hermes config set providers.zhipu.max_tokens 8192
```

### Configure auxiliary.vision to use Zhipu

```yaml
auxiliary:
  vision:
    provider: zhipu
    model: glm-4v
    base_url: ''      # inherit from provider
    api_key: ''       # inherit from provider
    timeout: 120
```

### Verification

```bash
curl -s -X POST https://open.bigmodel.cn/api/paas/v4/chat/completions \
  -H "Authorization: Bearer $ZHIPU_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"glm-4v","messages":[{"role":"user","content":[{"type":"text","text":"描述这张图"},{"type":"image_url","image_url":{"url":"data:image/jpeg;base64,..."}}]}],"max_tokens":300}'
```

### Known characteristics

- `glm-4v` may NOT appear in `/v4/models` endpoint response but still works when called directly
- Accepts same image format as NVIDIA: `data:image/jpeg;base64,...`
- Inherits `base_url` and `api_key` from the `providers.zhipu` entry — leave these empty in `auxiliary.vision`
- Tested 2026-07-14: ✅ works with Hermes `auxiliary.vision` config

## Configure `auxiliary.vision` for Hermes

```yaml
# ~/.hermes/config.yaml — vision block

# Option A: via OmniRoute
auxiliary:
  vision:
    provider: omniroute
    model: oc/mimo-v2.5-free      # or ddgw/gpt-4o-mini
    base_url: ''
    api_key: ''
    timeout: 120

# Option B: via Zhipu (standalone provider)
auxiliary:
  vision:
    provider: zhipu
    model: glm-4v
    base_url: ''
    api_key: ''
    timeout: 120
```

**Note:** The `vision_analyze` tool in Hermes routes through this `auxiliary.vision` config. When that fails (e.g. rate limited), switch providers.

## Pitfalls

- **Model prefix required:** Always use full form like `oc/mimo-v2.5-free`, not `mimo-v2.5-free`.
- **Not all free models support vision:** `oc/deepseek-v4-flash-free` is free but has NO vision capability.
- **`provider: auto` uses OmniRoute's default routing** — this can pick a non-vision model. Explicitly set `provider: omniroute` + the specific vision model.
- **Image format matters:** All vision APIs need base64 data URL. `file://` paths don't work.
- **Rate limits are per-model under OmniRoute:** If mimo is 429'd, try a different model (ddgw/gpt-4o-mini) instead of retrying the same one.
- **No vision model in OmniRoute's free tier is guaranteed available:** Have at least one fallback (NVIDIA direct or Zhipu glm-4v).
- **Zhipu glm-4v hidden from listing:** Don't assume it's unavailable if not in `/v4/models`. Test directly.
- **⚠️ `api_key: ''` does NOT inherit from provider (CRITICAL):** Setting `api_key: ''` in `auxiliary.vision` overrides the provider-level key with an empty string. The `vision_analyze` tool passes this empty key, causing `401 ModelNotSupported`. Two fixes:
  - **Fix A:** Remove the `api_key` line entirely from `auxiliary.vision` → Hermes falls back to the provider's key.
  - **Fix B:** Set `api_key: ${ZHIPU_API_KEY}` and add `export ZHIPU_API_KEY='sk-...'` to `.env`.
  - **Fix C (last resort):** Hardcode the key directly in `config.yaml` (works but leaks the key into the config file).
  - **Verification:** Run `grep -A5 'vision:' ~/.hermes/config.yaml` and confirm `api_key` is not `''`.