# Gateway "Empty Stream" / Streaming Failure Diagnosis

## Pattern: API works via direct CLI test but fails when called from gateway

**Familiar smell:** You can curl the API and get a valid response, but the gateway's agent logs show "Streaming failed before delivery: Provider returned an empty stream".

### Step-by-step

#### 1. Verify the actual HTTP request URL

The gateway saves `request_dump_*.json` files in `~/.hermes/sessions/`. Read the most recent one:

```bash
ls -t ~/.hermes/sessions/request_dump_* | head -1 | xargs python3 -c "import sys,json; d=json.load(open(sys.argv[1])); print('url:', d.get('url', 'N/A')); print('model:', d.get('model', 'N/A')); print('msgs:', len(d.get('messages', [])))"
```

**Common finding:** The URL path is wrong — e.g., `http://host:3000/chat/completions` instead of `http://host:3000/v1/chat/completions`.

**Root cause:** The OpenAI SDK constructs URLs by appending `/chat/completions` to the `base_url`. If `base_url` is `http://host:3000` (no `/v1`), the SDK builds `http://host:3000/chat/completions`. Non-v1 paths on many API gateways (New API, LiteLLM, etc.) return empty or malformed responses.

**Fix:** Set `base_url: http://host:3000/v1` in the gateway's config.yaml.

#### 2. Verify request_dump when response is empty

If the dump shows a non-standard URL path, the root cause is found before reading further code.

#### 3. Check quota when using New API / one-api

**Symptom:** Gateway gets "empty stream" but gate access logs show 403. In streaming mode, New API's quota-exhausted 403 surfaces as **"empty stream with no finish_reason"** (Hermes wraps the error), not as a visible 403.

**Check quota in New API DB:**

```bash
sqlite3 /path/to/one-api.db "SELECT id, username, quota, used_quota, (quota - used_quota) as remaining FROM users WHERE id=1"
```

**Fix:** Increase quota:
```sql
UPDATE users SET quota=quota+1000000000 WHERE id=1;
```
Then restart New API for the change to take effect.

#### 4. Narrow the gap: replicate the gateway's request

When the gateway fails and direct CLI tests pass, test with the EXACT same parameters:

```python
import os
os.environ['HTTP_PROXY'] = ''
os.environ['HTTPS_PROXY'] = ''

from openai import OpenAI
client = OpenAI(
    base_url='http://host:3000/v1',  # MUST match config
    api_key='sk-...',                  # MUST match config
    http_client=httpx.Client(verify=False, timeout=30.0)
)

# Use large message count to match real session size
messages = [{"role": "user", "content": "test"}] * 100
stream = client.chat.completions.create(
    model='model-name',
    messages=messages,
    stream=True,
    max_tokens=256
)
for chunk in stream:
    print(chunk)
```

#### 5. Check the log chain

Gateway logs at `~/.hermes/logs/gateway.log` show response timing:
```
response ready: ... time=X.Xs api_calls=N response=Y chars
```

- **time < 2s** with large context (43K tokens): The request was rejected quickly — URL path issue or quota check failed before processing.
- **time > 5-15s**: Request reached the model and is being processed normally.

## Common Failure Signatures

| Signature | Likely Root Cause |
|-----------|-------------------|
| time < 2s, response=empty "empty stream" | Wrong base_url path (missing `/v1`) |
| time < 2s, response=error-like chars | New API quota exhausted (403 wrapped as empty stream) |
| time > 15s, response=non-empty but "empty stream" | Provider rate limit (429) or model-side error |
| `HTTP 403: 预扣费额度失败` in errors.log | New API user quota insufficient for pre-authorization |
| `Provider returned an empty stream` + logs show 429 | API provider rate-limited; try different model or channel |

## Prevention

- Always set `base_url` ending with `/v1` (or the API's version prefix) when using OpenAI-compatible SDKs.
- Keep New API user quota generously high (1B+ units) to avoid surprise pre-auth failures.
- When adding gateway config for a new client, always test with `curl -v` first to confirm the exact path works.
