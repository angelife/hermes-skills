# Hindsight Timeout Diagnostics — Slow LLM Backend

## Objective

When hindsight recall/retain operations time out or fail with `APIConnectionError`, determine whether the root cause is a slow LLM backend that causes background tasks to pile up and consume all worker slots.

## Quick Check

```bash
# 1. Hindsight logs — look for stuck tasks and API errors
docker logs hindsight --tail 50 2>/dev/null | grep -E "APIConnectionError|attempt|stuck|timeout|age="

# 2. Worker slot usage — is the pool saturated?
docker logs hindsight --tail 20 2>/dev/null | grep WORKER_STATS
# Expected: "slots=4/10" — if shared=3/8 or reserved slots saturated, tasks are piling up

# 3. LLM backend — test response time directly
curl -s -X POST http://host.docker.internal:9090/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"meta/llama-3.3-70b-instruct","messages":[{"role":"user","content":"ping"}],"max_tokens":10}' \
  -w '\nHTTP %{http_code} time=%{time_total}s'
# If time > 10s per call, the backend is the bottleneck
```

## Root Cause Chain

```
Hindsight background processing task
  → calls LLM (through configured provider/endpoint)
    → LLM returns slowly (e.g. 14s per call)
      → background task blocks its worker slot for 14s+
        → next background task also takes 14s+
          → all slots consumed by stuck tasks
            → new foreground recall/retain requests
              → wait for a free slot → time out
```

Typical logs when this is happening:

```
[WORKER_STATS] worker=hindsight-prod slots=4/10
  reserved: [consolidation=1/2(attempt 2/11, age 971s)]
  shared=3/8(avail=5)
APIConnectionError (HTTP None), attempt 2: Request timed out
```

Key indicators:
- `attempt N/M` with high N (retrying the same task)
- `age Xs` measured in hundreds of seconds (task stuck for minutes)
- `APIConnectionError` on the LLM backend (not Telegram — this is model API latency)
- First recall works; subsequent ones time out as the queue fills

## Diagnostics Walkthrough

### Step 1: Check hindsight service health

```bash
# Is the server itself alive?
curl -s http://localhost:8888/ | head -5

# Memory provider health (test recall)
python3 -c "
from hindsight_client import Hindsight
h = Hindsight(base_url='http://localhost:8888', api_key='')
r = h.recall(bank_id='hermes', query='healthcheck', budget='low')
print(f'Recall OK: {len(r.results)} items')
"
```

### Step 2: Inspect stuck background operations

```bash
# Processing operations (the stuck ones)
curl -s 'http://localhost:8888/v1/default/banks/hermes/operations?status=processing' | python3 -m json.tool

# Pending operations (backlog)
curl -s 'http://localhost:8888/v1/default/banks/hermes/operations?status=pending' | python3 -m json.tool
```

Look for operations with long age / high retry count.

### Step 3: Test the LLM endpoint that hindsight uses

Find hindsight's configured LLM endpoint:

```bash
docker inspect hindsight --format '{{json .Config.Env}}' | tr ',' '\n' | grep -i llm
```

Typical env vars:
- `HINDSIGHT_LLM_BASE_URL` — e.g. `http://host.docker.internal:9090/v1` (NVIDIA proxy)
- `HINDSIGHT_LLM_MODEL` — e.g. `meta/llama-3.3-70b-instruct`
- `HINDSIGHT_LLM_ENABLED` — should be `true` for background processing

### Step 4: Measure LLM response time

```bash
# For NVIDIA proxy running on host at port 9090:
curl -s -X POST http://localhost:9090/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"meta/llama-3.3-70b-instruct","messages":[{"role":"user","content":"respond with one word: hello"}],"max_tokens":10}' \
  -w '\n---\nHTTP %{http_code} time=%{time_total}s'

# For opencode-zen:
curl -s -X POST https://opencode.ai/zen/v1/chat/completions \
  -H "Authorization: Bearer $OPENCODE_ZEN_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"deepseek-v4-flash-free","messages":[{"role":"user","content":"ping"}],"max_tokens":10}' \
  -w '\n---\nHTTP %{http_code} time=%{time_total}s'
```

Compare response times. If the difference is >2x (e.g. 14s vs 5s), the proxy is the bottleneck.

### Step 5: Check NVIDIA proxy liveness (if applicable)

```bash
# Is the proxy process alive?
ps aux | grep nvidia_proxy

# Can it reach NVIDIA?
curl -s -X POST http://localhost:9090/v1/models
```

### Step 5: Check for rate throttling at the proxy

Test the same request twice in quick succession:

```bash
# First call (cold)
time curl -s -X POST ... -w '%{time_total}s' -o /dev/null
# Second call (should be faster if warm)
time curl -s -X POST ... -w '%{time_total}s' -o /dev/null
```

### Step 6: Check if `hindsight_retain` is silently failing

When the background task queue is full (all worker slots consumed by stuck tasks), `hindsight_retain()` returns `success=False` with **NO exception or error message**. The operation appears to succeed from the agent's perspective but the data is never stored.

Unlike recall failures (which surface as `APIConnectionError`), retain failures are **silent** — the only way to detect them is:

1. Check hindsight logs for stuck tasks: `docker logs hindsight --tail 50 | grep -E "attempt|age="`
2. Check worker stats: `docker logs hindsight --tail 20 | grep WORKER_STATS` (look for slots=4/10 or similar saturation)
3. Manually verify: after `hindsight_retain()`, try `hindsight_recall()` with the same content — if the new fact isn't returned, the retain silently failed

## Fix Options

### Quick fix: Restart hindsight (clear stuck tasks)

```bash
docker restart hindsight
sleep 10
# Verify:
docker ps --filter name=hindsight --format '{{.Status}}'
curl -s http://localhost:8888/ | head -3
```

Memory data is persisted in PostgreSQL. Only in-flight operations are lost.

### Medium fix: Switch to faster LLM endpoint

1. Identify a faster available endpoint (e.g. `deepseek-v4-flash-free` via opencode-zen)
2. Recreate hindsight with updated LLM env vars
3. Verify consolidation speed improves in logs

**Caveat:** Different models produce different-quality memory extraction. Flash models may degrade fact quality.

### Long-term: Accept and live with it

If the backend is unavoidably slow but recall works on first attempt, the pragmatic approach is: periodic hindsight restart (cron weekly) as preventive maintenance.

## Pitfalls

- **APIConnectionError does NOT mean the service is down.** It means the LLM call timed out. First recall OK + subsequent timeout = slow backend, not dead service.
- **NVIDIA proxy may return HTTP 200 with correct JSON** but take 14s+. The proxy is alive; the bottleneck is NVIDIA API response time for that specific model.
- **A single stuck task can block a worker for 15+ minutes.** If consolidation retries 11 times at 14s each, the slot is gone for ~3 minutes. Multiple retries compound.
- **Container logs don't show LLM call response times.** Use direct `curl` to the endpoint for latency measurement.
- **Restarting hindsight drops in-flight consolidation** but retains all stored data (persistent PostgreSQL).
