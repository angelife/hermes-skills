# OmniRoute Down → Bot Silent (2026-07-12)

## Symptom

Bot receives messages but never replies. Telegram connection is healthy (`Connected to Telegram` in gateway.log), but no AI responses are generated.

## Root Cause

Hermes `fallback_providers` points directly at upstream APIs (`opencode-zen-primary`, `opencode-zen-backup-3`, `nvidia-primary`, etc.) instead of routing through OmniRoute (`localhost:20128`). When all upstream providers simultaneously fail (429 / timeout / connection-error), there's no intermediate layer to handle auto-fallback — the bot goes completely silent.

OmniRoute v3.8.46 was installed but not running. Port 20128 had no listener.

## Diagnosis

```bash
# Step 1: Check if OmniRoute is running
lsof -i :20128  # empty = NOT running

# Step 2: Check Hermes error log for provider failures
cat ~/.hermes/logs/gateway.error.log | tail -20
# Shows: APITimeoutError, RateLimitError 429, ConnectionError across ALL providers

# Step 3: Verify token and Telegram connection still work
curl -s "https://api.telegram.org/bot${TOKEN}/getMe"
# Returns {"ok":true,...} — Telegram path is fine

# Step 4: Verify proxy works
curl -s --max-time 10 -x socks5://127.0.0.1:10808 https://httpbin.org/ip
# Returns origin IP — network path is fine
```

## Fix Applied

Started OmniRoute with Node 22 via `.n`:

```bash
export PATH=/Users/macos/.n/bin:$PATH
cd ~/.omniroute
node /Users/macos/.n/lib/node_modules/omniroute/bin/omniroute.mjs serve --daemon --no-open
```

Verified: port 20128 listening, 92+ models available in `/v1/models`.

## Prevention

1. **Configure Hermes to route through OmniRoute** — see `research-9router-vs-freellm-api` skill, "Recommended Architecture" section.
2. **Add OmniRoute health check to watchdog** — before checking gateway logs, verify port 20128 is listening.
3. **When diagnosing "bot silent"** — check OmniRoute first (it's the single point of failure for provider-level fallback).

## Key Commands

- Start: `export PATH=~/.n/bin:$PATH && node ~/.n/lib/node_modules/omniroute/bin/omniroute.mjs serve --daemon --no-open`
- Check: `lsof -i :20128`
- Test: `curl -s http://localhost:20128/v1/models | python3 -c "import json,sys; print(len(json.load(sys.stdin)['data']), 'models')"`

## Pitfalls to Avoid

- Do NOT use `/usr/local/lib/node_modules/omniroute/dist/server/index.js` — this path does not exist. The entry point is `bin/omniroute.mjs`.
- Do NOT use `omniroute server start` — the CLI subcommand is `serve`, not `server start`.
- Always use Node 22 from `.n` — system Node 23 may have ABI compatibility issues with `better-sqlite3`.