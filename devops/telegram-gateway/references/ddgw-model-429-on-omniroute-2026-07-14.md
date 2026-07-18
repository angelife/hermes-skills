# ddgw/gpt-5-mini 429 on OmniRoute (2026-07-14)

## Pattern

Bot receives messages (polling OK) but never replies. `gateway.error.log` shows:

```
RateLimitError provider=custom base_url=http://localhost:20128/v1 model=ddgw/gpt-5-mini
summary=HTTP 429: [429]: DuckDuckGo AI Chat error: ERR_RATE_LIMIT
```

Fallback chain also dead:
- opencode-zen `deepseek-v4-flash-free` → Connection error (all 4 keys)
- nvidia `minimaxai/minimax-m2.7` / `deepseek-ai/deepseek-v4-flash` → 429 ResourceExhausted

## Root Cause

The `model.default: ddgw/gpt-5-mini` model on OmniRoute hits DuckDuckGo's per-key rate limit. This is model-specific — other models on the same OmniRoute aggregator work fine. The opencode-zen and nvidia fallbacks are independently dead (opencode connection errors, nvidia 48/48 worker exhaustion).

**This is NOT a gateway problem.** Gateway itself is healthy, connected to Telegram, polling normally. The bottleneck is the upstream model API.

## Diagnostic (3 commands)

```bash
# 1. Check gateway is connected
cat ~/.hermes/gateway_state.json | python3 -c "import sys,json; print(json.load(sys.stdin).get('telegram',{}).get('state','?'))"
# Expected: "connected"

# 2. Check model-level errors  
tail -1 ~/.hermes/logs/gateway.error.log | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('summary','?')[:200])"
# Expected: 429 / RateLimitError on ddgw model

# 3. List working models on OmniRoute
curl -s http://localhost:20128/v1/models | python3 -c "import sys,json; [print(m['id']) for m in json.load(sys.stdin)['data'][:20]]"
```

## Fix

Switch default model to a known-working model on the same OmniRoute aggregator:

```bash
sed -i '' 's/^  default: .*/  default: wuxing-free/' ~/.hermes/config.yaml
launchctl stop ai.hermes.gateway && sleep 3 && launchctl start ai.hermes.gateway
```

Model candidates on OmniRoute (verified working during this session):
- `wuxing-free` — used by CLI session, confirmed working
- `auto/best-free` — OmniRoute auto-routing cheapest models
- `auto/best-chat` — chat-optimized auto-route

## Lesson

OmniRoute aggregates many free model providers. Individual models (especially `ddgw/*`, `oc/*`) have independent rate limits. When one exhausts, switch to a different model on the same aggregator — NOT to a different provider chain.

Compare with `all-providers-exhausted-2026-07-14.md` where ALL aggregators (OmniRoute + opencode-zen + nvidia) were at capacity simultaneously.
