# API Provider Billing & Silent-Agent Diagnosis

## Session: 2026-06-21 — DeepSeek 402 Balance Exhaustion

### Problem
A Docker containerized Hermes agent (hermes-gold) is running (`Up N hours`, processes alive via `docker top`) but not responding to user messages. No output at all — as if the agent is dead.

### Key Distinction

| Status | Meaning | HTTP Code |
|--------|---------|-----------|
| 200 | API key works (models list) | ✅ |
| 401 | API key invalid/revoked | Auth failure |
| 402 | API key valid but account insufficient balance | **Billing failure** |
| 400/500 | Server/network issue | Different class |

**Critical insight:** A working models list endpoint (HTTP 200) does NOT mean inference calls will work. The key distinction is **authentication** (key is valid → models list works) vs **authorization/billing** (account has funds → inference works).

### Diagnostic Checklist

```
Symptom: container up, agent silent
  │
  ├─ 1. Container health
  │    docker ps | grep <container>
  │    → Status: Up N hours (container running)
  │
  ├─ 2. Process tree
  │    docker top <container>
  │    → s6-supervise, gateway-<profile>, python3 all present
  │
  ├─ 3. Container logs
  │    docker logs --tail 100 <container>
  │    → Look for HTTP errors, retries, timeouts
  │    → e.g. "Insufficient Balance", "402", "429", "401"
  │
  ├─ 4. Read container config
  │    docker exec <container> cat /config/config.yaml
  │    → Check model.default, model.provider
  │    → Check providers: section (does target provider exist?)
  │
  ├─ 5. Extract API key
  │    docker exec <container> env | grep <PROVIDER>_API_KEY
  │    → Confirm key is set and non-empty
  │
  ├─ 6. Test API key directly (credentials check)
  │    curl -s https://api.provider.com/v1/models \
  │      -H "Authorization: Bearer $KEY"
  │    → HTTP 200 = key is valid (but NOT sufficient for billing check)
  │
  ├─ 7. Check account balance (if endpoint exists)
  │    curl -s https://api.provider.com/user/balance \
  │      -H "Authorization: Bearer $KEY"
  │    → DeepSeek returns {is_available, balance_infos}
  │    → Negative balance = 402 on every inference call
  │
  └─ 8. Verify provider routing alignment
       Config says: model.provider = X
       But logs show calls to: Y API endpoint
       → Root cause: provider X config missing or incomplete,
         causing fallback/routing to wrong provider
```

### Provider-Specific Balance Endpoints

#### DeepSeek
```
GET https://api.deepseek.com/user/balance
Response:
  is_available: bool
  balance_infos: [
    {currency: "CNY", total_balance: "-0.12",
     granted_balance: "0.00", topped_up_balance: "-0.12"}
  ]
```

Note: Negative balance is possible (credit overuse). `total_balance` is the final figure.
Models listing: `GET https://api.deepseek.com/v1/models` (requires key in bearer header)

#### OpenAI / Azure
No billing balance API available through the API key. Must check via web dashboard.

#### Other providers
Document as discovered in future sessions. The pattern is:
1. Check API docs for `/billing` or `/balance` endpoint
2. If none exists, check web dashboard
3. Key that works for `models` but fails for `chat` = likely billing issue

### Failure Modes

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| Logs show 402 on all calls | Billing exhausted | Recharge or switch provider |
| Logs show 401 | API key wrong/expired | Update key in config + env |
| Logs show connection refused/ETIMEDOUT | Network/DNS in container | Check bridge network, container DNS |
| Logs call API X but config says provider Y | Provider routing misalignment | Add missing provider config or correct model.provider |
| Container shows old key despite env update | Container env not rebuilt | Rebuild container (not just `docker restart`) |

### Provider Routing Misalignment

Hermes resolves which API to call through a chain:
1. `model.provider` → names a key in `providers:` section
2. If that provider key doesn't exist in config → Hermes may fall back to a built-in default
3. The built-in default may hit a different billing system

**Example from session:**
```
Config says:
  model.default: deepseek-v4-flash-free
  model.provider: opencode-zen

But gold container's config is MISSING the `opencode-zen` provider definition.
→ Hermes falls back to deepseek-v4-pro via built-in deepseek provider
→ Which goes to api.deepseek.com/v1 with DeepSeek API key
→ Which shows models=200 (key valid) but chat=402 (no balance)
```

**Fix:** Either add the provider definition to the container's config, or set `model.provider` to a provider that IS configured in the container.

### When This Applies

- Any containerized Hermes agent that is alive but unresponsive
- Docker compose / s6-supervise managed agents
- Multi-provider setups with shared API keys
- After config changes that didn't rebuild containers
- API credits running out silently (no other error mode)

### Quick Test Script

```bash
# For DeepSeek specifically
KEY=$(docker exec <container> env | grep DEEPSEEK_API_KEY | cut -d= -f2)

echo "=== Models (auth check) ==="
curl -s -w "\nHTTP %{http_code}" \
  https://api.deepseek.com/v1/models \
  -H "Authorization: Bearer $KEY" | tail -3

echo ""
echo "=== Balance (billing check) ==="
curl -s -w "\nHTTP %{http_code}" \
  https://api.deepseek.com/user/balance \
  -H "Authorization: Bearer $KEY" | tail -3

echo ""
echo "=== Provider config ==="
docker exec <container> cat /path/to/config.yaml | grep -A3 'model:'
```
