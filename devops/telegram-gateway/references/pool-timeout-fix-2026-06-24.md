# Pool Timeout Fix Record (2026-06-24)

## Problem

Telegram bot (Hermes gateway) stops responding after 1-5 hours. Gateway process alive but cannot send messages. Logs show "Pool timeout: All connections in the connection pool are occupied."

## System

- macOS 15.7 (localhost)
- Hermes Agent v0.17.0 (python-telegram-bot, HTTPX)
- SOCKS5 proxy on 127.0.0.1:10808 (xray via v2rayN)
- xray -> Cloudflare(104.19.54.45:2087) -> VLESS/WS+TLS remote server
- launchd-managed gateway daemon

## Root Cause Chain

1. xray-to-remote connections occasionally stall at Cloudflare layer
2. Connection appears "in use" to httpcore but no data flows and no RST arrives
3. SOCKS5 proxy may swallow TCP RSTs
4. Pool slots fill with zombie connections until 0 slots remain
5. Any new request gets immediate "Pool timeout"
6. After minutes-hours, some zombies eventually timeout naturally
7. Cycle repeats

## What Did NOT Work

- Adjusting pool_size (512->64->256): just changed time-to-fill
- Enabling xray mux: remote server doesn't support it, killed proxy entirely
- Setting env vars in .env and ~/.zshrc: code doesn't read them at runtime
- Setting env vars in launchd plist without code support: env vars exist but httpx pool doesn't read them — need code patch to add httpx_kwargs with Limits

## What Fixed It

Three-layer defense:

### Layer 1: TCP Keepalive (macOS kernel)
Defaults were 2 hours. Dead connections detected and freed in seconds now.
```
net.inet.tcp.keepidle=30000 (was 7200000)
net.inet.tcp.keepintvl=10000 (was 75000)
net.inet.tcp.keepinit=10000 (was 75000)
```
Persisted in /etc/sysctl.conf.

### Layer 2: httpx Limits via httpx_kwargs
Modified telegram.py connect() to pass limits with keepalive_expiry=30s and max_keepalive_connections=16 via httpx_kwargs. This overrides PTB's default Limits which only set max_connections.

### Layer 3: Periodic Client Refresh
Added _periodic_client_refresh method. Rebuilds general HTTPX client every 300 seconds (env: HERMES_TELEGRAM_HTTP_REFRESH_INTERVAL). Atomically swaps new for old so in-flight requests are not disrupted.

## Env Vars (launchd plist)

HERMES_TELEGRAM_HTTP_POOL_SIZE=256
HERMES_TELEGRAM_HTTP_POOL_TIMEOUT=30
HERMES_TELEGRAM_HTTP_CONNECT_TIMEOUT=15
HERMES_TELEGRAM_HTTP_READ_TIMEOUT=30
HERMES_TELEGRAM_HTTP_WRITE_TIMEOUT=30
HERMES_TELEGRAM_HTTP_MAX_KEEPALIVE=16
HERMES_TELEGRAM_HTTP_KEEPALIVE_EXPIRY=30
HERMES_TELEGRAM_HTTP_REFRESH_INTERVAL=300

## Code Location

/Users/macos/.hermes/hermes-agent/gateway/platforms/telegram.py

New methods added:
- _periodic_client_refresh() (near line 1388)
- Modified connect() lines 2085-2093 for httpx_kwargs
- asyncio.ensure_future call near return True (line 2352-2354)

## Verification

- Last Pool timeout: 2026-06-24 12:29:55 (old code)
- New gateway deployed: 2026-06-24 12:50
- First periodic refresh: 2026-06-24 12:55:59
- Zero Pool timeout after deployment (verified across 2+ hours)

## Failed Approaches Record

1. Env vars in launchd plist only — code doesn't read env vars for httpx limits, only for connection_pool_size
2. Pool size reduction alone — just changed time-to-fill, didn't fix root cause
3. xray mux enable — remote VLESS server didn't support it
4. Watchdog cron only — treats symptom, not cause (kept as safety net)
