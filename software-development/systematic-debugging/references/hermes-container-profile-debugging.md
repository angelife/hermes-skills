# Hermes Container Profile Override Debugging

## Session: 2026-06-22 — Gold container 404 / 401 / wrong model

### Problem
A Docker containerized Hermes agent (hermes-gold) shows model provider failures despite correct-looking main config. Changes to `/opt/data/config.yaml` and `/opt/data/.env` have no effect.

### Root Cause
**Profile config overrides.** When Hermes starts with `profile: gold`, it loads `/opt/data/profiles/gold/config.yaml` which **completely overrides** the main `config.yaml` for all same-named sections (model, providers, fallback_providers, etc.). Similarly, `profiles/gold/.env` overrides main `.env`.

The config file chain is:

```
Main config.yaml       →  model.default, model.provider, providers:
                              ↓ (COMPLETELY OVERRIDDEN by profile)
Profile config.yaml    →  model.default, model.provider, providers:
                              ↓ (ACTUALLY USED)
Main .env              →  AGNES_API_KEY=xxx
                              ↓ (INDEPENDENTLY OVERRIDDEN by profile .env)
Profile .env           →  AGNES_API_KEY=yyy (ACTUALLY USED)
```

**Key insight:** Modifying the main config after a profile is active has ZERO effect. You must modify the profile copy.

### Detection

```bash
# 1. Check which profile is active
docker logs <container> --tail 5 | grep Profile
# → "Profile: gold" (or whatever)

# 2. Check what config the container actually uses
docker exec <container> cat /opt/data/profiles/<profile>/config.yaml
# vs
docker exec <container> cat /opt/data/config.yaml

# 3. Check what .env the container actually reads
docker exec <container> env | grep AGNES_API_KEY
# Did it get the main .env value or the profile .env value?
```

### Full Diagnostic Sequence

```bash
# Step 1: Container running?
docker ps | grep hermes-gold

# Step 2: Profile detection
docker logs hermes-gold --tail 10 2>&1 | grep -i profile

# Step 3: Read profile config (the one that matters)
docker exec hermes-gold cat /opt/data/profiles/gold/config.yaml

# Step 4: Test model from inside container
docker exec hermes-gold python3 -c "
import os, json, urllib.request
url = 'https://apihub.agnes-ai.com/v1/chat/completions'
body = json.dumps({
    'model': 'agnes-2.0-flash',
    'messages': [{'role':'user','content':'hi'}]
}).encode()
req = urllib.request.Request(url, data=body, headers={
    'Authorization': f'Bearer {os.environ[\"AGNES_API_KEY\"].strip()}',
    'Content-Type': 'application/json'
})
try:
    resp = urllib.request.urlopen(req, timeout=15)
    data = json.loads(resp.read())
    print(f'OK: {data[\"choices\"][0][\"message\"][\"content\"][:50]}')
except urllib.error.HTTPError as e:
    print(f'HTTP {e.code}: {e.read().decode()[:200]}')
"
```

### Symptom-to-Cause Map (Container Profile Context)

| Symptom | Likely Root Cause | Fix |
|---------|------------------|-----|
| Logs show Profile: X but you modified main config | Profile overrides main | Edit profile config, not main |
| 404 on custom provider endpoint | Profile config has wrong `base_url` or missing `api_mode: custom` | Fix base_url + api_mode in profile config |
| 401 "invalid token" in container but 200 from host | Profile .env has wrong/old key | Sync key in `profiles/<name>/.env` |
| 200 from model test but agent still errors | Profile may be missing `fallback_providers` or have wrong `model.default` | Check all sections in profile config |
| Container fails but was working before | Check if profile was recently added/changed | `docker logs` for recent changes |
| Agent always uses old model name | Profile overrides `model.default` | Edit `model.default` in profile config, not main |

### Fallback Provider Config in Profile

Profile config must have the **complete** fallback provider definition, since profile overrides main:

```yaml
model:
  default: agnes-2.0-flash
  provider: agnes
  fallback_providers: [xunfei]

providers:
  agnes:
    base_url: https://apihub.agnes-ai.com/v1
    api_mode: custom
    # key from .env: AGNES_API_KEY

  xunfei:
    base_url: https://spark-api-open.xf-yun.com/v1
    api_mode: custom
    # key from .env: XUNFEI_API_KEY
```

### When This Applies

- Any Hermes instance started with `profile: <name>` in config
- Docker Compose / s6-supervise managed multi-instance setups
- When config changes appear to have no effect
- When `docker restart` doesn't fix a config issue
- Multi-profile setups where each agent (金/木/火) has its own model and provider

### Key Distinctions

| Check | What It Tests | Common Failure |
|-------|--------------|----------------|
| `docker exec <c> env \| grep KEY` | Which key the container actually uses | Profile .env has stale key |
| `docker logs \| grep Profile` | Which config layer is active | Profile != expected |
| `docker exec <c> cat .../profiles/X/config.yaml` | Actual effective config | Contents differ from main |
| `docker exec <c> python3 -c "test chat"` | End-to-end model connectivity | Works from host, fails in container |
