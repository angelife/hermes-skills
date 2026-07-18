# Hindsight Export Script Patch — 2026-07-12

## Problem

The cron script `hindsight_export.py` was connecting to **Hindsight Cloud** (`api.hindsight.vectorize.io`) instead of the local server (`localhost:8888`).

### Root Cause

The script read `HINDSIGHT_API_KEY` from `~/.hermes/.env` via a dedicated `_load_api_key()` function, but `HINDSIGHT_API_URL` was only read from **environment variables** (line 43: `os.environ.get("HINDSIGHT_API_URL", "https://api.hindsight.vectorize.io")`).

Since the cron job runs in `no-agent` mode (no Hermes agent env vars), `HINDSIGHT_API_URL` was never set in the environment, and the script fell back to the cloud API.

### Secondary Problem

The export dumped ALL memories every day. The `--since` flag existed but was never used. Result: 9 identical export files (every day, same data).

## Fix Applied

### 1. Unified `_load_env()` function

Replaced the single-purpose `_load_api_key()` with a generic `_load_env(key_name)` that works for any config key, reading from environment variables first, then `.env`:

```python
def _load_env(key_name: str) -> str:
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

### 2. Auto-incremental export

Added `_auto_since(output_dir)` that scans existing export filenames for the latest date, then passes it as `--since` to only export new data.

```python
def _auto_since(output_dir: str) -> str | None:
    if not os.path.isdir(output_dir):
        return None
    files = [f for f in os.listdir(output_dir)
             if f.startswith("hindsight-export-") and f.endswith(".json")]
    if not files:
        return None
    dates = sorted(set(f.split("_")[0].replace("hindsight-export-", "")
                        for f in files), reverse=True)
    return dates[0] if dates else None
```

### 3. Verification

Before fix: connected to cloud, exported **1294** memories.
After fix: connected to **localhost:8888**, exported **6718** memories.

## Cron Job Details

- Job: `hindsight-export` (job_id `11e7d7377e4f`)
- Schedule: daily at 02:00
- Mode: `no-agent` (script stdout delivered directly)
- Script: `~/.hermes/scripts/hindsight_export.py`
- Workdir: `~/.hermes`
