# Gateway Pool Timeout / Proxy Connectivity Stuck

## Symptom

Gateway process is alive but bot doesn't respond. User messages arrive (inbound OK) but replies never deliver. Log shows repeating `Pool timeout: All connections in the connection pool are occupied`.

## Typical Log Signature

```
Pool timeout: All connections in the connection pool are occupied.
... (10 retries with increasing backoff) ...
Fatal telegram adapter error: ... polling could not reconnect after 10...
Restarting gateway.
Reconnecting telegram (attempt 1)...
Connected to Telegram (polling mode)
✓ telegram reconnected successfully
... (few minutes later, same cycle repeats) ...
```

The gateway enters a **connect → work briefly → Pool timeout → reconnect → repeat** cycle.

## Diagnostic Flow

### Step 1: Confirm the pattern in gateway logs

```bash
tail -200 ~/.hermes/logs/gateway.log | grep -E "Pool timeout|send_path_degraded|Not connected|reconnect|Fatal telegram"
```

### Step 2: Check proxy process

```bash
ps aux | grep -E "sing-box|clash|v2ray|xray"
```

### Step 3: Measure proxy latency to Telegram API

```bash
curl -s -o /dev/null -w "http_code=%{http_code} time=%{time_total}s\n" \
  --proxy http://127.0.0.1:10808 -m 10 https://api.telegram.org/bot
```

If response takes **>2 seconds**, the proxy is adding significant latency.

### Step 4: Test both HTTP and SOCKS5 proxy schemes

```bash
curl -s -o /dev/null -w "time=%{time_total}s\n" --proxy http://127.0.0.1:10808 -m 10 https://api.telegram.org/bot
curl -s -o /dev/null -w "time=%{time_total}s\n" --socks5 127.0.0.1:10808 -m 10 https://api.telegram.org/bot
```

## Root Cause Model

Each Telegram API request (polling poll, send message, edit message) holds a connection in the pool. When the proxy adds **2–4 seconds latency** per request, concurrent requests exhaust the pool faster than connections return to the pool. Result: new requests queue → timeout → gateway restarts its Telegram adapter → cycle repeats.

## Pitfalls

- **Do NOT** jump to restarting the gateway or adjusting pool size parameters — the real fix is proxy latency, not gateway config.
- **Do NOT** claim "gateway crashed" — the process is alive; it's the Telegram connection layer that's cycling.
- **Do NOT** offer to "fix it" immediately — present the evidence (cycle pattern + proxy latency) and let the user decide. The proxy may be serving multiple devices intentionally (e.g. an Android phone using the same port), and the latency is an architectural constraint, not a bug.

## See Also

- `scripts/telegram-gateway-diag-proxied.py` — automated proxy-aware diagnostic script
- `references/parallel-cascade-fd-docker-proxy-20260622.md` — related proxy diagnostics
