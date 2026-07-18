# Cloud Full Export Recovery

Session record: 2026-06-20 — rescued 1,294 cloud memories after cloud API began returning 401.

## Problem

Cloud hindsight API (`https://api.hindsight.vectorize.io`) was unreachable:

```
curl -H "X-API-Key: hsk_..." https://api.hindsight.vectorize.io/v1/default/banks/hermes/stats
→ {"detail":"Authentication failed: API key required"}
```

The cron export script (`hindsight_export.py`) using `hindsight_client.list_memories()` only captured 82 items, while the cloud dashboard showed 439+ memories (actual total: 1,294 nodes: 285 observation + 573 world + 436 experience).

## Root Cause

- **Auth header mismatch**: Cloud API requires `Authorization: Bearer <key>` but our SDK/scripts were sending `X-API-Key: <key>`. The `X-API-Key` header works against **local** hindsight servers but not the cloud.
- **SDK export incomplete**: `hindsight_client.list_memories()` returned far fewer items than the REST API's `/memories/list` endpoint. The SDK may filter/consolidate results differently than the raw memory list.

## Full Export Procedure

### 1. Try both auth methods

```bash
KEY=$(grep HINDSIGHT_API_KEY ~/.hermes/.env | cut -d= -f2)

# Method A: X-API-Key (works for local server)
curl -H "X-API-Key: $KEY" http://localhost:8888/v1/default/banks/hermes/stats

# Method B: Bearer token (works for cloud when method A fails)
curl -H "Authorization: Bearer $KEY" https://api.hindsight.vectorize.io/v1/default/banks/hermes/stats
```

### 2. Check stats to know total size

```python
import requests
key = "hsk_..."
headers = {"Authorization": f"Bearer {key}"}
r = requests.get("https://api.hindsight.vectorize.io/v1/default/banks/hermes/stats", headers=headers)
stats = r.json()
# stats["nodes_by_fact_type"] shows:
#   observation, world, experience
# stats["total_nodes"] is the grand total
```

### 3. Full export via paginated REST API

```python
import requests, json
key = "hsk_..."
headers = {"Authorization": f"Bearer {key}"}
base = "https://api.hindsight.vectorize.io/v1/default/banks/hermes"
types = ["observation", "world", "experience"]
all_items = {}
for t in types:
    items = []
    offset = 0
    PAGE = 500  # max per-page
    while True:
        r = requests.get(f"{base}/memories/list?type={t}&limit={PAGE}&offset={offset}", headers=headers, timeout=30)
        if r.status_code != 200:
            break
        batch = r.json().get("items", [])
        if not batch:
            break
        items.extend(batch)
        if len(batch) < PAGE:
            break
        offset += PAGE
    all_items[t] = items
out = {
    "bank": "hermes",
    "exported_at": datetime.now().isoformat(),
    "source": "cloud",
    "stats": {k: len(v) for k, v in all_items.items()},
    "memories": all_items,
}
with open("cloud-full-export.json", "w") as f:
    json.dump(out, f, indent=2, ensure_ascii=False, default=str)
```

### 4. Import into local server

The local hindsight server's REST API is at `http://localhost:8888/v1/default/banks/hermes`.

```python
import requests, json
key = "hsk_..."
headers = {"X-API-Key": key, "Content-Type": "application/json"}
local_base = "http://localhost:8888/v1/default/banks/hermes"

with open("cloud-full-export.json") as f:
    data = json.load(f)

memories = []
for mtype, mems in data["memories"].items():
    for m in mems:
        memories.append({
            "content": m.get("text", m.get("content", "")),
            "context": m.get("context", ""),
            "tags": m.get("tags", []),
            "type": m.get("type", mtype)
        })

# POST endpoint accepts {"items": [item]} (single memory per batch)
# /import is for BANK TEMPLATES (config, mental-models, directives), NOT memories
ok = err = 0
for i, item in enumerate(memories):
    r = requests.post(f"{local_base}/memories", json={"items": [item]}, headers=headers, timeout=120)
    if r.status_code in (200, 201):
        ok += 1
    else:
        err += 1
    if (i+1) % 50 == 0:
        print(f"  {i+1}/{len(memories)} ({ok}成功, {err}失败)")
```

### 5. Monitor import progress via stats

```bash
curl -s -H "X-API-Key: $KEY" http://localhost:8888/v1/default/banks/hermes/stats \
  | python3 -c "import json,sys;d=json.load(sys.stdin);n=d['nodes_by_fact_type'];print(f'observerations={n[\"observation\"]} world={n[\"world\"]} experience={n[\"experience\"]} total={d[\"total_nodes\"]}')"
```

## Performance characteristics

| Metric | Value |
|--------|-------|
| Per-memory POST time | ~5–10s (LLM embedding + entity extraction per item) |
| Throughput | ~12 memories/minute |
| 1,294 memories total | ~1.5–2 hours |
| Import must be backgrounded | Use `background=true notify_on_complete=true` in terminal tool |

## Available API endpoints on local hindsight server

```
GET  /v1/default/banks/{bank_id}/stats              — bank statistics
GET  /v1/default/banks/{bank_id}/memories/list      — paginated memory list
POST /v1/default/banks/{bank_id}/memories           — create memory(s), accepts {"items": [...]}
GET  /v1/default/banks/{bank_id}/export             — bank template export (NOT memories)
POST /v1/default/banks/{bank_id}/import             — bank template import (NOT memories)
GET  /health                                         — server health
```

NOTES:
- `/import` is for **bank templates** (config, mental models, directives), NOT memory data.
- Memory data goes through `/memories` with `{"items": [item]}`.
- `X-API-Key` header works on local. Cloud requires `Authorization: Bearer`.

## Bank structure

Nodes are organized in three fact types:
- **observation** (285 for this bank) — raw observed facts, deduplicated
- **world** (573) — consolidated world knowledge
- **experience** (436) — action patterns and lessons learned

Total: 1,294 nodes, 36 documents, 485 completed operations at export time.
