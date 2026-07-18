# Provider Key Inventory Scan — Systematic Fallback Discovery

## Trigger

A Hermes provider returns `HTTP 401` or `HTTP 403`. Instead of single-key debugging, scan ALL API keys in `.env` to find working fallbacks.

## Why This Works

The .env often contains 3-7 API keys (NVIDIA, OpenCode, DeepSeek, OpenRouter, etc.). When one key expires, another may still be valid. Most provider dashboards don't overlap — a valid NVIDIA API key doesn't tell you anything about your OpenCode Zen key.

## Procedure

### Step 1: Extract all API_KEY / _TOKEN vars from .env

```bash
# On the host (macOS or Docker host):
grep -E 'API_KEY|_TOKEN|_SECRET' ~/.hermes/.env

# Inside a Docker container:
docker exec <container> grep -E 'API_KEY|_TOKEN|_SECRET' /opt/data/.env
```

Expected output (redacted but shows key names + value length):
```
OPENCODE_ZEN_API_KEY=sk-*** (37 chars)
NVIDIA_API_KEY=nvapi-*** (30 chars)
DEEPSEEK_API_KEY=sk-*** (52 chars)
HINDSIGHT_API_KEY= (empty? missing?)
```

### Step 2: Test each key independently (Python — avoids shell quoting issues)

Create and run a small script that tests each endpoint:

```python
import urllib.request
import json
import os

tests = [
    {
        "name": "OpenCode Zen",
        "url": "https://opencode.ai/zen/v1/models",
        "headers": {"Authorization": "Bearer <KEY>"},
        "key_var": "OPENCODE_ZEN_API_KEY"
    },
    {
        "name": "NVIDIA",
        "url": "https://integrate.api.nvidia.com/v1/models",
        "headers": {"Authorization": "Bearer <KEY>"},
        "key_var": "NVIDIA_API_KEY"
    },
    {
        "name": "DeepSeek",
        "url": "https://api.deepseek.com/v1/models",
        "headers": {"Authorization": "Bearer <KEY>"},
        "key_var": "DEEPSEEK_API_KEY"
    },
]

for t in tests:
    key = os.environ.get(t["key_var"], "")
    if not key:
        print(f"{t['name']}: SKIP (no key)")
        continue
    req = urllib.request.Request(
        t["url"],
        headers={k: v.replace("<KEY>", key) for k, v in t["headers"].items()}
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            print(f"{t['name']}: HTTP {resp.status} ✅")
    except urllib.error.HTTPError as e:
        print(f"{t['name']}: HTTP {e.code} ❌ ({e.reason})")
    except Exception as e:
        print(f"{t['name']}: ERROR ({type(e).__name__}: {e})")
```

**Why Python and not curl?** API keys often contain special characters (`$`, `{`, `}`, `!`) that get mangled by shell interpolation even inside single quotes. Python's urllib bypasses the shell entirely.

### Step 3: For Docker containers, source .env before running the test

```bash
docker exec <container> sh -c '
set -a
. /opt/data/.env
set +a
python3 -c "
import urllib.request, json, os
# ... same test script as above ...
"
'
```

Or use a heredoc with a helper script that is written directly inside the container.

### Step 4: Record results in a matrix

| Provider      | Key Var                  | Key Status | Endpoint Status |
|---------------|--------------------------|------------|-----------------|
| OpenCode Zen  | OPENCODE_ZEN_API_KEY     | present    | HTTP 403 ❌     |
| NVIDIA        | NVIDIA_API_KEY           | present    | HTTP 200 ✅     |
| DeepSeek      | DEEPSEEK_API_KEY         | present    | (untested)      |

### Step 5: Switch to a working provider

Once a working key is identified:

1. Update `config.yaml` model section to use the working provider + its model name
2. Verify the new model works: `docker exec <container> python3 -c "..."` with an actual chat completion call
3. Restart the Docker container (NOT just `gateway run --replace` — see Docker diagnostics section)
4. Verify with an actual @-mention

## Pitfalls

- **Don't trust the key format alone.** A key that "looks valid" (e.g. `nvapi-xxx`) may be expired, revoked, or rate-limited. Always test against a live endpoint.
- **Don't skip empty keys.** `API_KEY=` (no value) or `API_KEY=''` means unconfigured — note it as SKIP, not FAIL.
- **Don't test via the Hermes agent's internal API.** Go direct to the provider endpoint. Hermes may cache/fallback/retry internally, masking a dead key.
- **Different providers have different key prefixes** — NVIDIA keys start with `nvapi-`, OpenCode Zen starts with `sk-`, OpenRouter starts with `sk-or-`. This helps disambiguate.
- **Some providers (NVIDIA) offer free tiers** that don't expire but have rate limits. 429 ≠ 401 — they're different failure modes.
- **Two Hermes instances (Mac + Docker) may have different .env files.** Always check both if debugging cross-instance issues.
- **Note which keys are paid vs free** — FAL AI image generation requires payment. If the user says to delete it, do so. Only test keys the user intends to keep.

## Cross-Container Key Testing (Mac ↔ Docker)

When two Hermes agents share the same API key name but report different errors (Mac returns 200, Docker returns 401/403):

1. **Compare the raw key values**, not just the key name. The `.env` files on Mac and Docker mounts may have diverged if they were set from different sources at different times. First compare `wc -c` on the value to detect length differences:
   ```bash
   # Mac
   grep "OPENCODE_ZEN_API_KEY" ~/.hermes/.env | sed 's/.*=//' | wc -c
   # Docker
   docker exec <container> sh -c 'grep "OPENCODE_ZEN_API_KEY" /opt/data/.env | sed "s/.*=//" | wc -c'
   ```
   A length difference (+2 chars on Docker) often means the Docker .env has stray single quotes around the value.

   **But length alone is not enough** — two keys of the same length can be completely different. After checking length, **compare the actual key content** (first 15 + last 10 chars, not the full key):
   ```bash
   # Mac
   echo "Mac: $(grep 'OPENCODE_ZEN' ~/.hermes/.env | sed 's/.*=//' | head -c 15)...$(grep 'OPENCODE_ZEN' ~/.hermes/.env | sed 's/.*=//' | tail -c 10)"
   # Docker
   echo "Docker: $(docker exec <container> sh -c 'grep "OPENCODE_ZEN" /opt/data/.env | sed "s/.*=//; s/\"//g" | head -c 15')...$(docker exec <container> sh -c 'grep "OPENCODE_ZEN" /opt/data/.env | sed "s/.*=//; s/\"//g" | tail -c 10')"
   ```
   If the prefixes don't match (e.g. Mac shows `sk-TOIDG...` but Docker shows `sk-bctyz...`), the keys are completely different — likely one was copied from a different source. Fix by syncing the valid key to the other `.env`.

2. **Check for stray quotes** — Docker `.env` files sometimes wrap key values in single quotes (`'sk-xxx'`) while the Mac `.env` doesn't. These quotes become part of the key value when loaded by Hermes, causing 401/403 auth failures. Check visually:
   ```bash
   docker exec <container> sh -c 'grep "OPENCODE_ZEN_API_KEY" /opt/data/.env'
   ```
   Expected: `OPENCODE_ZEN_API_KEY=sk-xxx...`  ✅ (no quotes)
   Bad:      `OPENCODE_ZEN_API_KEY='sk-xxx...'` ❌ (stray quotes)

   **Fix:** Remove the quotes from the Docker `.env` with `sed`:
   ```bash
   # On the host, for Docker-bind-mounted .env files:
   /usr/bin/sed -i "s/^OPENCODE_ZEN_API_KEY='\\(.*\\)'/OPENCODE_ZEN_API_KEY=\\1/" /path/to/docker/.env
   ```
   Or use Python to read, fix, and rewrite the file.

   **Watch out for XUNFEI_API_KEY too** — if Docker `.env` wraps it in double quotes (`"key"`), the same issue applies.

3. **Compare key prefixes with head/tail** (same as step 1 above) — extract the first 15 and last 10 chars to confirm the actual values match.

4. **Test with curl via Python subprocess (most reliable)** — curl and Python's urllib can produce different HTTP results for the same endpoint due to different TLS libraries, header order, or default headers. Use subprocess to call curl (with args list to avoid shell expansion):
   ```python
   import subprocess, json
   # Read key from .env at runtime (never hardcode in test scripts!)
   with open("/opt/data/.env") as f:
       key = [l.split("=", 1)[1].strip().strip("'\"") for l in f if l.startswith("OPENCODE_ZEN_API_KEY")][0]
   # Use args list — no shell, no expansion issues
   auth = "Authorization: Bearer " + key  # String concat, NOT f-string (see redaction trap below)
   result = subprocess.run(
       ["curl", "-s", "-w", "\n%{http_code}", "https://opencode.ai/zen/v1/chat/completions",
        "-H", "Content-Type: application/json",
        "-H", auth,
        "-d", '{"model":"deepseek-v4-flash-free","messages":[{"role":"user","content":"hi"}],"max_tokens":5}'],
       capture_output=True, text=True, timeout=15
   )
   lines = result.stdout.strip().splitlines()
   print(f"HTTP {lines[-1]}")
   print("\n".join(lines[:-1])[:300])
   ```

   **NOTE:** The `auth` variable is built with string concatenation (`"Bearer " + key`), NOT an f-string (`f"Bearer {key}"`). See pitfall #5 for why.

5. **Watch out for the `write_file` redaction trap** — when using `write_file` to create a test script, the tool redacts `{key}` in f-strings to literal `***`. The resulting file will send `Bearer ***` instead of the actual key, causing spurious 403 errors. **Always read the key from `.env` at runtime** rather than baking it into the script.

   **How to verify the trap has NOT triggered (do this BEFORE running the script):**
   ```bash
   # Read the file back — look for the Authorization header line
   read_file /tmp/test_script.py | grep -i authorization
   ```
   Expected: the file must contain `{key}` as a Python variable reference, NOT literal `***`.
   If you see `Bearer ***` instead of `Bearer `, the file is corrupted — delete it and rewrite without using f-strings with the key variable inside the content parameter.

   **Why this happens:** The `write_file` tool performs content-level redaction on its `content` parameter. When it sees a pattern like `f"...{key}..."` where `key` is a variable that could hold a secret, it replaces `{key}` with `***` in the actual written file. This is NOT just display redaction — the written bytes are corrupted.

   **The only reliable pattern to avoid this:**
   ```python
   # 👎 DON'T DO THIS (write_file redacts {key}):
   header = f"Authorization: Bearer {key}"  # Becomes "Bearer ***" in the file

   # 👍 DO THIS instead (string concat — safe from redaction):
   with open("/path/to/.env") as f:
       key = [l.split("=",1)[1].strip().strip("'\"") for l in f if l.startswith("VAR_NAME")][0]
   auth = "Authorization: Bearer " + key  # String concat, not f-string
   result = subprocess.run(["curl", ..., "-H", auth, ...], ...)
   ```

6. **Unknown key status = test it.** Before reporting "unknown" status for a key in `.env`, test it against its actual API endpoint. Use the weread-skills or relevant skill to find the correct endpoint — don't guess. Common mistakes:
   - WeRead endpoint is `https://i.weread.qq.com/api/agent/gateway`, NOT any public health URL
   - FAL AI health is at `https://fal.run/serverless/health` (but this is paid — ask before testing)
   - Firecrawl health is at `https://api.firecrawl.dev/v1/health` (but this is core config, not a skill)

## Accidental Key Misalignment Between Environments

**Root cause:** Mac local `.env` (`~/.hermes/.env`) and Docker container `.env` (`/opt/data/.env` mounted from host) can contain different values for the same key name, even though they were set up to be "the same."

**How this happens in practice:**
- The Docker `.env` was copied at container creation time from an older version
- A key was updated only in one location (e.g. following a provider dashboard change)
- The Docker bind-mount `.env` was created at a different time than the Mac `.env`
- Editing tools introduced quoting differences (`'sk-xxx'` vs `sk-xxx`)

**Diagnostic:** Run step 1-3 from Cross-Container Key Testing above. If the prefixes match and lengths match but results differ, the keys are the same — the issue is elsewhere.

**Prevention:** Use a single source-of-truth `.env` file and symlink or copy it to Docker mount points. Alternatively, mount the same `~/.hermes/.env` into all containers.

## Testing Pitfall: curl vs Python urllib Discrepancy

**Symptom:** The same API key works with `curl` in the terminal but returns 403 when tested with Python `urllib` from a test script. Code is correct (same endpoint, same headers, same body).

**Possible explanations (check in order):**
1. **Shell quoting in test scripts** — if your test script had the key hardcoded, the `write_file` tool may have redacted `{key}` to `***`. Read the file to confirm (see pitfall #5 above).
2. **Proxy/interceptor** — Python `urllib` may use a different proxy than `curl`. Check `HTTPS_PROXY`/`http_proxy` env vars. This is especially likely in Docker containers where env differs from host.
3. **User-Agent / TLS fingerprint** — Some API gateways (like opencode.ai's Zen) have different behaviour for different User-Agent strings. Setting `User-Agent: curl/8.4.0` in Python can help reproduce curl's behaviour. But this is rare — check #1 first.
4. **Header order** — Some providers are sensitive to header order. `urllib` sends headers in dict iteration order (Python 3.7+ preserves insertion order).

**Preferred method for reliable tests:** Use `subprocess.run` with curl (args list) as shown in step 4 of cross-container testing. This reproduces exactly what will happen in production (the Hermes gateway also uses curl/libcurl internally for HTTP requests).

## API Key Source-of-Truth Convention

When running multiple Hermes instances (Mac + Docker containers) with shared `.env` files:

- **Mac local:** `~/.hermes/.env` — the canonical copy. Update keys here first.
- **Docker (木):** Mounted from host at `/Users/macos/.hermes-docker/minimaxlab/.env`
- **Docker (金):** Mounted from host at `/Users/macos/.hermes-docker/gold/.env`

After updating the Mac canonical copy, sync to Docker mount points:
```bash
# For each key that changed, extract and rewrite:
MAC_KEY=$(grep "^OPENCODE_ZEN_API_KEY=" ~/.hermes/.env | sed 's/^OPENCODE_ZEN_API_KEY=//')
for dest in /Users/macos/.hermes-docker/minimaxlab/.env /Users/macos/.hermes-docker/gold/.env; do
    # Use Python to avoid shell escaping issues with special chars in keys
    python3 -c "
with open('$dest') as f: content = f.read()
old_line = [l for l in content.splitlines() if l.startswith('OPENCODE_ZEN_API_KEY=')][0]
content = content.replace(old_line, 'OPENCODE_ZEN_API_KEY=$MAC_KEY')
with open('$dest', 'w') as f: f.write(content)
"
done
```

This prevents the "same key name, different value" divergence that silently breaks Docker-based agents.
