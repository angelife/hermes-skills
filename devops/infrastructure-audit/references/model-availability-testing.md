# Provider Model Availability Testing

When auditing a provider's model availability, run a systematic parallel test using Python + ThreadPoolExecutor.

## Core Script Pattern

```python
python3 << 'PYEOF'
import json, urllib.request, os, concurrent.futures

env = {}
with open(os.path.expanduser("~/.hermes/.env")) as f:
    for line in f:
        line = line.strip()
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            env[k] = v

key = env.get("PROVIDER_API_KEY_ENV_VAR", "")
base_url = "https://provider.api.endpoint/v1/chat/completions"

def test_model(model):
    try:
        req = urllib.request.Request(
            base_url,
            data=json.dumps({
                "model": model,
                "messages": [{"role": "user", "content": "say OK in 1 word"}],
                "max_tokens": 5,
                "temperature": 0
            }).encode(),
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=12) as r:
            resp = json.loads(r.read())
            return f"✅ {model}"
    except urllib.error.HTTPError as e:
        return f"❌ {model}: HTTP {e.code}"
    except Exception as e:
        err = str(e)
        if "timeout" in err.lower(): return f"⏱️ {model}: timeout"
        elif "401" in err or "403" in err: return f"🚫 {model}: auth"
        else: return f"❌ {model}: {err[:60]}"

with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex:
    futures = {ex.submit(test_model, m): m for m in model_list}
    for fut in concurrent.futures.as_completed(futures, timeout=240):
        print(fut.result())
PYEOF
```

## Known Provider Endpoints & Auth

| Provider | Key Env | Chat Endpoint | Common Failures |
|----------|---------|---------------|-----------------|
| NVIDIA NIM | NVIDIA_API_KEY | https://integrate.api.nvidia.com/v1/chat/completions | 404 (not in free tier), timeout (model too large) |
| OpenCode Zen | OPENCODE_ZEN_API_KEY | https://opencode.ai/zen/v1/chat/completions | 403 = key expired |
| DeepSeek | DEEPSEEK_API_KEY | https://api.deepseek.com/v1/chat/completions | 402 = quota 0; try via NVIDIA NIM |
| Firecrawl | FIRECRAWL_API_KEY | POST https://api.firecrawl.dev/v0/scrape | 404 on status endpoint is not fatal |
| Agnes | AGNES_API_KEY | https://apihub.agnes-ai.com/v1 | Works; list via /models endpoint |

## Result Categorization

| Prefix | Meaning | Action |
|--------|---------|--------|
| `✅` | Working | Keep |
| `❌ HTTP 404` | Model not available in this tier | Remove from list |
| `❌ HTTP 401/403` | Auth failure | Replace key |
| `❌ HTTP 402` | Quota exhausted | Top up or route via another provider |
| `⏱️ timeout` | Model too large/slow | Note as slow tier |
| `❌ 500/400` | Server error | Retry later |

## Cleanup After Testing

1. Collect all `❌` models from test output
2. Find where they are referenced:
   - Hermes config: usually auto via `model: ''`, no manual deletion needed
   - New API/one-api: update via admin UI or direct SQL
3. Report net changes to user: how many added, how many removed, key replacements needed

## NVIDIA NIM Specific (2026-06, ~38/121 models usable free)

**Working**: deepseek-v4-flash, llama-3.3-70b, llama-3.1-70b, llama-3.1-8b, qwen3.5-397b-a17b, kimi-k2.6, mistral-medium-3.5-128b, step-3.7-flash, llama-3.2-11b-vision-instruct

**404 not in free tier**: nemotron-4-340b, mistral-large-2, mixtral-8x22b, gemma-*-12b, llama2-70b, codellama-70b, yi-large, qwen3.5-122b

**Timeout (too large)**: minimax-m2.7, minimax-m3, qwen3-next-80b, nemotron-3-ultra-550b

Re-test when new model errors appear — NVIDIA model catalog changes frequently.