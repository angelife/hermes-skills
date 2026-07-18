# OmniRoute Provider Configuration via SQLite

When OmniRoute's Dashboard requires password setup (first run) and you know the
provider details and API keys, bypass the Dashboard by writing directly to the
SQLite database.

## Schema

```sql
-- Provider node defines a service type (base URL, API format)
CREATE TABLE provider_nodes (
    id TEXT PRIMARY KEY,           -- e.g. 'opencode-zen', 'nvidia', 'agnes'
    type TEXT NOT NULL,            -- 'openai' for OpenAI-compatible API
    name TEXT NOT NULL,            -- Display name
    api_type TEXT,                 -- 'openai' / works for most
    base_url TEXT,                 -- API endpoint
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

-- Provider connection holds the actual API key
CREATE TABLE provider_connections (
    id TEXT PRIMARY KEY,           -- UUID
    provider TEXT NOT NULL,        -- References provider_nodes.id
    auth_type TEXT,                -- 'bearer' for API keys
    name TEXT,                     -- Display label (e.g. 'OpenCode Zen #1')
    priority INTEGER,              -- Lower = preferred
    is_active INTEGER DEFAULT 1,   -- 1 = active
    api_key TEXT,                  -- The actual API key
    default_model TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
```

## Insert Pattern

```bash
# Create a provider node
sqlite3 ~/.omniroute/storage.sqlite "
INSERT OR IGNORE INTO provider_nodes
(id, type, name, api_type, base_url, created_at, updated_at)
VALUES ('my-provider', 'openai', 'My Provider', 'openai',
        'https://api.example.com/v1', datetime('now'), datetime('now'));
"

# Add a connection with API key
sqlite3 ~/.omniroute/storage.sqlite "
INSERT INTO provider_connections
(id, provider, auth_type, name, priority, is_active, api_key, default_model, created_at, updated_at)
VALUES (hex(randomblob(16)), 'my-provider', 'bearer', 'My Provider #1', 1, 1,
        'sk-...', '', datetime('now'), datetime('now'));
"
```

## Verify

```bash
# List all connections
sqlite3 ~/.omniroute/storage.sqlite "
SELECT pn.id AS provider, pc.name, pc.priority, substr(pc.api_key, 1, 12) || '...'
FROM provider_connections pc
JOIN provider_nodes pn ON pc.provider = pn.id
ORDER BY pn.id, pc.priority;
"

# Check models are recognized
curl -s http://localhost:20128/v1/models | python3 -c "
import json, sys
data = json.load(sys.stdin)
for m in data['data']:
    print(m['id'])
print(f'---\\nTotal: {len(data[\"data\"])}')
"
```

## Known Providers (this installation)

| Provider | Base URL | Key prefix |
|----------|----------|------------|
| opencode-zen | https://opencode.ai/zen/v1 | `sk-` |
| nvidia | https://integrate.api.nvidia.com/v1 | `nvapi-` |
| agnes | https://apihub.agnes-ai.com/v1 | `sk-` |

## Notes

- OmniRoute must be restarted after adding providers for the Dashboard to reflect them
- The `/v1/models` endpoint works without auth (it's an OpenAI-compatible endpoint)
- The Dashboard API (`/api/providers`) requires auth unless first-time setup is done
