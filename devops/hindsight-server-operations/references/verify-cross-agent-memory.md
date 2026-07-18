# Cross-Agent Memory Verification Session

## Scenario

火同学 (remote Hermes on 192.168.1.x) configured hindsight memory provider:
```yaml
memory:
  provider: hindsight
  url: http://192.168.1.2:8888
  bank_id: hermes
```

But could not confirm whether `memory` tool writes reached the shared hindsight.

## Investigation

### 1. Confirm hindsight is running and healthy
```bash
curl -s http://localhost:8888/health
# → {"status":"healthy","database":"connected"}
```

### 2. Check bank stats
```bash
curl -s http://localhost:8888/v1/default/banks/hermes/stats
# → {"bank_id":"hermes","total_nodes":1096,"total_links":33695,"total_documents":46,
#    "nodes_by_fact_type":{"experience":634,"observation":456,"world":6},
#    "last_consolidated_at":"2026-06-22T05:33:03.688193+00:00",
#    "pending_operations":0,"failed_operations":1}
```

### 3. Search for expected content via hindsight_recall
Used the built-in `hindsight_recall` tool with queries specific to:
- "火同学" — only returned discussion ABOUT 火, not content FROM 火
- "192.168.1.2:8888" — returned discussion about the port forwarding solution
- "hindsight config 记忆写入" — returned old memories only

No new memories from the remote agent appeared.

### 4. Determine how hindsight is deployed
```bash
lsof -i :8888
# → com.docke 1553 macos ... TCP *:ddi-tcp-1 (LISTEN)
```
Hindsight runs in Docker Desktop (port forwarded), not as a native process.

## Root Cause

The `memory(action='add')` tool writes to Hermes's **built-in memory**, not the hindsight provider. For writes to reach the shared hindsight, the agent must either:
- Use the `hindsight_retain` tool (if the provider exposes it)
- Have the hindsight provider's `sync_turn` active (auto-writes after each turn)

The config file change also requires a **gateway restart** to take effect.

## Key API Endpoints Discovered

| Endpoint | Purpose |
|----------|---------|
| `GET /health` | Health check |
| `GET /v1/default/banks/{bank_id}/stats` | Bank statistics |
| `POST /v1/default/banks/{bank_id}/recall` | Recall memories (via hindsight_client) |
| `POST /v1/default/banks/{bank_id}/retain` | Store memories (via hindsight_client) |
| `GET /version` | API version |

These are consumed through the `hindsight_client` Python package, not raw HTTP.

## Tool Availability

The hindsight provider exposes three Hermes tools:
- `hindsight_recall` — search memories
- `hindsight_retain` — store memories
- `hindsight_reflect` — synthesize answer from memories

These are separate from the `memory` tool which writes to the built-in memory store.
