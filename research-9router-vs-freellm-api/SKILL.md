---
name: research-9router-vs-freellm-api
description: OmniRoute (9Router) AI gateway — install, native-module repair, upgrade, provider config, and comparison with FreeLLM-API for the Angelife fleet.
---

# OmniRoute (9Router) AI Gateway Operations

OmniRoute (née 9Router, npm package `omniroute`) is a unified AI gateway with auto-fallback across multiple providers and keys. Exposes an OpenAI-compatible `/v1` endpoint.

| Item | Value |
|------|-------|
| Port | `20128` |
| API | `http://localhost:20128/v1` |
| Dashboard | `http://localhost:20128` |
| Data dir | `~/.omniroute/storage.sqlite` (SQLite) |
| Config | `~/.omniroute/.env` |

---

## Installation

```bash
npm install -g omniroute@latest
```

### Native Module Compilation (macOS, Node 23+)

OmniRoute depends on `better-sqlite3` (native C++ addon). On macOS with Node 23 (ABI 131), `prebuild-install` has no prebuilt binary, and `node-gyp` may fail with:

```
fatal error: 'climits' file not found
```

This happens when the macOS SDK include path isn't found by `node-gyp`. Xcode CLT is installed but the compiler doesn't resolve the C++ standard library headers automatically.

**Fix — set CXXFLAGS before rebuild:**
```bash
export CXXFLAGS="-I/Library/Developer/CommandLineTools/SDKs/MacOSX.sdk/usr/include/c++/v1"
cd /usr/local/lib/node_modules/omniroute
npm rebuild better-sqlite3
```

After rebuild, verify the native module loads:
```bash
node -e "const b = require('/usr/local/lib/node_modules/omniroute/node_modules/better-sqlite3'); \
  const db = new b(':memory:'); db.exec('CREATE TABLE t (x INT)'); \
  db.prepare('INSERT INTO t VALUES(1)').run(); \
  console.log('OK:', db.prepare('SELECT * FROM t').all());"
```

**`omniroute runtime repair`** — built-in repair command that also generates `STORAGE_ENCRYPTION_KEY` in `~/.omniroute/.env`. May need the same CXXFLAGS workaround.

### Node Version Compatibility

v3.8.45 warns: "Node.js v23.11.0 is outside OmniRoute's approved secure runtime policy."
- **Supported:** 22.22.2+ (22.x LTS), 24.0.0+, 25.0.0+, 26.0.0+
- **Runs on 23.x:** ✅ with CXXFLAGS workaround
- **Recommended: use Node 22 LTS** via `n` to avoid all ABI issues (see `references/omniroute-node22-deploy.md`)
- **No prebuilts for ABI 131:** must compile from source

---

## Upgrade (v3.6.x → v3.8.x)

**Critical — DB format changed.** v3.8.45 probes old v3.6.5 DB, renames it to `storage.sqlite.probe-failed-<timestamp>`, creates a 0-byte replacement, then hangs at "⏳ Starting server..." forever.

**Fix — clean DB before first v3.8.x start:**
```bash
kill $(pgrep -f omniroute)
rm -f ~/.omniroute/storage.sqlite*
rm -f ~/.omniroute/db_backups/*
omniroute --no-open     # creates fresh schema
```

The new DB auto-runs 20+ migrations. Takes 5-10s on first start. After that, Dashboard returns 307 (login redirect) instead of 500.

**Consequence:** all manually configured providers from v3.6.x are lost. Must re-add (see "Provider Configuration via SQLite" below).

---

## Provider Configuration

### Option A: Dashboard

Visit `http://localhost:20128` → set password → add providers via UI.

### Option B: CLI `omniroute nodes add` (Preferred — avoids Dashboard auth + SQLite probe issues)

The CLI manages provider nodes through OmniRoute's internal API. Requires the service to be running and database healthy.

```bash
# Add a provider node (e.g. NVIDIA NIM)
omniroute nodes add \
  --provider nvidia \
  --base-url https://integrate.api.nvidia.com/v1 \
  --name "NVIDIA NIM" \
  --region auto \
  --weight 100 \
  --auth-header "Authorization=bearer nvapi-xxxxx"

# List configured nodes
omniroute nodes list

# Test a specific node
omniroute nodes test <node-id>

# Remove a node
omniroute nodes remove <node-id>
```

`--auth-header` format is `HeaderName=value` (key=value). The CLI reads `~/.omniroute/.env` for `STORAGE_ENCRYPTION_KEY` on startup. If the DB is in a probe-failure loop (pitfall #13), the CLI will fail — fix the DB first.

### Option C: Direct SQLite (when Dashboard API is auth-blocked)

**Schema:**

`provider_nodes` — defines a provider type:
```sql
CREATE TABLE provider_nodes (
    id TEXT PRIMARY KEY,
    type TEXT NOT NULL,       -- 'openai' / 'anthropic' etc.
    name TEXT NOT NULL,
    prefix TEXT,
    api_type TEXT,
    base_url TEXT,
    chat_path TEXT,
    models_path TEXT,
    created_at TEXT,
    updated_at TEXT
);
```

`provider_connections` — API keys:
```sql
CREATE TABLE provider_connections (
    id TEXT PRIMARY KEY,
    provider TEXT NOT NULL REFERENCES provider_nodes(id),
    auth_type TEXT,          -- 'bearer'
    name TEXT,
    priority INTEGER,       -- lower = tried first (auto-fallback)
    is_active INTEGER DEFAULT 1,
    api_key TEXT,
    default_model TEXT,
    created_at TEXT,
    updated_at TEXT
);
```

**Add a node:**
```bash
sqlite3 ~/.omniroute/storage.sqlite "
INSERT OR IGNORE INTO provider_nodes
  (id, type, name, api_type, base_url, created_at, updated_at)
VALUES
  ('nvidia', 'openai', 'NVIDIA', 'openai',
   'https://integrate.api.nvidia.com/v1',
   datetime('now'), datetime('now'));
"
```

**Add a connection (API key):**
```bash
sqlite3 ~/.omniroute/storage.sqlite "
INSERT INTO provider_connections
  (id, provider, auth_type, name, priority, is_active, api_key,
   default_model, created_at, updated_at)
VALUES
  (hex(randomblob(16)), 'nvidia', 'bearer', 'NVIDIA #1', 1, 1,
   'nvapi-...', '', datetime('now'), datetime('now'));
"
```

**Verify:**
```bash
sqlite3 ~/.omniroute/storage.sqlite "
SELECT pn.id AS provider, pc.name, pc.priority, pc.is_active,
       substr(pc.api_key,1,12)||'...' AS key_prefix
FROM provider_connections pc
JOIN provider_nodes pn ON pc.provider = pn.id
ORDER BY pn.id, pc.priority;
"
```

### Auto-Fallback Between Keys

OmniRoute tries `provider_connections` ordered by `priority` within the same `provider`. If a key returns 5xx / 429 / timeout, it falls back to the next priority. Verified working for OpenCode Zen (3 keys, v3.6.5).

---

## Built-in Providers (v3.8.45+)

v3.8.45+ lists 92+ models across 8+ provider groups. **The `oc/` provider has a built-in key pool that works with zero manual config, but verified testing shows only 1 model actually responds 200:**

| Prefix | Models Listed | Verified Working |
|--------|---------------|-----------------|
| `oc/` | 8 models inc. `deepseek-v4-flash-free`, `minimax-m2.5-free`, `qwen3.6-plus-free`, etc. | **Only `oc/deepseek-v4-flash-free`** ← the one Hermes needs |
| `auto/` | `best-coding`, `best-reasoning`, `best-fast`, `best-vision`, `best-chat`, `pro-*` (29) | ❌ All 500 |
| `tllm/` | `GPT_5_4`, `GPT_5_3`, `GPT_5_2`, `GPT_5_1` + 22 more (26) | ❌ All 500 |
| `nvidia/` | NVIDIA-hosted models (131) | ✅ With valid `nvapi-` keys. Direct connection works on this network. See "Known Provider Issues" table. |
| `aug/` | Claude Sonnet 4.6, Opus 4.6, Haiku 4.5 (12) | ❌ All 500 |
| `ddgw/` | `gpt-4o-mini`, `gpt-5-mini`, `claude-3-5-haiku`, `llama-4-scout` (6) | ❌ All 500 |
| `mcode/`, `pepper/`, `veo-free/`, `no-think/` | 10 models total | ❌ All 500 |
| `opencode-zen/` | Custom provider (free models) | ✅ 5 free models verified 200 |

**⚠️ Model list ≠ working models.** Do not claim more models work than verified by actual 200 response. The `oc/` built-in key pool covers only `deepseek-v4-flash-free`. Other listed `oc/` models share the same prefix but return 500.

**Verified working:**
```bash
curl -s http://localhost:20128/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"oc/deepseek-v4-flash-free","messages":[{"role":"user","content":"hi"}],"max_tokens":10,"stream":false}'

---

## Runtime Repair Limitations

The built-in `omniroute runtime repair` command may claim success but do nothing when `dist/node_modules/better-sqlite3/` lacks `binding.gyp`. This is because the dist bundle ships a **prebuilt-only package** without compilation sources. The repair command's "OK" output is misleading.

**Manual rebuild paths** (see `references/omniroute-node22-deploy.md`):
- **Path A:** Compile the main `node_modules/better-sqlite3` (has binding.gyp) via `node-gyp rebuild`, then copy the `.node` file to `dist/node_modules/better-sqlite3/build/Release/`
- **Path B:** Complete `npm uninstall -g omniroute` + reinstall — fresh install triggers correct ABI build
- **Path C:** Switch to Node 22 via `n` and rebuild — avoids all ABI version conflicts

## Dashboard Password Recovery

When the Dashboard password is lost (or the default `CHANGEME` was changed to an unknown value), you can recover it by directly updating the bcrypt hash in SQLite:

```bash
# Generate hash using OmniRoute's built-in bcryptjs (NOT npm bcrypt)
export PATH=/Users/macos/.n/bin:$PATH
HASH=$(node -e "const b=require('/Users/macos/.n/lib/node_modules/omniroute/node_modules/bcryptjs'); console.log(b.hashSync('1234567890',12));")
sqlite3 ~/.omniroute/storage.sqlite "UPDATE key_value SET value='\"$HASH\"' WHERE key='password';"
```

Alternatively, disable login requirement entirely (works without restart — read from DB at runtime):
```bash
sqlite3 ~/.omniroute/storage.sqlite "UPDATE key_value SET value='false' WHERE key='requireLogin';"
```
After this, Dashboard and API are accessible without authentication.

**Pitfall:** The settings `password` and `requireLogin` are stored as individual rows in `key_value`, keyed by name (e.g. key=`password`, value=`"$2b$12$..."`). They are NOT nested inside a JSON `settings` object. The bcrypt hash must be wrapped in JSON double-quotes in the SQL UPDATE.

## API Cookie Auth for Management Endpoints

OmniRoute's `/api/*` endpoints require authentication via session cookie. The `/v1/*` (chat completions, model list) work without auth by default.

```bash
# Login and save cookie
curl -c /tmp/omniroute_cookies.txt -X POST http://localhost:20128/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"password":"your-password"}'
# Response: {"success":true} + Set-Cookie: auth_token=...

# Use cookie for subsequent API management calls
curl -s -b /tmp/omniroute_cookies.txt http://localhost:20128/api/settings/proxy
```

### Management API Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/auth/login` | POST | Login, returns session cookie |
| `/api/settings/proxy` | GET/PUT/DELETE | Legacy global proxy config (cookie auth) |
| `/api/v1/management/proxies` | GET/POST/PATCH/DELETE | New proxy registry CRUD |
| `/api/settings/api-keys` | GET | List API keys for `/v1/*` access |
| `/api/providers` | POST | Add/update provider API key connections |

Validated provider IDs for `POST /api/providers`: `nvidia`, `opencode`, `openai`, `anthropic`, `google`, `openrouter`, `groq`, `mistral`, `deepseek`, `siliconflow`, `fireworks`, `together`, `cerebras` (all return 201). Invalid: `oc`, `agnes`, `agnesis`, `nvidia-nim`, `deepseek-ai`.

## Proxy Configuration

OmniRoute has a **4-level proxy system** (global → provider → combo → connection) for routing upstream AI traffic through HTTP, HTTPS, or SOCKS5 proxies. This is necessary when the local network has restricted internet access.

### Set Global Proxy

```bash
curl -s -b /tmp/omniroute_cookies.txt -X PUT http://localhost:20128/api/settings/proxy \
  -H "Content-Type: application/json" \
  -d '{"level": "global", "proxy": {"type":"http","host":"192.168.1.8","port":10808}}'
```

Verify with:
```bash
curl -s -b /tmp/omniroute_cookies.txt http://localhost:20128/api/settings/proxy
```

### Proxy Troubleshooting

The proxy is applied via Node.js `undici` dispatcher. Known failure modes:

| Symptom | Log line | Likely cause |
|---------|----------|-------------|
| Timeout after 16-30s | `request_signal_aborted` | `undici` proxy agent connection failure — try different proxy type |
| `proxy=global:192.168.1.8 status=error` | ProxyEgress | Proxy is assigned but undici can't connect |
| `proxy=direct status=error` | ProxyEgress | No proxy assigned; direct connection fails |

**Key insight:** `curl -x socks5://host:port` working does NOT guarantee OmniRoute's internal proxy works. The `undici` HTTP client may have compatibility issues with certain proxy implementations. When this happens:
1. Try switching between `socks5` and `http` proxy types
2. Verify via `ProxyFetch` logs that the proxy context is being applied (`Applied request proxy context: http://...`)
3. If undici fails, set `HTTP_PROXY`/`HTTPS_PROXY` env vars before starting the OmniRoute Node process — Node 22's native fetch also uses undici but may handle it differently
4. Direct curl calls from the CLI (outside OmniRoute) work fine with `-x`; the issue is specifically in undici's proxy handling

### Provider Connection Status

Check key/service health in the database:

```sql
-- View all provider connections with their live status
sqlite3 ~/.omniroute/storage.sqlite "
SELECT provider, name, test_status, error_code, substr(last_error,1,60) as error,
       is_active, proxy_enabled
FROM provider_connections
ORDER BY provider, priority;
"
```

| `test_status` | Meaning |
|---------------|---------|
| `active` | Key works, last test passed |
| `expired` | Key returned 401/403 — invalid or revoked |
| `unknown` | Not yet tested (provider type doesn't support test) |
| `error` | Test failed (may be test framework limitation, not actual key) |

**Pitfall:** `test_status = 'error'` with message `Provider test not supported` means the CLI test framework lacks a test handler for that provider type. The actual key may still work when called through `/v1/chat/completions`. Always verify with an actual chat completion call, not just the CLI test.

### Built-in Provider OAuth vs API-Key Incompatibility

Some built-in OmniRoute providers (like `opencode`) use **OAuth** authentication. API keys stored via `provider_connections` are NOT picked up by OAuth-based executors. This manifests as:

- Log: `Using opencode account: noauth...`
- Response: `401 Missing API key`
- `test_status: unknown` (CLI can't test)

**Fix:** Use the provider as an **OpenAI-compatible custom endpoint** instead, pointing at the correct upstream API:

| Service | Correct Endpoint | Provider Type |
|---------|-----------------|---------------|
| OpenCode Zen (free models) | `https://opencode.ai/zen/v1` | OpenAI-compatible |
| OpenCode Zen (GPT models) | `https://opencode.ai/zen/v1/responses` | OpenAI Responses |
| OpenCode Zen (Anthropic) | `https://opencode.ai/zen/v1/messages` | Anthropic Messages |
| NVIDIA NIM | `https://integrate.api.nvidia.com/v1` | OpenAI-compatible |

Not all models listed under `opencode/` prefix in OmniRoute's model catalog are accessible with API keys — many are OAuth-only. The proper way to use OpenCode Zen API keys is as a separate OpenAI-compatible provider, NOT through the built-in `opencode` OAuth provider.

### Model Catalog Sources

The model list in `/v1/models` comes from TWO sources:
1. **Built-in provider registry** — Hardcoded in OmniRoute source (`providerRegistry.ts`)
2. **Imported model lists** — Stored in `key_value` table as `provider:connectionId` → JSON array

The `provider:connectionId` entries are created when a provider is connected and its model catalog is synced. These are separate from the `provider_connections` table.

### CLI Subcommand Variations

| Command | Purpose |
|---------|---------|
| `omniroute providers list` | List configured connections (alias: `omniroute provider list`) |
| `omniroute providers available` | List provider catalog (built-in types) |
| `omniroute providers test <name>` | Test a provider connection |
| `omniroute keys list` | List configured API keys (from provider_connections) |
| `omniroute keys list --json` | JSON output with connection IDs |
| `omniroute combo list` | List combos |
| `omniroute doctor` | System diagnostics (DB, native modules, config) |
| `omniroute reset-password` | Interactive password reset (requires 8+ chars)

## Known Provider Issues

| Provider | Via OmniRoute | Direct curl | Notes |
|----------|--------------|-------------|-------|
| **OpenCode Zen** (`oc/` built-in) | ✅ v3.8.46 | ✅ | Built-in pool works. Only `deepseek-v4-flash-free` verified 200. |
| **OpenCode Zen** (API keys, via `opencode/` provider) | ❌ (OAuth only) | ✅ via `https://opencode.ai/zen/v1` | The built-in `opencode` provider uses OAuth, not API keys. Keys stored in `provider_connections` are ignored (log says `noauth...`). **Workaround:** create a custom OpenAI-compatible provider node + connection via `POST /api/provider-nodes` + `POST /api/providers` (see section below). |
| **opencode-zen/** (custom provider) | ✅ v3.8.46 | ✅ 200 | Custom OpenAI-compatible provider with `base_url: https://opencode.ai/zen/v1`. Supports 5 free models: `deepseek-v4-flash-free`, `mimo-v2.5-free`, `hy3-free`, `nemotron-3-ultra-free`, `north-mini-code-free`. Paid models return `CreditsError: No payment method`. |
| **NVIDIA** (via built-in `nvidia/` prefix) | ✅ Direct (no proxy) | ✅ 200 | API keys (nvapi-...) work. Models list 131 items. **Does NOT need proxy** on networks where `integrate.api.nvidia.com` is directly reachable. Proxy may actually **block** NVIDIA — OmniRoute's undici proxy agent fails with `request_signal_aborted` on some proxy setups. Always test direct first. Rate-limited: free tier has burst limits. |
| **Agnes** (via `openai/` prefix) | ❌ Keys expired | ❌ 401 | 3 keys all return `Incorrect API key provided`. Remove dead connections via SQLite: `DELETE FROM provider_connections WHERE provider='openai' AND test_status='expired';` |
| **auto/best-*** | ❌ All 500 | — | Requires configured `provider_connections` to function; built-in oc/ pool doesn't power auto-routing. |

---

## Custom OpenAI-Compatible Providers via provider_nodes API

Some upstream services (like OpenCode Zen) are **not built-in OmniRoute providers** and cannot be configured via the standard CLI `keys add` command (which only works for known provider IDs). The solution is to register them as custom OpenAI-compatible providers through the `provider_nodes` system.

### Flow

1. **Create a provider node** (defines the API endpoint)
2. **Create provider connections** (stores your API keys)
3. **Verify models appear** in `/v1/models`
4. **Test** with a chat completion call

### Step 1: Create Provider Node

```bash
# Login first (cookie required for all /api/* calls)
curl -c /tmp/omniroute_cookies.txt -X POST http://localhost:20128/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"password":"your-password"}'

# Register a custom OpenAI-compatible provider
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

**Required fields:**
| Field | Value | Notes |
|-------|-------|-------|
| `type` | `"openai-compatible"` or `"anthropic-compatible"` | Only these two are valid |
| `name` | Human-readable name | e.g. "OpenCode Zen" |
| `prefix` | Model prefix | Appears in model IDs as `<prefix>/<model-id>` |
| `baseUrl` | Upstream API base | Must not end with `/v1` path — that's added by `chatPath` |
| `apiType` | `"chat"` | Only supported value |
| `chatPath` | `"/v1/chat/completions"` | Appended to baseUrl for chat calls |
| `modelsPath` | `"/v1/models"` | Appended to baseUrl for model listing |

**Response:**
```json
{"node":{"id":"openai-compatible-chat-<uuid>","type":"openai-compatible","name":"OpenCode Zen","prefix":"opencode-zen","baseUrl":"https://opencode.ai/zen/v1",...}}
```

### Step 2: Create Provider Connections (Add API Keys)

```bash
curl -s -b /tmp/omniroute_cookies.txt -X POST http://localhost:20128/api/providers \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "opencode-zen",    # MUST match the provider node prefix
    "authType": "apikey",
    "name": "OC Zen Main",
    "apiKey": "sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxx"
  }'
```

Repeat for each API key (OmniRoute auto-fallbacks between keys in the same provider).

### Step 3: Verify Models

```bash
# Check that custom provider models appear
curl -s http://localhost:20128/v1/models | python3 -c "
import json,sys
data = json.load(sys.stdin)
zen = [m['id'] for m in data['data'] if 'opencode-zen' in m['id']]
for m in zen: print(f'  {m}')
print(f'Total: {len(zen)}')
"
```

### Step 4: Test Chat Completion

```bash
curl -s -w "\nHTTP %{http_code}\n" --max-time 30 http://localhost:20128/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model": "opencode-zen/deepseek-v4-flash-free", "messages": [{"role": "user", "content": "hi"}], "max_tokens": 10}'
```

The response headers include `x-omniroute-provider: opencode-zen` to confirm routing.

### Gotchas

- **The `provider` field in `POST /api/providers` must match the `prefix` from Step 1**, not the `name` or the node `id`.
- **Custom providers are NOT visible to the CLI** — `omniroute keys add opencode-zen` returns `Unknown provider: opencode-zen` because the CLI only knows built-in providers.
- **Model discovery is manual** — OmniRoute fetches `/v1/models` from the upstream to populate the model list, but some providers may return different sets depending on auth context. Verify by actual call.
- **The provider node appears in `provider_nodes` SQLite table**, NOT in `provider_connections` as a row (though the *connection* keys are in `provider_connections`).

---

## Combo Management

Combos provide ordered fallback across multiple models/providers. When the primary model fails, OmniRoute tries the next in sequence.

### Create a Combo via API

```bash
curl -s -b /tmp/omniroute_cookies.txt -X POST http://localhost:20128/api/combos \
  -H "Content-Type: application/json" \
  -d '{
    "name": "wuxing-free",
    "strategy": "priority",
    "models": [
      {"model": "oc/deepseek-v4-flash-free"},
      {"model": "opencode-zen/deepseek-v4-flash-free"},
      {"model": "nvidia/deepseek-ai/deepseek-v4-flash"}
    ]
  }'
```

| Field | Description |
|-------|-------------|
| `name` | Combo identifier used as model name in `/v1/chat/completions` |
| `strategy` | `"priority"` — tries models in listed order |
| `models` | Ordered list of model objects with `model` key in `<prefix>/<model-id>` format |

### Use a Combo

Call it as a model in chat completions:
```bash
curl -s http://localhost:20128/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model": "wuxing-free", "messages": [{"role": "user", "content": "hi"}], "max_tokens": 5}'
```

### Set Default Combo

```sql
sqlite3 ~/.omniroute/storage.sqlite "UPDATE key_value SET value='\"wuxing-free\"' WHERE key='activeComboId';"
```

### List Combos via CLI

```bash
omniroute combo list
```

---

## Connection Cleanup

Remove stale/dead provider connections via SQLite or API.

### SQLite Direct Delete

```bash
# Remove expired Agnes (openai) connections
sqlite3 ~/.omniroute/storage.sqlite "DELETE FROM provider_connections WHERE provider='openai' AND test_status='expired';"

# Remove OAuth opencode connections (replaced by custom provider)
sqlite3 ~/.omniroute/storage.sqlite "DELETE FROM provider_connections WHERE provider='opencode' AND test_status='error';"
sqlite3 ~/.omniroute/storage.sqlite "DELETE FROM provider_connections WHERE provider='opencode' AND test_status='unknown';"
```

### API-Based Delete

The `DELETE /api/providers` endpoint removes a connection by ID. The CLI `omniroute keys remove <provider>` is interactive (requires confirmation prompt).

```bash
# Non-streaming
curl -s http://localhost:20128/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"oc/deepseek-v4-flash-free","messages":[{"role":"user","content":"Hello"}],"max_tokens":100,"stream":false}'

# v3.8.45 defaults to streaming — omit `stream` for SSE chunks
```

### Model naming convention
`<provider-prefix>/<model-id>` — e.g., `oc/deepseek-v4-flash-free`, `nvidia/deepseek-ai/deepseek-v4-flash`.

---

## Hermes Integration

### Recommended Architecture: OmniRoute as Primary Provider

**Critical: Do NOT put upstream providers directly in `fallback_providers`.** Route everything through OmniRoute first. When upstream providers (opencode-zen, nvidia, etc.) are called directly by Hermes, a failure in one provider takes down the entire bot — there's no intermediate layer to handle auto-fallback.

Correct config structure:

```yaml
providers:
  omniroute:
    base_url: http://localhost:20128/v1
    api_key: not-needed       # OmniRoute manages its own key pool

# All fallbacks go through OmniRoute, which handles its own provider-level routing
fallback_providers:
  - provider: omniroute
    model: wuxing-free        # Combo defined in OmniRoute
  - provider: omniroute
    model: oc/deepseek-v4-flash-free
```

**Why this matters (2026-07-12 diagnosis):** The previous config had `opencode-zen-primary`, `opencode-zen-backup-3`, `nvidia-primary` etc. as direct fallback_providers. When ALL of them simultaneously returned 429/timeout/connection-error, the bot went completely silent. If these had been routed through OmniRoute, the built-in `oc/` key pool or combo routing would have provided fallback paths before Hermes even knew there was a problem.

### Startup Checklist

When diagnosing "bot silent" issues, always verify OmniRoute is running FIRST:

```bash
lsof -i :20128 2>/dev/null || echo "OmniRoute NOT running — start it"
```

To start OmniRoute (requires Node 22 via `.n`):

```bash
export PATH=/Users/macos/.n/bin:$PATH
cd ~/.omniroute
node /Users/macos/.n/lib/node_modules/omniroute/bin/omniroute.mjs serve --daemon --no-open
```

⚠️ **Do NOT use** `/usr/local/lib/node_modules/omniroute/dist/server/index.js` — that path does not exist in the installed layout. The entry point is `bin/omniroute.mjs`.

⚠️ **Do NOT use** `omniroute server start` — the CLI subcommand is `serve`, not `server start`.

### Alternative: Direct Provider Config (if OmniRoute unavailable)

If OmniRoute cannot run, at least ensure multiple providers are configured as fallbacks. But this is inferior — you lose OmniRoute's compression, combo routing, and unified dashboard.

---

## User Preference — Zero-Config First

When installing for Angelife: **prefer built-in providers over manual key configuration.** The `oc/` provider in v3.8.45 works out of the box with 8 models including `deepseek-v4-flash-free`. Only add manual provider_connections when the built-in pool doesn't cover the needed model. This avoids the probe-failed DB issue on restart.

Decision shorthand: if the built-in `oc/` pool provides the model you need (as it does for the Hermes fleet's default model), **stop there**. Do not proactively add NVIDIA/Agnes manual keys unless the user asks.

## Comparison: OmniRoute vs FreeLLM-API

**Core positioning:**
- **FreeLLM-API** (3001) = "万能钥匙串" — 堆叠 14-16 个免费 Tier（Groq, Cerebras, Mistral, 硅基流动等），做好测速、探活、轮询和 429 自动切。通用 LLM 代理，适用 Web 聊天、轻量脚本、日常倒腾。
- **OmniRoute** (20128) = "IDE 专属外挂" — 专为 Claude Code / Cursor / Cline 等 AI 编程工具的高并发、吃上下文场景设计。核心痛点是：不是找不到 Key，而是"读写项目上下文太烧钱、高并发瞬间熔断"。

**Key technology differences:**

| Feature | FreeLLM-API | OmniRoute |
|---------|-------------|-----------|
| **Traffic compression** | Passthrough (no compression) | **Caveman 堆叠压缩 + RTK 算法** — 针对 git diff, grep, npm build 日志等冗余文本，高比例压缩 15%-95% 无效 Token |
| **Fallback strategy** | Flat round-robin (A down → B) | **4-Tier 回退分流** — 区分已购订阅 / 便宜付费 / 免费 / 备用，按 Token 量自动把长文本塞给高上下文免费渠道（如 Gemini Free） |
| **Model ecosystem** | 聚合各平台公版小模型（Llama, DeepSeek, Qwen） | 强优化对接 Claude 3.5 Sonnet / Gemini Pro 等编程梯队模型，聚合 OpenRouter 等上游中转免费池 |
| **Role** | 通用 LLM 代理 | 编程场景专用路由网关 |
| **Key management** | Built-in pool or single key | Multi-key auto-fallback (priority), circuit breaker |
| **Dashboard** | Web UI (直观好管理) | Web UI (auth-gated) |
| **Startup** | Docker container | Native Node (npm install + compile) |
| **MCP support** | ❌ | `omniroute --mcp` ✅ |
| **Anthropic ↔ OpenAI** | ❌ | Translation layer ✅ |

### When to use which

- **FreeLLM-API**: 环境已跑通、日常写小脚本、轻量使用。Web Dashboard 更直观好管理。适合手机端轻量聊天场景。
- **OmniRoute**: 深度依赖 Cline / Claude Code 等重度上下文 CLI 编程助手，频繁被各平台免费额度灌满、限流。Caveman 压缩 + 4-Tier 回退让你薅得更久、写得更顺畅。
- **Both**: 两家本质同类产品，底层逻辑一样（聚合免费 Key 做成 OpenAI 兼容端点供 Cursor/Cline 使用）。从"日常敲代码"视角看定位和优化侧重点不同。Hermes 中可通过 `fallback_providers:` 并存，OmniRoute 为主、FreeLLM-API 为备胎。

### Migration guide

| Situation | Choice |
|-----------|--------|
| Light usage, existing FreeLLM-API working | Stay on FreeLLM-API |
| Starting to hit free-tier rate limits | Move to OmniRoute (compression saves tokens) |
| Running Cursor/Cline daily | OmniRoute is the default |
| Phone-based light agents (水/金) | OmniRoute for future-proofing, FreeLLM-API as fallback |

---

## Pitfalls

26. **Combo models may return empty streams** — When calling a combo model (e.g. `wuxing-free`) through OmniRoute, the response may be an empty stream with no `finish_reason`. Hermes logs this as: `Provider returned an empty stream with no finish_reason (possible upstream error or malformed SSE response)`. **Fix:** use direct model IDs (`oc/deepseek-v4-flash-free`, `opencode/deepseek-v4-flash-free`) instead of combos in Hermes `model.default`. Combos work fine for manual curl testing but can fail in Hermes due to streaming/SSE handling differences.

27. **OmniRoute startup command is NOT `omniroute server start`** — The CLI subcommand is `serve`, not `server start`. Correct: `node bin/omniroute.mjs serve --daemon --no-open`. Using `server start` gives "too many arguments" error. Also do NOT use `/usr/local/lib/node_modules/omniroute/dist/server/index.js` — that path does not exist in the installed layout.

28. **Hermes config change requires gateway restart** — After editing `config.yaml` (provider/model/fallback), you MUST restart the gateway (`hermes gateway restart`). The old config values remain in memory until restart. A restart without `--replace` may fail if launchd-managed process is still alive — use `hermes gateway restart` which handles launchd gracefully.

29. **Rate limit on free key pools is cumulative** — The `oc/` built-in free key pool has burst rate limits. Rapid consecutive tests (even with 30s curl calls) can exhaust the quota. If you see 429, wait 2-5 minutes before retrying. Multiple concurrent sessions amplify this — each Hermes agent session holding a connection while retrying makes the pool fill faster.

1. **Node 23 needs CXXFLAGS** — `npm rebuild` fails without the SDK include path workaround
2. **Upgrade requires full DB wipe** — v3.6.x → v3.8.x broken; `rm storage.sqlite*` first
3. **Dashboard auth blocks API** — `/api/*` endpoints return 401 without login; `/v1/*` (chat) works fine
4. **Built-in `oc/` providers need zero config** — don't waste time adding manual OpenCode Zen keys
5. **Model list ≠ working models** — OmniRoute lists what the provider advertises; actual availability depends on key + quota
6. **Streaming default** — v3.8.45 streams; add `"stream": false` for single-response
7. **NVIDIA auth broken in v3.6.5** — OmniRoute's account auth step 404s; direct curl works
8. **v3.8.45 warns on Node 23** — still runs correctly after native rebuild; warning is informational
9. **SQLite is per-version format** — never assume backward compatibility on upgrade
10. **v3.8.45 probe rejects SQLite-writes + restart** — INSERTing provider_connections into a running v3.8.45 database works for that session, but on the next restart the probe renames the DB to storage.sqlite.probe-failed-<ts> and hangs at "Starting server...". The probe checks metadata that manual SQLite inserts don't satisfy. Workaround: use Dashboard API once auth is set up.
11. **auto/best-* returns 500 with no configured connections** — v3.8.45 shows 29 auto-route models in /v1/models, but they return 500 on use until at least one provider_connection row exists. The built-in oc/ key pool is separate and does NOT power auto-routing.
12. **Streaming vs non-streaming response parsing** — curl -s without stream:false returns SSE chunks (data: {...}), not valid JSON. Always add "stream": false for single-response testing.
13. **v3.8.45 spontaneous probe crash loop ("out of memory")** — An existing healthy v3.8.45 instance can spontaneously enter a crash loop where the DB probe fails with `out of memory`. This is DISTINCT from pitfall #10 (SQLite-write probe rejection on restart). Symptoms:
    - logs repeat `[DB] Could not probe existing DB: out of memory` every 10s (not real OOM — SQLite WAL/journal inconsistency)
    - DB gets renamed `storage.sqlite.probe-failed-<ts>` and auto-restored in an endless loop
    - Dashboard returns 500, API returns 500, CLI also fails
    - `STORAGE_ENCRYPTION_KEY` in `.env` does NOT prevent this
    - **Fix:** `pkill -f omniroute`, `rm -f ~/.omniroute/storage.sqlite*`, restart fresh. All manually configured providers are lost.
14. **CLI nodes add needs healthy DB** — `omniroute nodes add/list/test/remove` all fail when the DB is in probe-failure loop (pitfall #13). Fix the DB before using CLI commands.
15. **`omniroute runtime repair` may claim success but do nothing** — The command outputs "✓ better-sqlite3 repaired OK" even when `dist/node_modules/better-sqlite3/` lacks `binding.gyp`. Verify by checking `build/Release/better_sqlite3.node` existence after repair. Use manual rebuild (paths A/B/C in `references/omniroute-node22-deploy.md`) instead.
16. **Path to `node` matters, not the omniroute binary** — The `#!/usr/bin/env node` shebang resolves to the first `node` in PATH. If system `node` is v23 but `.n/bin/node` is v22, you must override PATH in the background process command. Setting PATH in a prior foreground terminal step does NOT carry into `terminal(background=true)` calls — export PATH in the same command string.
17. **Fresh install from scratch fixes more than runtime repair** — Complete `npm uninstall -g omniroute` + `rm -rf /usr/local/lib/node_modules/omniroute` + `npm install -g omniroute` resolves stale prebuilt ABI mismatches that `omniroute runtime repair` and `npm rebuild` cannot fix. Do this when runtime repair repeatedly claims success without creating the .node file.
18. **Dashboard password recovery via bcryptjs** — Use the `bcryptjs` module bundled with OmniRoute (NOT the `bcrypt` C++ native module) to generate a compatible hash. `bcryptjs` lives at `node_modules/bcryptjs` under the omniroute install dir. The db stores password as `key='password', value='"$2b$12$..."'` (JSON-string-wrapped bcrypt hash).
19. **Proxy config via settings API does NOT populate proxy_registry table** — The legacy `PUT /api/settings/proxy` stores settings in-memory. The new proxy registry at `api/v1/management/proxies` uses the `proxy_registry` + `proxy_assignments` SQLite tables. Both code paths ultimately reach `ProxyFetch` but may behave differently. If one fails, try the other.
20. **Beware `request_signal_aborted` from undici proxy agent** — This error means undici's HTTP CONNECT tunnel failed. It's NOT a timeout (happens at ~16-30s, not at the configured timeout). The same proxy works fine with `curl -x`. Try: switch proxy type (HTTP vs SOCKS5), set env vars, or route through a different proxy port.
21. **OAuth-based providers ignore stored API keys** — The `opencode` built-in provider executor uses OAuth tokens only. API keys stored in `provider_connections` with `provider='opencode'` are never used. The log says `Using opencode account: noauth...`. Workaround: create a separate OpenAI-compatible provider with the correct upstream base URL.
22. **Model count in `/v1/models` includes imported + built-in** — The `provider:connectionId` entries in `key_value` table add to the model list. A connection that's broken (key expired) still contributes models to the list until the connection is removed. Don't assume a listed model works.
23. **`test_status: unknown` is not a failure** — OpenCode Zen connections show `unknown` because the CLI test framework doesn't have a handler for the OpenCode provider type. The actual key may still work when routed through the correct API endpoint.
24. **Proxy can BLOCK reachable providers** — On networks where `integrate.api.nvidia.com` is directly reachable (0.35s for `/v1/models`), applying a global proxy may cause all NVIDIA requests to fail with `request_signal_aborted`. Always test providers WITHOUT proxy first. Set `"global": null` via `PUT /api/settings/proxy` and restart if proxy causes failures.
25. **Built-in NVIDIA provider model names differ from upstream** — OmniRoute maps `nvidia/deepseek-ai/deepseek-v4-flash` (OmniRoute model ID) to upstream model `deepseek-ai/deepseek-v4-flash` (NVIDIA model ID). The `nvidia/` prefix is stripped before forwarding. The model IDs in OmniRoute's `/v1/models` are **not** always the same as the upstream's model IDs — OmniRoute prepends its provider prefix.
