# Memory Audit: Hindsight Server Down (2026-07-17)

## Context

The memory-audit cron job ran on 2026-07-17 and found the Hindsight memory server unreachable.
This is the first occurrence of this failure — previous runs (July 14, 15, 16) all succeeded.

## What was observed

### Hindsight server
```
curl -s http://localhost:8888/health      → "hindsight not reachable"
curl -s http://localhost:9077/health      → "hindsight not reachable"
ps aux | grep hindsight                   → no process (only grep itself)
```

### Database files
Two hindsight.db files exist (Docker volume leftovers):
- `~/.hermes-docker/minimaxlab/hindsight/data/hindsight.db` — 1.5MB, zero tables
- `~/.hermes-docker/minimaxlab/hindsight/hindsight.db` — 1.5MB, zero tables

These are likely PostgreSQL-backed files (not SQLite), so sqlite3 `.tables` returns nothing.
No Docker container named `hindsight` is running.

### What still works
- fact_store.db: 34 entries, accessible via sqlite3
- fabric cards: 20 `.md` files in `~/.hermes/fabric/`
- State file: readable and writable
- Previous audit logs: available (14-16 July)

## Diagnosis

Likely root cause: Docker daemon restarted (or container was pruned) and the hindsight
container had no `--restart always` policy, so it never came back.

## Hermes config

From `~/.hermes/config.yaml`:
```yaml
memory:
  memory_enabled: true
  user_profile_enabled: true
  write_approval: false
  memory_char_limit: 2200
  user_char_limit: 1375
  provider: hindsight
```