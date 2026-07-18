# Telegram Connectivity Diagnostics for Remote Hermes Gateways

## Diagnostic Chain Order

Always follow this order. Earlier links often look OK but hide the real failure.

1. **Mac/Proxy layer** — verify the proxy is listening on the right address
2. **Protocol** — HTTP CONNECT vs SOCKS5 distinction
3. **Target device** — test proxied requests from inside the device chroot
4. **Bot token** — verify via `/getMe` with a language that bypasses terminal desensitisation
5. **Config priority** — `config.yaml` `bot_token:` overrides `.env` `TELEGRAM_BOT_TOKEN`
6. **Gateway log** — look past "connected" to reconnection traces

## Step 1: Proxy Listen Address

The most common silent failure: proxy listens on `127.0.0.1:10808` only, while remote Hermes gateways (Mi6, Mi8) connect via `192.168.1.8:10808`.

```sh
lsof -i :10808
# Look for LISTEN — must be *:10808 or 192.168.1.8:10808, not just 127.0.0.1:10808
```

## Step 2: HTTP CONNECT vs SOCKS5

Hermes `python-telegram-bot` / httpx sends **HTTP CONNECT** tunnelling through `HTTPS_PROXY=http://...`.  
xray/V2Ray commonly expose a **SOCKS5** inbound on the same port — these are NOT interchangeable.

Test both from the target device's chroot:

```sh
# HTTP CONNECT
curl -x http://192.168.1.8:10808 -v https://api.telegram.org

# SOCKS5
curl -x socks5://192.168.1.8:10808 -v https://api.telegram.org
```

If HTTP works (CONNECT 200 + TLS handshake), the proxy is fit.  
If only SOCKS works, `.env` `HTTPS_PROXY=` must use `socks5://` scheme.

### Verifying CONNECT tunnel

```sh
curl -x http://192.168.1.8:10808 -v https://api.telegram.org/bot<TOKEN>/getMe 2>&1 | head -30
```

Expected: `CONNECT api.telegram.org:443 HTTP/1.1` → `HTTP/1.1 200 Connection established` → TLS handshake → HTTP 200.

## Step 3: Bot Token Validation

**Critical: terminal output desensitisation** silently replaces token secrets with `***`.  
Commands like `grep`, `cat`, `sed` show `TELEGRAM_BOT_TOKEN=8858037161:***` — the `***` corresponds to real bytes that were read but masked.

Verify with a language runtime that prints hex, not text:

```py
import json, urllib.request
token = open('/root/.hermes/.env').readlines()
# extract real token programmatically
# then:
url = 'https://api.telegram.org/bot' + real_token + '/getMe'
resp = urllib.request.urlopen(url, timeout=10)
print(resp.status, json.loads(resp.read()))
```

- **200** + `"ok": true` → token valid
- **401** `Unauthorized` → token exists but expired/revoked
- **404** `Not Found` → token does not exist (most likely: desensitised shell printed `***` but actual request used `***` as literal chars)

## Step 4: Config Priority (env vs config.yaml)

`config.yaml` `bot_token:` value **always overrides** `.env` `TELEGRAM_BOT_TOKEN` in the current Hermes version.

If they differ, Hermes uses the config.yaml value, not the env value.  
**Fix**: either delete the `bot_token:` line from config.yaml, or keep both in sync.

## Step 5: Gateway Log Interpretation

A "Connected to Telegram (polling mode)" entry does NOT guarantee stable connectivity.  
Look for trailing reconnection patterns:

```
Reconnecting telegram (attempt N)...
Connect attempt N/8 failed: httpx.ConnectError
telegram connect timed out after 30s
```

These indicate the initial handshake succeeded but long-lived polling is broken — usually a proxy/TLS/timing issue.

## Common Pitfalls

| Pitfall | Symptom | Fix |
|---------|---------|-----|
| Proxy only on 127.0.0.1 | Remote gateway can't connect | Bind xray to `0.0.0.0` |
| `.env` uses `http://` but xray is SOCKS only | Same connection failure | Change to `HTTPS_PROXY=socks5://...` |
| config.yaml bot_token != .env token | Gateway authenticates with wrong token | Sync or delete from config.yaml |
| Terminal desensitisation | Token appears valid but API returns 404 | Read bytes, not text |
| NO_PROXY includes Telegram IP | Proxy settings silently bypassed | Ensure `NO_PROXY` does not contain `api.telegram.org` or fallback IPs |
| Device time skew > hours | TLS handshake succeeds but polling drops | Sync device time with `date -s` or ntpd |

## Verification Flow (Telegram end-to-end)

After any fix, the minimum proof is:

1. From Mac: `curl https://api.telegram.org/bot<TOKEN>/getMe` → HTTP 200
2. From device chroot via proxy: `curl -x <proxy> https://api.telegram.org/bot<TOKEN>/getMe` → HTTP 200
3. Gateway log: `✓ telegram connected` followed by no reconnection errors for 2+ cycles
4. `/proc/<pid>/environ` shows `TELEGRAM_BOT_TOKEN` with correct value
