# Android chroot Telegram gateway debugging patterns

## Session: 2026-07-07 (Mi6 水同学, Mi8 金同学)

### 1. Proxy address mismatch

**Symptom**: gateway.log shows `Connect attempt failed: Timed out` with a proxy address you didn't configure.

**Root cause**: `.env` has a stale/orphaned proxy address that Hermes reads instead of the shell env var. On Android chroot, `export HTTP_PROXY=...` before `hermes gateway run` does NOT propagate if `.env` has the same key.

**Debug workflow**:
```
# 1. Check what proxy Hermes actually uses
grep "Proxy detected" /root/.hermes/logs/gateway.log

# 2. Compare .env vs shell environment
grep -i proxy /root/.hermes/.env
cat /proc/<pid>/environ | tr '\0' '\n' | grep -i proxy

# 3. Verify reachability from inside chroot
curl -s -o /dev/null -w "%{http_code} %{time_total}s" --max-time 10 \
  -x socks5://<expected-ip>:10808 https://api.telegram.org
curl -s -o /dev/null -w "%{http_code} %{time_total}s" --max-time 10 \
  -x socks5://<stale-ip>:10808 https://api.telegram.org  # This should fail

# 4. Fix: rewrite .env with correct proxy, then kill+restart gateway
```

**Key insight**: Hermes 0.18.0 reads `.env` from `~/.hermes/.env` at startup. If `.env` has proxy vars, they **override** the shell environment. To fix, edit `.env`, don't export in shell.

### 2. PTB version compatibility with Hermes 0.18.0

**Symptom**: `HTTPXRequest.__init__() got an unexpected keyword argument 'httpx_kwargs'` in gateway.log.

**Root cause**: Hermes 0.18.0 Telegram adapter creates `HTTPXRequest(httpx_kwargs=_with_limits())`. PTB 20.8 does NOT support `httpx_kwargs`. PTB ≥21.10 supports it.

**Fix**:
```
pip install --no-cache-dir "python-telegram-bot>=21.10,<22"
```

Verify with:
```
python3 -c "import inspect, telegram.request as r; print(inspect.signature(r.HTTPXRequest.__init__))"
# Should show httpx_kwargs in the signature
```

**Do NOT** manually pin PTB 20.8 unless you know the adapter doesn't use `httpx_kwargs`.

### 3. .env auto-loading failure in chroot

**Symptom**: Gateway starts but says "No messaging platforms enabled" even though `.env` has `TELEGRAM_BOT_TOKEN`. Process environ shows `HOME=/` and no Telegram vars.

**Root cause**: Hermes 0.18.0 auto-loads `.env` only when the runtime can detect it. Inside chroot (especially when started via `chroot ... /bin/sh -lc`), the detection may fail. The process environ will lack all `.env` vars.

**Fix**: Explicitly source `.env` before starting the gateway:
```
# In the same shell process:
set -a; . /root/.hermes/.env; set +a
export TELEGRAM_BOT_TOKEN TELEGRAM_ALLOWED_USERS HTTPS_PROXY HTTP_PROXY ...
/root/.hermes/hermes-agent/venv/bin/hermes gateway run --replace
```

**Verify**: Check `/proc/<pid>/environ` after start for the expected vars.

### 4. Gateway lifecycle on Android chroot

**Symptom**: Two gateways running (one host PID, one chroot PID). `--replace` doesn't work as expected.

**Root cause**: On Android, Hermes can run as:
- **Host process** (started from Android shell, using chroot filesystem paths) — behaves as a standard process
- **Chroot process** (started via `chroot ...`) — different PID namespace behavior

**Kill workflow** (kill from host, not from inside chroot):
```
adb shell su 0 -c "kill -9 <PID1> <PID2>"
adb shell su 0 -c "pkill -9 -f hermes"  # nuclear option
```

**Start workflow**:
```
adb shell su 0 -c 'chroot /data/local/tmp/chroot/debian /bin/sh -lc \
  ". /root/.hermes/.env && export ... && /root/.hermes/hermes-agent/venv/bin/hermes gateway run --replace >> /root/.hermes/logs/gateway.log 2>&1 &"'
```

### 5. Bot token validation

**Symptom**: `telegram.error.InvalidToken` or `401 Unauthorized`.

**Check directly** (bypasses Hermes):
```
curl -sS --max-time 10 -x <proxy> \
  https://api.telegram.org/bot<TELEGRAM_BOT_TOKEN>/getMe
```

If 200/OK → Hermes adapter issue. If 401 → token wrong/revoked.
