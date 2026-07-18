# macOS Infrastructure Audit Commands

## Process Discovery
```bash
# Find all bot/agent processes
ps aux | grep -iE '(python|node|bot|hermes|hindsight|new-api|one-api|uvicorn|gunicorn)' | grep -v grep

# Memory per process (RSS in MB)
ps aux | grep -E 'python|node' | grep -v grep | awk '{printf "PID=%-6s RSS=%-8s MB=%-6.1f CMD=%s\n", $2, $6, $6/1024, $11" "$12" "$13}'

# All listening ports
lsof -iTCP -sTCP:LISTEN -P

# System launchd services (non-Apple)
launchctl list | grep -iv apple

# Cron jobs
crontab -l

# Shell env (key-related)
cat ~/.zshrc | grep -iE 'key|token|api|secret|proxy'
```

## Docker
```bash
# Running containers with ports
docker ps --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}'

# Resource usage per container (live)
docker stats --no-stream --format 'table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}'

# Inspect mounts and env
docker inspect <name> --format '{{range .Mounts}}{{.Type}} {{.Source}} -> {{.Destination}}{{"\n"}}{{end}}'
docker inspect <name> --format '{{json .Config.Env}}'

# Container logs (tail)
docker logs <name> 2>&1 | tail -30

# Container shell (if accessible)
docker exec <name> bash -c '<command>'
```

## Hardware & Memory
```bash
# Full hardware profile
system_profiler SPHardwareDataType

# Model identifier -> year (decode at everymac.com)
sysctl -n machdep.cpu.brand_string

# Memory
memory_pressure
sysctl vm.swapusage
top -l 1 -s 0 | grep "PhysMem"

# Free pages to MB
vm_stat | awk '/Pages free/ {printf "Free: %.0f MB\n", $NF * 4096 / 1048576}'
```

## Network
```bash
# IP, subnet, gateway
networksetup -getinfo Wi-Fi  # or Ethernet

# DNS
scutil --dns | grep 'nameserver\['

# Proxy-aware services
lsof -iTCP -sTCP:LISTEN -P | grep -iE 'xray|v2ray|socks|1080|10808|7890'
```

## Key Discovery
```bash
# Find all .env files (exclude noise)
find /Users -maxdepth 4 -name '.env' -not -path '*/node_modules/*' -not -path '*/.npm/*' 2>/dev/null

# Find all config.yaml with api_key fields
grep -rl 'api_key' /Users/*/.hermes/config.yaml /Users/*/.hermes-docker/*/config.yaml 2>/dev/null

# Scan for known key prefixes
grep -rE 'api_key.*sk-|api_key.*nvapi|api_key.*om-|api_key.*fe_' /Users/*/.hermes/config.yaml /Users/*/.hermes-docker/*/config.yaml 2>/dev/null
```

## Common Bottleneck Patterns on MacBot Infrastructure

1. **Memory Wall**: MacBook Pro 2015 (16GB) + Hindsight (3GB) + 3x Hermes bots (~1.7GB) + macOS (~2GB) = near OOM. Swap of 4GB+/5GB signals critical pressure.

2. **Sleep Kill**: macOS sleep stops ALL processes (local + Docker). No amount of container restart policies helps when the host itself sleeps.

3. **Single Points of Failure**: Docker bind-mount configs and .env files create tight-coupling. If hindsight container dies, all bot memory layers fail simultaneously.

4. **Telegram Connection Issues**: api.telegram.org may require fallback IPs. Check container logs for `[SSL: SSLV3_ALERT_HANDSHAKE_FAILURE]` which indicates the primary endpoint is unreachable.
