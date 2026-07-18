---
name: hindsight-server-operations
category: devops
description: Manage Hindsight memory server — diagnose resource usage, optimize memory, deploy on ARM hardware.
---

# Hindsight Server Operations

Managing the Hindsight memory server — deployment, resource diagnostics, and optimization.

Hindsight is a central service in multi-agent architectures (shared memory provider). Its Python process (FastAPI + ONNX/transformers) often dominates container memory, making optimization critical when running alongside other agents in resource-constrained environments.

## When to Use

- Hindsight container memory usage spikes or stays high
- Need to free Docker VM space for additional agents
- Deploying hindsight on ARM hardware (N1 box, Raspberry Pi)
- Diagnosing slow recall or OOM kills

## Quick Diagnostic (5 seconds)

```bash
# Memory breakdown
docker stats hindsight --no-stream

# Python process actual RSS (not VmSize which is virtual)
docker exec hindsight cat /proc/$(pgrep -f hindsight-api | head -1)/status | grep VmRSS

# What non-default config is set
docker exec hindsight env | grep HINDSIGHT | sort

# Find PostgreSQL config in use
docker exec hindsight ps aux | grep postgres
```

## Memory Optimization Levers (ordered by impact)

### 1. Embeddings Provider (saves **500MB-1GB**)

Default `local` loads `BAAI/bge-small-en-v1.5` via ONNX runtime — the largest single memory consumer.

**Fix:** Switch to a remote API:
```
HINDSIGHT_API_EMBEDDINGS_PROVIDER=openai
HINDSIGHT_API_EMBEDDINGS_OPENAI_MODEL=text-embedding-ada-002
HINDSIGHT_API_EMBEDDINGS_OPENAI_BASE_URL=https://your-api/v1
```

### 2. Reranker Provider (saves **200-500MB**)

Default `local` loads `cross-encoder/ms-marco-MiniLM-L-6-v2` via transformers.

**Options:**
- `HINDSIGHT_API_LAZY_RERANKER=true` — only loads when needed (not at startup)
- Switch to API-based reranker (Cohere, etc.)

### 3. Control Plane (saves **135MB**)

Node.js `next-server` web UI — not needed if accessing solely via API.

**Fix:** `HINDSIGHT_ENABLE_CP=false`

### 4. PostgreSQL Memory Tuning (saves **~150MB**)

The embedded pg0 uses generous defaults. Set these in the `start-all.sh` invocation or Docker run command:
- `shared_buffers=128MB` (was 256MB)
- `maintenance_work_mem=256MB` (was 512MB)
- `work_mem=32MB` (was 64MB)

### 5. DB Connection Pool (saves **~50-100MB**)

Default `db_pool_min_size=5` keeps 5 idle PostgreSQL connections resident.

**Fix:** `HINDSIGHT_API_DB_POOL_SIZE=2`

## ARM64 Deployment

### Docker (Recommended)

Hindsight publishes native ARM64 Docker images. Works on:
- N1 box (刷Armbian, S905, 2GB RAM — tight but functional)
- Raspberry Pi 4/5 (4GB+ recommended)
- Any ARM64 Linux with Docker

Confirmed: `docker exec hindsight uname -m` returns `aarch64` on supported images.

### Standalone Binary (Off-Docker)

Hindsight also publishes standalone Linux binaries for both amd64 and arm64 on GitHub releases:
```
hindsight-linux-amd64   (2.9MB, dynamically linked against glibc)
hindsight-linux-arm64   (2.9MB, dynamically linked against glibc)
```

Usage:
```bash
chmod +x hindsight-linux-arm64
# Configure via env vars or config file
./hindsight-linux-arm64 --help
```

**GLIBC dependency**: The binary requires `/lib/ld-linux-aarch64.so.1` (glibc). This means it runs on standard Linux (Debian, Ubuntu, Alpine with glibc compat) but NOT on:
- Android / Termux (uses bionic libc, not glibc)
- Pure musl-based distros (unless glibc compat layer installed)

### Python Wheel (Alternative)

The GitHub release includes a pure-Python wheel `hindsight_all-0.8.3-py3-none-any.whl` (12KB) that provides a Python API wrapper. This in turn depends on `hindsight-api-slim` which pulls in heavy dependencies:
- `litellm>=1.83.14` (LLM abstraction layer)
- `langchain-core>=1.2.22`
- `langsmith>=0.6.3`
- `markitdown>=0.1.4` (with docx/pdf/pptx/xlsx extras)
- `obstore>=0.4.0` (Rust package — no prebuilt aarch64 wheel, needs Rust compilation)

**`obstore` is the blocker on ARM/aarch64 Linux and Android Termux**: PyPI provides no prebuilt wheel for `aarch64-unknown-linux-gnu`, and compiling from source requires a Rust toolchain. This makes `pip install hindsight-all` unreliable on ARM devices.

Workarounds:
1. Use the Go binary instead (avoids all Python dependency issues)
2. For Android (Termux): install `proot-distro`, create a Debian chroot, run the Go binary inside it
3. Skip server — only install the `hindsight-client` Python package (light, no heavy deps) to send data to an existing Hindsight server

## Hindsight Data Export

Hindsight supports both the cloud API (`api.hindsight.vectorize.io`) and private/local servers (e.g., `localhost:8888`). The default export script (`hindsight_export.py`) is used by cron jobs to back up memories.

### Auto-incremental export

The default full export creates 1.3MB files daily with the same data. Add auto-incremental:

```python
def _auto_since(output_dir: str) -> str | None:
    """Return latest export date in YYYY-MM-DD format."""
    import os
    if not os.path.isdir(output_dir):
        return None
    files = [f for f in os.listdir(output_dir)
             if f.startswith("hindsight-export-") and f.endswith(".json")]
    if not files:
        return None
    dates = sorted(set(f.split("_")[0].replace("hindsight-export-", "")
                       for f in files), reverse=True)
    raw = dates[0] if dates else None
    if raw and len(raw) == 8:   # YYYYMMDD → YYYY-MM-DD
        raw = f"{raw[:4]}-{raw[4:6]}-{raw[6:]}"
    return raw
```

Then in `main()`:
```python
since = args.since
if not since:
    auto = _auto_since(output_dir)
    if auto:
        since = auto
```

### Common pitfalls

- **`_auto_since()` date format mismatch**: If `_auto_since()` returns `YYYYMMDD` (e.g. `20260712`) but the script compares it against API dates in ISO format (`2026-07-12T18:01:00Z`), the string comparison silently **filters everything out** — `'0'` (ASCII 48) > `'-'` (ASCII 45). Always convert `_auto_since()` output to `YYYY-MM-DD` before using as a date filter.
- **API_URL not read from `.env`**: If the script connects to the cloud when you configured `localhost:8888` in `.env`, it's because only `HINDSIGHT_API_KEY` was read from `.env` but `HINDSIGHT_API_URL` was read from environment variables only. Use a unified `_load_env(key_name)` function for all config values so `.env` works for every parameter.
- **Daily duplicates**: The default export dumps all memories every day. Add `--since` or auto-detect last export date from existing filenames to only export new data.

### Unified `.env` loading pattern

```python
def _load_env(key_name: str) -> str:
    \"\"\"Read from environment variable first (override), then from .env file.\"\"\"
    val = os.environ.get(key_name, "")
    if val:
        return val
    env_path = os.path.expanduser("~/.hermes/.env")
    try:
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line.startswith(f"{key_name}="):
                    val = line.split("=", 1)[1].strip().strip('"').strip("'")
                    if val:
                        return val
    except FileNotFoundError:
        pass
    return ""
```

The lesson: reading some values from `.env` but not others silently breaks that one parameter and the script degrades to the wrong fallback.

### Reference

- `references/hindsight-export-patch-2026-07-12.md` — session transcript: debug steps and final fix for the export script

## Server Unreachable / Empty Database

When another consumer (e.g. the memory-audit cron job, a Hermes agent session) reports that Hindsight is unreachable or memory reads return empty, follow this diagnostic chain.

### Quick triage

```bash
# 1. Is the server process running?
curl -s http://localhost:8888/health 2>/dev/null || echo 'NOT REACHABLE'
curl -s http://localhost:9077/health 2>/dev/null || echo 'NOT REACHABLE'

# 2. Is the Docker container alive?
docker ps --filter name=hindsight --format '{{.Names}} {{.Status}}'

# 3. Does the data directory exist with content?
ls -la ~/.hermes-docker/*/hindsight/data/hindsight.db 2>/dev/null
file ~/.hermes-docker/*/hindsight/data/hindsight.db 2>/dev/null
```

### DB file integrity check

Hindsight stores memory in an embedded PostgreSQL (via pg0) which backs to `hindsight.db`. If the file exists but `sqlite3` reports zero tables, it's either a PostgreSQL-backed file (not SQLite) or the container was killed before migrations completed.

**SQLite check:**
```bash
sqlite3 ~/.hermes-docker/*/hindsight/data/hindsight.db ".tables" 2>&1
# "Error: file is not a database" → PostgreSQL-backed, not directly readable
# No output (no tables) → empty/broken, container likely never completed init
```

**Real-world symptoms (observed 2026-07-17):**
- `memory` Hermes tool returns `"Memory is not available"` despite `memory.memory_enabled=true` and `memory.provider=hindsight`
- `hindsight-recognizable` db files exist (1.5MB) but contain zero tables
- No Docker container is running
- Previous day's memory audit logs (July 14-16) had full content access; this failure appeared overnight

**Likely root causes (in order):**
1. Docker daemon restarted and the hindsight container was not set to `--restart always`
2. The container was removed/purged in a cleanup operation (Docker prune, dev env teardown)
3. The hindsight embedded PG database became corrupted and the container exited

**Resolution:**
```bash
# Recreate container from scratch (preserve data if it exists)
docker run -d --restart always --name hindsight \
  -p 8888:8888 \
  -v ~/.hermes-docker/hindsight/data:/data \
  ghcr.io/vectorize-io/hindsight:latest

# Or if data is lost, re-init by starting fresh:
docker run -d --restart always --name hindsight \
  -p 8888:8888 \
  -e HINDSIGHT_API_BANK_DIR=/data/banks \
  ghcr.io/vectorize-io/hindsight:latest

# Verify back up
sleep 10 && curl -s http://localhost:8888/health
```

### Impact on dependent cron jobs

The `memory-audit` cron job critically depends on Hindsight being reachable. When the server is down:
- Audit produces a degraded report (no memory content analysis, only fact_store + state file)
- Status file gets updated with `no_issues: false` (server-down is an issue)
- No memory modifications can occur (observation phase only anyway)
- The failure does NOT trigger `pause_on_error` unless it persists 7+ consecutive runs

**What the audit still CAN do when Hindsight is down:**
- Clean up old log files (>30 days)
- Read and update the state file
- Check fact_store.db (34 entries as of 2026-07-17) and fabric cards (20 as of 2026-07-17)
- Report the server-down status so the user knows to restore it

### Memory data locations on this system

| Path | Content | Accessible when server is down? |
|------|---------|--------------------------------|
| `~/.hermes-docker/*/hindsight/data/hindsight.db` | Primary memory store (PostgreSQL-backed) | No — PG engine only responds on port 8888 |
| `~/.hermes/fact_store.db` | Structured facts (SQLite) | Yes — direct sqlite3 read |
| `~/.hermes/fabric/*.md` | Experience cards | Yes — direct file read |
| `~/.hermes/cron/output/memory-audit-*.txt` | Audit history | Yes — direct file read |
| `~/.hermes/cron/memory-audit-state.json` | Cursor state | Yes — direct file read |

When the server is down, the fact_store and fabric cards are the only live memory sources available for auditing. The audit report should note which data sources were accessible and which were not.

## Verifying Cross-Agent Shared Memory

When multiple Hermes agents (土/火/金/木) share a single hindsight instance, you need to verify that remote agents' memory writes actually reached the shared database.

### Quick Check

```bash
# 1. Confirm hindsight is reachable from the remote agent
curl -s http://<hindsight-host>:8888/health
# Expected: {"status":"healthy","database":"connected"}

# 2. Check bank stats for recent activity
curl -s http://localhost:8888/v1/default/banks/hermes/stats

# 3. Use hindsight_recall to search for expected content
# (via the tool — searches for specific terms the remote agent would have written)
```

### Key diagnostics

| Check | What to look for |
|-------|-----------------|
| `/health` | `database: connected` |
### Consolidation delay
Recently written memories may not surface in recall immediately.

**Fix for stuck consolidation:**
If `recall` times out or `failed_operations > 0` in stats, trigger manual consolidation:
```bash
curl -X POST http://localhost:8888/v1/default/banks/hermes/consolidate
```
Response includes `operation_id` and `deduplicated` flag.
After triggering, check stats for `pending_operations` and `failed_operations`:
```bash
curl -s http://localhost:8888/v1/default/banks/hermes/stats
```

### Why memories might not appear

1. **Config not applied** — `memory.provider: hindsight` written but gateway not restarted
2. **Network blocked** — remote agent can't reach the hindsight host/port (double NAT, firewall)
3. **Tool mismatch** — `memory(action='add')` uses Hermes built-in memory, NOT the hindsight provider. Only `hindsight_retain` or the provider's auto-sync path writes to hindsight
4. **Consolidation delay** — recently written memories may not surface in recall immediately
5. **Recall query too narrow** — try broader terms and check `total_nodes` growth

### Agent identification in memories

Hindsight stores metadata per memory — if the remote agent's provider config sets `retain_source` or its gateway passes `user_id`/`chat_id`, these are searchable. To verify a specific agent's writes:

```bash
# Use hindsight_recall with terms unique to that agent's content
# (no direct "query by agent" API — rely on content matching)
```

### Reference file

See `references/verify-cross-agent-memory.md` for a complete session transcript of diagnosing a remote agent that couldn't write to shared hindsight.

## Retain Write Repair Pattern

When `hindsight_retain` fails because fact extraction is returning 403/401/5xx from an upstream LLM, do NOT blind-retry. Replace the provider chain:

```bash
# 1) Inspect current upstream config
docker exec hindsight env | grep HINDSIGHT_API_LLM | sort

# 2) Use a known-working direct provider instead of local proxy fallback.
# This session's lesson: NVIDIA direct base_url works; local 9090 nvidia_proxy.py is unreliable for Hindsight because its key env names likely mismatch.
docker rm -f hindsight >/dev/null 2>&1 || true
docker run -d --name hindsight \
  -p 8888:8888 -p 9999:9999 \
  -e HINDSIGHT_API_HOST=0.0.0.0 \
  -e HINDSIGHT_API_PORT=8888 \
  -e HINDSIGHT_API_LOG_LEVEL=info \
  -e HINDSIGHT_API_WORKER_ID=hindsight-prod \
  -e HINDSIGHT_API_WORKERS=1 \
  -e HINDSIGHT_API_CONSOLIDATION_WORKERS=1 \
  -e HINDSIGHT_API_LLM_PROVIDER=openai \
  -e HINDSIGHT_API_LLM_BASE_URL=https://integrate.api.nvidia.com/v1 \
  -e HINDSIGHT_API_LLM_API_KEY="$WORKING_NVIDIA_KEY" \
  -e HINDSIGHT_API_LLM_MODEL=meta/llama-3.1-8b-instruct \
  -e HINDSIGHT_ENABLE_API=true \
  -e HINDSIGHT_ENABLE_CP=true \
  -e HINDSIGHT_CP_DATAPLANE_API_URL=http://localhost:8888 \
  ghcr.io/vectorize-io/hindsight:latest
```

**Pitfall:** `nvidia_proxy.py` health can show `keys_loaded:2` yet still return `403` on `/v1/chat/completions`. Health is not auth verification.

**Pitfall:** After changing providers, retain may fail differently, e.g. `Connection reset by peer` instead of `403 Authorization failed`. That still means the write path is not restored; verify the new container's port readiness first:

```bash
curl -sS -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8888/health || echo 'not_ready'
```

Then re-run `hindsight_retain` once per small test fact.

## Remote Access via Cloudflare Tunnel

When remote Hermes agents (火/金/木, or external devices) need to use this Hindsight instance as their shared memory provider, but can't reach `localhost:8888` directly, use Cloudflare Tunnel to expose it securely without opening firewall ports.

### Prerequisites

```bash
# Install cloudflared (macOS)
brew install cloudflare/cloudflare/cloudflared

# Verify
cloudflared --version
```

### Option A: Ephemeral Tunnel (Quick Test)

Best for one-off testing. No Cloudflare account needed.

```bash
cloudflared tunnel --url http://127.0.0.1:8888
```

Prints a `https://<random>.trycloudflare.com` URL. Stop with Ctrl+C when done.

| | Pros | Cons |
|--|------|------|
| ✅ | Zero config, works immediately | URL changes each run, no custom domain, no auth |

### Option B: Persistent Named Tunnel (Production)

Best for ongoing fleet operations. Requires a Cloudflare account + domain.

```bash
# 1. Authenticate (one-time)
cloudflared tunnel login

# 2. Create a named tunnel
cloudflared tunnel create hindsight

# 3. Write config (~/.cloudflared/hindsight.yml)
cat > ~/.cloudflared/hindsight.yml << 'EOF'
tunnel: <tunnel-uuid-from-step-2>
credentials-file: /Users/macos/.cloudflared/<tunnel-uuid>.json
ingress:
  - hostname: hindsight.yourdomain.com
    service: http://localhost:8888
  - service: http_status:404
EOF

# 4. Route DNS
cloudflared tunnel route dns hindsight hindsight.yourdomain.com

# 5. Run
cloudflared tunnel run hindsight
```

**Security:** Tunnel alone doesn't gate access — pair with Hindsight API key auth or Cloudflare Access (Zero Trust) for production.

### Remote Agent Config

Once tunnelled, point remote Hermes agents at the public URL:

```yaml
# In remote agent's config.yaml
memory:
  provider: hindsight
  hindsight:
    base_url: https://hindsight.yourdomain.com   # or trycloudflare URL
    api_key: <your-hindsight-api-key>
```

### Verification

```bash
curl -s https://hindsight.yourdomain.com/health
# → {"status":"healthy","database":"connected"}
```

## Pitfalls

- **VmRSS ≠ VmSize.** The Python process can show 8GB virtual but only 2.8GB physical. Always read VmRSS.
- **Local models cost more than disk suggests.** `bge-small-en-v1.5` is 34MB on disk but 500MB+ when loaded into ONNX runtime in Python.
- **Embeddings/reranker changes require restart.** These are loaded at import time, not hot-reloadable.
- **Control Plane runs even if never visited.** Always check `HINDSIGHT_ENABLE_CP` — it defaults to `true`.
- **5 idle PG connections are normal.** `db_pool_min_size=5` matches exactly the 5 idle `postgres: hindsight` processes seen in `ps aux`.

## Reference Files

- `references/memory-optimization-session.md` — detailed findings from the memory diagnosis session
