# OmniRoute DB Probe Crash Recovery ("out of memory")

## Symptoms

- All Dashboard and API endpoints return `500 Internal Server Error`
- `app.log` repeats every ~10s:
  ```
  [DB] Could not probe existing DB: out of memory
  [DB] Renamed corrupt DB to storage.sqlite.probe-failed-<ts>
  [DB] Auto-restored preserved database from previous probe failure: storage.sqlite.probe-failed-<prev-ts>
  ```
- The loop: restore → probe fails → rename → restore from previous → repeat
- After many cycles, the DB files become 0-byte stubs (probe cleared the real data)
- The `storage.sqlite` file may disappear entirely between cycles

## Root Cause (observed 2026-07-07)

Not a true out-of-memory condition. The OmniRoute DB probe opens the SQLite WAL/journal and fails metadata validation after a crash or unclean shutdown. The probe's `out of memory` label is misleading — it's a SQLite journal recovery failure that OmniRoute interprets as OOM.

Known triggers:
- Kill -9 of the omniroute process while DB is mid-write
- Running omniroute processes on the same DB simultaneously (two PIDs fighting)
- SQLite WAL checkpoint interrupted mid-write

## Recovery Procedure

```bash
# 1. Kill all omniroute processes
pkill -f omniroute
sleep 2
pgrep -f omniroute  # verify none left

# 2. Remove ALL DB files (fresh start required)
rm -f ~/.omniroute/storage.sqlite*
rm -f ~/.omniroute/db_backups/*
rm -f ~/.omniroute/logs/application/*.log

# 3. Verify the .env has STORAGE_ENCRYPTION_KEY
cat ~/.omniroute/.env  # should show STORAGE_ENCRYPTION_KEY=<hex>

# 4. Start fresh
omniroute --no-open &

# 5. Wait for migrations (5-10s)
sleep 10

# 6. Verify
curl -s -o /dev/null -w "%{http_code}" http://localhost:20128/v1/models
# Expected: 200 (returns empty model list for fresh DB)

# 7. Now add providers via CLI:
omniroute nodes list  # should show empty list (healthy DB)
```

## Consequence

All manually configured provider nodes and connections are lost. Must re-add after recovery.

## Prevention

- Always `omniroute stop` or `graceful shutdown` instead of `kill -9`
- Never run two omniroute processes simultaneously on the same DB
- Regular DB backups: `cp ~/.omniroute/storage.sqlite ~/.omniroute/db_backups/storage-$(date +%Y%m%d-%H%M%S).sqlite`
