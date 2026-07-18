# macOS Docker Memory Optimization

Real-world memory management for 16GB Macs running Docker + multiple Hermes containers.

## Key metrics

```
total:  16 GB
free:   ~100 MB (truly free pages)
inactive: ~5.8 GB (reclaimable on demand)
speculative: ~18 MB
available: ~6 GB (free + inactive + speculative)

swap: 5.4 GB / 6 GB (high - performance likely degraded)
```

- `free` alone is misleading — `available` = free + inactive + speculative
- `inactive` pages are file cache / buffers that get reclaimed when OOM
- High swap usage indicates physical memory was exhausted at some point

## Reading vm_stat

```
vm_stat | awk '
/Pages free/ {free=$3}
/Pages inactive/ {inactive=$3}
/Pages speculative/ {spec=$3}
END {printf "available: %.0f MB\n", (free+inactive+spec)*4096/1024/1024}'
```

Page size on macOS ARM64: 4096 bytes per page.

## Top memory consumers to check

```
ps aux | sort -nrk 4 | head -8
```

Watch for:
- **com.apple.Virtualization.VirtualMachine** — Docker Desktop VM at 30–40% (4–6+ GB)
- **Python processes** — Hermes gateways, typically 100–200 MB each
- **Tabbit / Electron apps** — can add up to 10%+

## Optimization steps (in order)

### 1. Docker system prune (disk + cache)
```
docker system prune -af
```
Frees build cache and dangling images — often 10-20+ GB of disk. Does NOT directly free RAM but lets the VM shrink its page cache.

### 2. Reduce running container memory limits
```
docker update --memory 1638m --memory-swap 1638m <container_name>
```
- hindsight: typically uses 1.4-1.7 GB — try 1.6 GB (1638m) as a safe lower bound
- new-api: uses ~35 MB — set to 384 MB (from 512 MB saves ~128 MB)
- **Do NOT set below the container's actual working set** or it will be OOM-killed
- Check usage first: `docker stats --no-stream --format "table {{.Name}}\t{{.MemUsage}}\t{{.MemPerc}}"`
- After reducing: verify container is still running (`docker ps`)

### 3. Check actual working set after limit change
```
docker stats --no-stream --format "table {{.Name}}\t{{.MemUsage}}\t{{.MemPerc}}"
```
The kernel will reclaim file cache buffers when the limit is tightened, so actual usage often drops after a limit reduction.

### 4. Stopping unused containers
```
docker stop <name>
```
Stopped containers don't consume CPU but their filesystem layers remain in memory until freed by the VM.

### 5. What NOT to do
- `sudo purge` — usually not available (no passwordless sudo for automation), and only clears file cache, which gets repopulated almost immediately
- Restarting Docker Desktop — will free the ~6 GB VM memory but drops all running containers. Only do this when explicitly asked.

## Swap management

Swap at 5+ GB on a 16 GB system means physical RAM was exhausted. Options to clear swap:
- Restart Docker Desktop (stop+start via Docker menu or `killall Docker`)
- Or reboot the Mac
- Swap will slowly refill as the Docker VM grows again

There is no safe way to clear swap without process disruption.

## When memory is critically low

Signals:
- `memory_pressure` shows "critical" or "high"
- Swap > 5.5 GB and growing
- Containers being OOM-killed (`docker logs <name>` shows exit code 137)
- System UI becomes sluggish

Actions (in order of least disruptive to most):
1. `docker system prune -af`
2. Reduce container limits
3. Stop non-essential containers
4. Restart Docker Desktop
5. Reboot Mac
