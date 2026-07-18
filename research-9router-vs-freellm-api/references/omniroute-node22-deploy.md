# OmniRoute on Node 22 via `n` — sidesteps all better-sqlite3 ABI issues

## Problem

System Node 23 (ABI 131) has no prebuilt `better-sqlite3` binary. Manual `npm rebuild better-sqlite3` requires `CXXFLAGS` workaround, and `omniroute runtime repair` claims success but does nothing when `dist/node_modules/better-sqlite3/` lacks `binding.gyp`.

The bundle at `dist/node_modules/better-sqlite3/` is a **prebuilt-only package** — no `binding.gyp`, `src/`, or `deps/`. `npm rebuild` and `node-gyp rebuild` both fail silently because there's nothing to compile.

## Solution: Node 22 via `n`

Install Node 22 LTS alongside the system Node 23 using `n`:

```bash
export N_PREFIX=$HOME/.n
export PATH=$N_PREFIX/bin:$PATH
n 22
hash -r
node -v  # should show v22.23.1+
```

## Rebuild better-sqlite3 for Node 22

Two paths:

### Path A: Main node_modules (has binding.gyp) — preferred

```bash
cd /Users/macos/.n/lib/node_modules/omniroute
npx node-gyp rebuild --directory=node_modules/better-sqlite3
```

This works because the **main** node_modules has full build sources.

### Path B: Copy to dist (where the bundle needs it)

```bash
mkdir -p /Users/macos/.n/lib/node_modules/omniroute/dist/node_modules/better-sqlite3/build/Release
cp /Users/macos/.n/lib/node_modules/omniroute/node_modules/better-sqlite3/build/Release/better_sqlite3.node \
   /Users/macos/.n/lib/node_modules/omniroute/dist/node_modules/better-sqlite3/build/Release/
```

### Path C: Full uninstall + reinstall (cleans all cached builds)

Sometimes the cleanest fix — removes any stale prebuilt binaries:

```bash
pkill -f omniroute
rm -rf /usr/local/lib/node_modules/omniroute
npm uninstall -g omniroute
npm cache clean --force
npm install -g omniroute
```

The reinstall triggers a fresh `better-sqlite3` build matching the current Node ABI.

## Starting OmniRoute with Node 22

The omniroute binary uses `#!/usr/bin/env node` which resolves to the **first** `node` in PATH. System Node 23 is at `/usr/local/bin/node`, so you must override PATH:

```bash
export PATH=/Users/macos/.n/bin:$PATH
/Users/macos/.n/bin/node /Users/macos/.n/lib/node_modules/omniroute/bin/omniroute.mjs --no-open
```

Or for background processes with `terminal(background=true)`:

```bash
export PATH=/Users/macos/.n/bin:$PATH
/Users/macos/.n/bin/node /Users/macos/.n/lib/node_modules/omniroute/bin/omniroute.mjs --no-open
```

The `export PATH` in the background command ensures node resolves to v22.

## Cookie-based API Auth for Provider Key Injection

OmniRoute's `/api/*` endpoints require auth. The login endpoint returns a cookie:

```bash
# Login and save cookie
curl -c /tmp/omniroute_cookies.txt -X POST http://localhost:20128/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"your-password"}'
# Response: {"success":true} + Set-Cookie: auth_token=...

# Use cookie for subsequent API calls
curl -s -b /tmp/omniroute_cookies.txt -X POST http://localhost:20128/api/providers \
  -H "Content-Type: application/json" \
  -d '{"provider":"nvidia","name":"NVIDIA NIM","apiKey":"nvapi-xxxxx"}'
# Response: {"connection":{"id":"...","provider":"nvidia",...}}
```

## Provider ID Discovery

Not all provider IDs from the model list are valid for `POST /api/providers`. Tested working (return 201):

| Provider ID | Works? | Notes |
|-------------|--------|-------|
| `nvidia` | ✅ | NVIDIA NIM API |
| `opencode` | ✅ | OpenCode Zen API |
| `openai` | ✅ | Standard OpenAI API |
| `deepseek` | ✅ | DeepSeek API |
| `siliconflow` | ✅ | SiliconFlow API |
| `fireworks` | ✅ | Fireworks AI |
| `together` | ✅ | Together AI |
| `cerebras` | ✅ | Cerebras |
| `anthropic` | ✅ | Anthropic |
| `groq` | ✅ | Groq |
| `mistral` | ✅ | Mistral |
| `google` | ✅ | Google AI |
| `openrouter` | ✅ | OpenRouter |
| `oc` | ❌ | Not a valid provider ID (built-in prefix only) |
| `agnes` | ❌ | Not a valid provider ID |
| `agnesis` | ❌ | Not a valid provider ID |
| `nvidia-nim` | ❌ | 400 Invalid provider |
| `deepseek-ai` | ❌ | 400 Invalid provider |

Most API-key providers accept `sk-...` prefix keys. NVIDIA uses `nvapi-...` prefix.

## Key Observations

| Key Type | Source | Provider ID | Works? | Notes |
|----------|--------|-------------|--------|-------|
| NVIDIA ×3 | key.txt | `nvidia` | ✅ Keys accepted, model routing may need tuning |
| OpenCode Zen ×3 | key.txt | `opencode` | ✅ Keys accepted, returned 401 on test (needs base URL) |
| Agnes ×3 | key.txt | `openai` | ⚠️ Keys accepted but sent to api.openai.com — need actual base URL |
| Built-in oc/ pool | OmniRoute | (built-in) | ✅ `oc/deepseek-v4-flash-free` works out of box |

## When to Clean Install vs Runtime Repair

| Symptom | Best Fix |
|---------|----------|
| `out of memory` probe loop | Clean DB + restart |
| `NODE_MODULE_VERSION mismatch` | Switch Node via `n` + rebuild |
| `binding.gyp not found` in dist | Copy .node from main node_modules |
| Fresh install succeeds but OOM on restart | Reinstall (npm install -g overwrites stale builds) |
| `runtime repair` says OK but still broken | Use manual rebuild instead |
