# Docker Container Proxy Debugging 2026-07-18

## Symptom

New API Docker container reports `model_not_found (distributor)` despite:
- Channel configured correctly (type=1, status=1, models match, group='default')
- Token valid (not "Invalid token")
- self_use_mode disabled
- Container CAN reach the internet (baidu.com loads)
- Mac host CAN reach hetaosu upstream directly

## Root Cause

The container had `https_proxy=socks5://host.docker.internal:10808` set as env var.
`host.docker.internal` on Docker Desktop for Mac resolves to IPv6 only (`fdc4:f303:9324::254`), but v2rayN SOCKS5 proxy only listens on IPv4 `127.0.0.1:10808`.
Setting the proxy env var caused ALL hetaosu requests to fail because the container tried IPv6 -> proxy but proxy doesn't have IPv6.

## Fix

Remove ALL proxy env vars and rebuild the container without them. The container can reach hetaosu directly (no proxy needed on this network).

```bash
docker stop new-api && docker rm new-api
docker run -d --name new-api \
  -p 3000:3000 \
  -e TZ=Asia/Shanghai \
  -v /Users/macos/.hermes/data/new-api/one-api.db:/data/one-api.db \
  calciumion/new-api:latest
```

## Lesson

When debugging `model_not_found (distributor)`:
1. First check the THREE-WAY test (host direct → host proxy → container direct) — the skill's main doc has the full flowchart
2. **If the upstream is directly reachable from the container, remove ALL proxy env vars** — they can actively BREAK connectivity
3. `https_proxy` is harmful when not needed. On macOS Docker Desktop, the `host.docker.internal` IPv6 resolution bug makes it doubly dangerous
4. A batch-test of all 40 hetaosu keys showed ALL were working (HTTP 200) — the problem was the proxy env var, not the keys
