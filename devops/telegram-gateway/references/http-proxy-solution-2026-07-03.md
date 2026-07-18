# HTTP Proxy Solution for send_path_degraded (2026-07-03)

## Context

The gateway uses SOCKS5 proxy (xray/v2rayN, port 10808) for Telegram API access.
Two independent failure modes were documented:

1. **`_send_path_degraded` boolean** (2026-06-30): SOCKS5 link jitter → polling
   heartbeat timeout → `_send_path_degraded = True` → all sends short-circuited
   without touching the pool. Seconds to minutes, not pool fill.

2. **TCP stream leak** (2026-07-02): SSL handshake failure through SOCKS5 →
   httpcore's `AsyncSocks5Connection.handle_async_request()` fails to call
   `stream.aclose()` on error → TCP socket leaks on xray side → proxy degrades
   → pool fills over ~28 min.

Both share the same trigger (xray proxy instability) but have different leak
mechanisms. The HTTP proxy approach targets both at once.

## The Insight

SOCKS5 protocol: failures happen at the socket level. When a connection through
SOCKS5 fails (RST, timeout), httpcore's SOCKS5 connection handler catches the
Exception but may not properly close the underlying TCP stream. The connection
object lingers.

HTTP CONNECT proxy: failures are explicit HTTP-level responses (502, 504, etc.).
httpx sees the non-200 response, knows the connection failed, and immediately
releases it from the pool. No zombie connections.

**Root cause elimination chain:**
SOCKS5 failure swallowed at socket → httpcore no reclaim → connection lingers
→ pool fills → flag locks → all send blocked.

With HTTP proxy: failure becomes explicit non-200 → httpx releases immediately
→ no pool fill → flag never triggered.

## User's Solution Ranking (Discovery Gate)

The user evaluated 4 solutions using the Discovery Gate framework
(根治度 × 工作量):

| # | Solution | 根治度 | 工作量 | User Verdict |
|---|----------|--------|--------|-------------|
| ③ | Watchdog restart / pool_size tuning | Low | Low | Stop investing — palliative, delays but doesn't cure |
| ① | HTTP proxy instead of SOCKS5 | **High** | **Low** | **DO NOW** — highest ROI, attacks root causes 1+2 |
| ② | Decouple polling/send degraded flags | Medium | Medium | Defer — maintenance cost on PTB upgrades |
| ④ | Replace proxy protocol entirely | High | High | Defer — record as candidate, revisit after ① |

Key principle: solution cost/benefit is NOT independent — ① may make ② unnecessary.

## v2rayN Config Management Pitfall

xray is managed by v2rayN (GUI client). When adding an HTTP inbound:

1. v2rayN stores Inbound config in `guiNConfig.json` (Inbound[] array)
2. v2rayN regenerates `config.json` from IN-MEMORY state on restart,
   **overwriting any manual edits to config.json**
3. The guiNConfig.json is also regenerated from memory — in-memory edits
   to the file are also overwritten
4. v2rayN restarts the proxy core when it detects the previous core died

**Workarounds tried:**
- Editing config.json directly → overwritten by v2rayN within seconds
- Editing guiNConfig.json → also overwritten from memory
- Killing xray + patching fast → v2rayN regenerates before new xray starts

**Recommendation:** Do NOT fight v2rayN for config management. Instead:
- Use a standalone HTTP→SOCKS5 bridge (see `scripts/http_to_socks_proxy.py`)
- Or configure the gateway to talk HTTP proxy protocol to xray's "mixed" inbound
  on 10808 (port already accepts HTTP CONNECT)

## Bridge Script

`scripts/http_to_socks_proxy.py` runs as a standalone Python asyncio server:

- Listens on `127.0.0.1:10809`
- Accepts HTTP CONNECT
- Forwards to SOCKS5 `127.0.0.1:10808` (xray)
- On SOCKS5 failure → HTTP 502 → httpx releases immediately

**Verification:**
```bash
# Port 10809 should LISTEN
lsof -iTCP -sTCP:LISTEN | grep 10809

# Test SOCKS5 works directly
curl --socks5-hostname 127.0.0.1:10808 -s -o /dev/null -w "%{http_code}" https://httpbin.org/ip

# Test HTTP proxy
curl -x http://127.0.0.1:10809 -s -o /dev/null -w "%{http_code}" https://httpbin.org/ip
```

## Known Issue (2026-07-03)

The bridge proxy's CONNECT tunnel establishes successfully (200), but TLS
handshake through the tunnel may hang. Root cause not yet isolated —
likely a pipe buffer issue in the bidirectional asyncio stream forwarding.
Debug in progress.
