# Stale `gateway_state.json` — Process Dead But State Says "Running"

## The Trap

Hermes writes `gateway_state.json` (in `~/.hermes/`) when the gateway starts, setting `gateway_state: "running"`. When the gateway is `kill`ed or crashes unexpectedly, **this file is NOT cleaned up**. The result: `gateway_state.json` shows `"running"` but no process exists.

## Diagnostic Flow

```bash
# Step 1: Check process existence
ps aux | grep hermes | grep -v grep

# Step 2: Check state file
cat ~/.hermes/gateway_state.json | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('gateway_state'), d.get('pid'))"

# Step 3: Cross-reference
# If state says "running" but no PID in process table → stale state
```

## Common Roots of Unexpected Gateway Death

| Root Cause | Log Signature | Fix |
|---|---|---|
| Provider plugin missing | No clear error; falls into MOA loop with `No LLM provider configured` | Fix `model.provider` to an installed plugin or `custom` |
| MoA misconfig | `No LLM provider configured for task=moa_aggregator provider=openrouter` (repeat 3×) | Disable or fix MoA presets |
| All API keys exhausted | `402 Insufficient Balance` + `401 No payment method` on all providers | Replace keys or add fallback providers |
| Unhandled Telegram callback | `BadRequest: Query is too old and response timeout expired or query id is invalid` + Traceback | Restart; root fix is in adapter error handling |
| Proxy latency cycling | `Pool timeout: All connections in the connection pool are occupied` repeated | Fix proxy latency, not gateway config |

## Verification

After restart, confirm new PID matches `gateway_state.json`:

```bash
GATEWAY_PID=$(cat ~/.hermes/gateway_state.json | python3 -c "import sys,json; print(json.load(sys.stdin).get('pid',''))")
ps -p "$GATEWAY_PID" >/dev/null 2>&1 && echo "PID ${GATEWAY_PID} alive" || echo "PID ${GATEWAY_PID} STALE"
```

## See Also

- `hermes-troubleshooting` SKILL.md — Gateway crash from cascading provider failure
- `references/gateway-pool-timeout-diagnostics.md` — pool timeout vs stale state
