# Docker Container Inspection Patterns

## Multi-Container Hermes Setup

When the user runs multiple Hermes agent containers (gold, minimaxlab, etc.), they share a common pattern:

### Bind Mount Mapping

```
Host path                              Container path
/Users/macos/.hermes-docker/{name}/    -> /opt/data/
```

Container configuration always lives at `/opt/data/` which maps to the host bind mount. This means:

| Container | Host .env path | Host config.yaml path | Host SOUL.md path |
|-----------|---------------|----------------------|-------------------|
| gold      | /Users/macos/.hermes-docker/gold/.env | /Users/macos/.hermes-docker/gold/config.yaml | /Users/macos/.hermes-docker/gold/SOUL.md |
| minimaxlab | /Users/macos/.hermes-docker/minimaxlab/.env | /Users/macos/.hermes-docker/minimaxlab/config.yaml | /Users/macos/.hermes-docker/minimaxlab/SOUL.md |

### Inspecting Container Config

```bash
# Check mounts to understand bind paths
docker inspect <name> --format '{{range .Mounts}}{{.Type}} {{.Source}} -> {{.Destination}}{{"\n"}}{{end}}'

# Check environment variables
docker inspect <name> --format '{{json .Config.Env}}'

# Check Docker command/docker-compose equivalent
docker inspect <name> --format '{{json .Config.Cmd}}'
```

### Inspecting Container Internals

```bash
# Default model + provider
docker exec <name> bash -c 'grep -A3 ^model: /opt/data/config.yaml'

# Full config grep for key fields
docker exec <name> bash -c 'grep -E "model:|provider:|api_key:|base_url:|fallback_providers:" /opt/data/config.yaml'

# .env file
docker exec <name> bash -c 'cat /opt/data/.env'

# SOUL.md (persona)
docker exec <name> bash -c 'cat /opt/data/SOUL.md'

# Telegram bot token (masked)
docker exec <name> bash -c 'grep TELEGRAM_BOT_TOKEN /opt/data/.env | cut -c1-20'
```

### Log Inspection

```bash
# Recent logs
docker logs <name> 2>&1 | tail -30

# Look for specific errors
docker logs <name> 2>&1 | grep -ci 'error\|429\|timeout\|traceback\|exception\|failure'

# Look for Telegram connection issues
docker logs <name> 2>&1 | grep -i 'SSL\|handshake\|fallback\|telegram'

# Look for startup sequence
docker logs <name> 2>&1 | grep -E 'config-migrate\|Setup complete\|Started\|ready'
```

### Resource Usage

```bash
# Live stats
docker stats --no-stream --format 'table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}\t{{.NetIO}}'

# Inspect resource limits
docker inspect <name> --format '{{json .HostConfig.Memory}}'  # memory limit in bytes
docker inspect <name> --format '{{json .HostConfig.NanoCpus}}'  # CPU limit
```

### File Transfer (including Unicode filenames)

`docker cp` breaks with Unicode (Chinese) filenames. Workaround:

```bash
# DON'T do this (fails with Chinese chars):
docker cp <name>:/opt/data/reports/五行Bot审计报告.txt /tmp/

# DO this instead:
# 1. Find the host-side bind mount path
docker inspect <name> --format '{{range .Mounts}}{{.Source}}{{end}}'
# 2. Access the file directly on the host
ls /Users/macos/.hermes-docker/<name>/reports/
cp /Users/macos/.hermes-docker/<name>/reports/五行Bot审计报告.txt /tmp/
# 3. Then send via MEDIA: protocol from the host path
```

### Container Unresponsiveness

When `docker exec` returns empty but the container is `Up`:

```bash
# 1. Check if container is truly running
docker ps --filter name=<name> --format "{{.Status}}"

# 2. Try simpler shell (sh instead of bash)
docker exec <name> sh -c 'ls /opt/data/'

# 3. If still empty, access via host bind mount directly
ls /Users/macos/.hermes-docker/<name>/

# 4. Check container logs for resource exhaustion (OOM, CPU throttle)
docker logs <name> 2>&1 | tail -50
```
