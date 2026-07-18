# Gateway Env Injection Verification

## Problem

Hermes gateway uses environment variables for secrets (API keys, tokens, proxy settings).
When the gateway process does NOT inherit these vars, it either:
- Falls back to `config.yaml` plaintext (which may be wrong/stale)
- Fails with 401/404 at the external service
- Cannot connect to Telegram even though the proxy is working

## Root Cause Patterns

| Symptoms | Root Cause | Check |
|----------|-----------|-------|
| Gateway connected via Telegram but replies fail 401 | `config.yaml` `api_key` overrides `.env` | `grep api_key config.yaml` |
| Gateway can't connect to Telegram at all | `config.yaml` `bot_token` != `.env` `TELEGRAM_BOT_TOKEN` | Compare both files |
| Gateway connects but can't proxy through | `HTTPS_PROXY` in `.env` but `NO_PROXY` blocks Telegram IPs | Check `.env` `NO_PROXY` |
| Gateway starts but has no API key at runtime | `.env` exists but launch script didn't `source` it | Check `/proc/<pid>/environ` |

## Verification: `/proc/<pid>/environ`

**The only reliable way to confirm what a running Hermes gateway actually sees for environment variables.**

### Quick check (single PID, grep for known keys)

```python
import glob
for p in glob.glob('/proc/[0-9]*/cmdline'):
    try:
        if b'hermes gateway run' in open(p, 'rb').read():
            pid = p.split('/')[2]
            data = open('/proc/' + pid + '/environ', 'rb').read().decode('utf-8', 'ignore')
            hits = [l for l in data.split('\x00') 
                    if l.startswith(('AGNES_API_KEY=', 'HINDSIGHT_API_KEY=', 
                                     'HINDSIGHT_API_URL=', 'TELEGRAM_BOT_TOKEN='))]
            print(f'PID={pid}')
            print('\n'.join(hits) if hits else 'NO_ENV_IN_PROC')
    except:
        pass
```

### Full dump of relevant vars (for all gateways)

```python
import glob
for p in glob.glob('/proc/[0-9]*/cmdline'):
    try:
        if b'hermes gateway run' in open(p, 'rb').read():
            pid = p.split('/')[2]
            env_data = open('/proc/'+pid+'/environ', 'rb').read().decode('utf-8', 'ignore')
            hits = [l for l in env_data.split('\x00') 
                    if l.startswith(('AGNES_API_KEY=', 'HINDSIGHT_API_KEY=',
                                     'HINDSIGHT_API_URL=', 'HTTPS_PROXY=',
                                     'HTTP_PROXY=', 'NO_PROXY=', 
                                     'TELEGRAM_BOT_TOKEN='))]
            print(f'PID={pid}')
            for h in hits:
                print(h)
    except:
        pass
```

## On Android Chroot

On Android devices with a Debian chroot, the technique is identical — just run the Python script inside the chroot:

```
adb shell 'su 0 -c "chroot /data/local/tmp/chroot/debian /usr/bin/python3 /tmp/check_env.py"'
```

Push the script to `/data/local/tmp/` first, then copy into the chroot `/tmp/` and execute.

**Limitations inside Android chroot:**
- `pidof` is not available — use glob over `/proc/[0-9]*/cmdline`
- `pkill`, `sleep`, `rm`, `wc` may not exist — use Python equivalents (`os.kill`, `time.sleep`, `os.remove`, `len`)
- Android shell quoting is fragile — prefer pushing `.py` files and executing them directly

## Telegram Bot Token Verification

To test a Telegram bot token directly (bypassing Hermes):

```python
import urllib.request, json
url = f'https://api.telegram.org/bot{TOKEN}/getMe'
resp = urllib.request.urlopen(url, timeout=10)
data = json.loads(resp.read())
# 200 + ok:true = valid
# 404 = token does not exist (bot was deleted/never created)
# 401 = token format wrong or unauthorized
```

## Priority: config.yaml vs .env

```
config.yaml bot_token:  ❌ overrides .env TELEGRAM_BOT_TOKEN
config.yaml api_key:    ❌ overrides .env AGNES_API_KEY (if present)
```

**Fix**: Delete the secret from `config.yaml` so `.env` takes effect. Or align them exactly.

## Proxy Verification from Android Chroot

```
# HTTP CONNECT
curl -x http://192.168.1.8:10808 -sS -o /dev/null -w "%{http_code}" https://api.telegram.org/bot<TOKEN>/getMe

# SOCKS5
curl -x socks5://192.168.1.8:10808 -sS -o /dev/null -w "%{http_code}" https://api.telegram.org/bot<TOKEN>/getMe

# 200 = everything works end-to-end
# 404 = proxy OK, but token invalid
# timeout/connection refused = proxy or network issue
```
