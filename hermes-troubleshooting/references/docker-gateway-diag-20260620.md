# Docker Gateway Diagnostics — Session Transcript (2026-06-20)

## Context

Investigating 金同学's (Gold) gateway health after a Hermes upgrade from v0.16.0 to v0.17.0. Container `hermes-minimaxlab` runs both the "default" and "gold" profiles.

## Commands Used (in order)

### 1. List containers
```bash
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
```
Shows: container name, uptime, port mappings.

### 2. Check running processes
```bash
docker exec <container> ps aux | grep -i hermes
```
Expected: `hermes gateway run --replace` process. Shows actual gateway liveness.

### 3. Gateway and profile status
```bash
docker exec <container> hermes gateway list
docker exec <container> hermes profile list
```
Both showed "not running" / "stopped" even though the gateway process was alive. This is because `run --replace` bypasses the state file system.

### 4. Config stack
```bash
docker exec <container> cat /opt/data/config.yaml          # model, providers, platform config
docker exec <container> grep -A30 "^gateway:" ...          # gateway section
docker exec <container> grep -A10 "^telegram:" ...         # Telegram platform config
docker exec <container> grep -n "bot_token\|name:" ...     # named gateways
```

### 5. Environment
```bash
docker exec <container> cat /opt/data/.env
```
Exposes: TELEGRAM_BOT_TOKEN, API keys, HINDSIGHT_API_URL, and other secrets.

### 6. Gateway logs (s6-log)
```bash
# Current session
docker exec <container> cat /opt/data/logs/gateways/default/current
docker exec <container> cat /opt/data/logs/gateways/gold/current

# Rotated archives (contains full history)
docker exec <container> cat /opt/data/logs/gateways/default/@400*.u
```

### 7. Profile diagnostics
```bash
docker exec <container> ls -la /opt/data/profiles/gold/
docker exec <container> cat /opt/data/profiles/gold/gateway_state.json
docker exec <container> cat /opt/data/profiles/gold/SOUL.md
```

### 8. Process-level verification
```bash
docker exec <container> cat /proc/<pid>/cmdline | tr '\0' ' '
docker exec <container> ls -la /proc/<pid>/fd/
docker exec <container> cat /proc/<pid>/status | head -5
```

### 9. Health check
```bash
docker exec <container> hermes doctor 2>&1 | head -30
```

## Key Finding

`hermes gateway list` and `hermes profile list` are unreliable for `run --replace` mode. The definitive liveness check is `docker exec <container> ps aux | grep 'hermes gateway'`. The `gateway_state.json` PID and `updated_at` timestamp indicate whether the state is stale.
