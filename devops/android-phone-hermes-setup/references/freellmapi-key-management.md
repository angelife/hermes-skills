# FreeLLM-API Key Management

FreeLLMAPI (FreeLLM-API) is the unified API gateway for all Android agents. It is a fork of New API (One-API).

## Getting the unified_api_key

The unified_api_key is the master key that clients use to access all models through FreeLLMAPI.

```bash
# 1. Copy database from Docker container
docker cp freellmapi-freellmapi-1:/app/server/data/freeapi.db /tmp/freeapi.db

# 2. Query the key
sqlite3 /tmp/freeapi.db "SELECT value FROM settings WHERE key='unified_api_key';"

# 3. Other useful queries
sqlite3 /tmp/freeapi.db ".tables"
sqlite3 /tmp/freeapi.db "SELECT key, value FROM settings;"
sqlite3 /tmp/freeapi.db "SELECT * FROM api_keys;"
sqlite3 /tmp/freeapi.db "SELECT * FROM sessions;"
```

## Upstream API Keys

FreeLLMAPI stores upstream platform keys (NVIDIA, OpenCode Zen, Cloudflare, etc.) in the `api_keys` table:

```sql
SELECT * FROM api_keys;
```

To update an upstream key, modify the `value` column in `api_keys` and reload:
```bash
docker restart freellmapi-freellmapi-1
# OR through the FreeLLMAPI web UI: click "Reload"
```

## Client Provider Configuration

Each Android agent's `config.yaml` must have:

```yaml
model:
  default: deepseek-ai/deepseek-v4-flash
  provider: freellmapi

providers:
  freellmapi:
    api_key: <unified_api_key from settings table>
    base_url: http://192.168.1.8:3001
    timeout: 120
    max_tokens: 16384
```

The `base_url` is the Mac's LAN IP (not localhost). Verify with:
```bash
ipconfig getifaddr en0
```

## Common Errors

- **401 Invalid token**: The unified_api_key in the client config doesn't match the one in the DB. Re-sync from the DB.
- **403 Forbidden / rate limited**: The upstream platform (e.g., NVIDIA) has rate-limited or blocked the API key stored in `api_keys` table.
- **HTTP 429 All models rate-limited**: FreeLLMAPI's upstream providers are all hitting rate limits. Wait and retry.
