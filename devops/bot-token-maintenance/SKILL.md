---
name: bot-token-maintenance
description: Diagnose and fix Telegram bot token issues across Hermes agents (local Mac, Android chroot). Covers the `***` shell-substitution corruption pattern, .env repair, and gateway restart.
---

# Bot Token Maintenance

## Symptoms
- Bot doesn't respond in group chat / DM
- Gateway fails to connect to Telegram
- `.env` or `config.yaml` shows `***` instead of a real token
- `getMe` API call returns 401 Unauthorized

## Root Cause
When `.env` files are written via shell (echo, sed, heredoc), variable references like `${TELEGRAM_BOT_TOKEN}` or `${BOT_TOKEN}` expand to empty if the variable isn't set in that shell context, leaving **literal `***`** as the token value. The triple-asterisk pattern is a dead giveaway.

This happens commonly during:
- Initial `scp` of `.env` template followed by manual sed
- Shell scripts that source `.env` then rewrite it
- Accidental `echo` expansion

## Verification

### 1. Test token directly via Telegram API
```bash
curl -s "https://api.telegram.org/bot<TOKEN>/getMe"
```
Expected: `{"ok":true,"result":{"id":...}}`  
If 401: token is invalid. Check the raw bytes in the file.

### 1b. Test token via proxy (when direct connection is blocked)
If direct `curl` times out (possible GFW blocking), test through the SOCKS5 proxy:
```bash
# First verify the proxy itself works
curl -s --max-time 10 -x socks5://127.0.0.1:10808 https://httpbin.org/ip

# Then test the token through the proxy
curl -s --max-time 10 -x socks5://127.0.0.1:10808 "https://api.telegram.org/bot<TOKEN>/getMe"
```
⚠️ `no_proxy`/`NO_PROXY` env vars in `.env` can cause `-x` to be ignored. Before testing, either `unset no_proxy NO_PROXY` or use `--noproxy '*'`.
- Proxy returns `{"ok":true,...}` → token is valid, network issue (see telegram-gateway skill's NO_PROXY bypass diagnosis)
- Proxy returns `401 Unauthorized` → token is truly invalid
- Proxy times out too → proxy chain is broken (check xray/v2rayN)

### 2. Inspect actual file content (terminal redacts secrets)
```bash
# On local Mac:
xxd ~/.hermes/.env | grep BOT_TOKEN

# Over SSH:
ssh user@host "xxd ~/.hermes/.env | grep BOT_TOKEN"

# On Android via ADB:
adb shell "su 0 -c 'cat /path/to/.env'" 2>/dev/null | grep BOT_TOKEN | xxd
```
Look for `***` (0x2a 0x2a 0x2a) vs a real token (starts with `AA...`).
Also watch for **token duplication** (token value appears twice concatenated) — can happen when sed/python replacement scripts run partially.

## Fix Procedure

### A. Get the correct token
Ask the user to provide it. Bot tokens follow the format:
```
<digits>:AA<alphanumeric>
```
Example: `8858037161:AAEugv10JJDddYQKxcyMD_UxSKw5ULDOoMg`

The bot identity (firstName, username) in `getMe` response confirms which bot it is.

### B. Update .env on device

#### Local Mac
```bash
# Method 1: sed (replace entire line)
sed -i '' 's/^TELEGRAM_BOT_TOKEN=.*$/TELEGRAM_BOT_TOKEN=<CORRECT_TOKEN>/' ~/.hermes/.env

# Method 2: Python (safer)
python3 -c "
with open('/Users/macos/.hermes/.env', 'r') as f:
    c = f.read()
c = c.replace('TELEGRAM_BOT_TOKEN=...', 'TELEGRAM_BOT_TOKEN=<CORRECT_TOKEN>')
with open('/Users/macos/.hermes/.env', 'w') as f:
    f.write(c)
"
```

#### Remote Mac (via SSH)
```bash
ssh user@host "sed -i '' 's/^TELEGRAM_BOT_TOKEN=.*$/TELEGRAM_BOT_TOKEN=<CORRECT_TOKEN>/' ~/.hermes/.env"
```
⚠️ Remote Mac may have broken Python (xcrun error) — use `sed`.

#### Android chroot (via ADB)
**Step 1**: Pull .env to local
```bash
adb -s <DEVICE_ID> shell "su 0 -c 'cat /data/local/tmp/chroot/debian/root/.hermes/.env'" 2>/dev/null > /tmp/device_env.txt
```

**Step 2**: Fix locally (Python)
```bash
python3 -c "
with open('/tmp/device_env.txt', 'r') as f:
    c = f.read()
c = c.replace('TELEGRAM_BOT_TOKEN=<OLD_BAD_VALUE>', 'TELEGRAM_BOT_TOKEN=<CORRECT_TOKEN>')
with open('/tmp/device_env.txt', 'w') as f:
    f.write(c)
"
```

**Step 3**: Push back
```bash
adb -s <DEVICE_ID> push /tmp/device_env.txt /data/local/tmp/env_fixed.env
adb -s <DEVICE_ID> shell "su 0 -c 'cp /data/local/tmp/env_fixed.env /data/local/tmp/chroot/debian/root/.hermes/.env && chmod 600 /data/local/tmp/chroot/debian/root/.hermes/.env'"
```

### C. Remove bot_token from config.yaml (CRITICAL)

If `telegram.bot_token` in config.yaml has `***`, **remove the entire line** or delete the key.
Do NOT just replace it — Hermes reads `telegram.bot_token` from config.yaml directly and the literal `***` value
will override the correct `TELEGRAM_BOT_TOKEN` from `.env`.

```bash
# On local Mac — remove the bot_token line
sed -i '' '/bot_token:/d' ~/.hermes/config.yaml

# On remote Mac via SSH
ssh user@host "sed -i '' '/bot_token:/d' ~/.hermes/config.yaml"

# On Android chroot — pull → edit → push (add `grep -v bot_token` filter)
adb -s <DEVICE_ID> shell "su 0 -c 'cat ...config.yaml | grep -v bot_token > /tmp/config_clean.yaml && mv /tmp/config_clean.yaml .../config.yaml'"
```

**After removing, verify:**
```bash
grep bot_token config.yaml  # should return empty / no match
```

The correct token lives in `.env` as `TELEGRAM_BOT_TOKEN=...` — Hermes v0.18.0
reads this env var when `telegram.bot_token` is absent from config.yaml.

### D. Restart gateway

Always use `--replace` to handle existing gateway instances gracefully.
Use `set -a && source .env && set +a` (not just `source .env`) to export all
variables — critical in chroot where `env` may otherwise be empty.

#### Local Mac
```bash
cd ~/.hermes && set -a && source .env && set +a && \
  exec venv/bin/hermes gateway run --replace
```

#### Remote Mac (via SSH)
```bash
ssh user@host "cd ~/.hermes && set -a && source .env && set +a && \
  exec venv/bin/hermes gateway run --replace"
```

#### Android chroot (via ADB)
```bash
adb -s <DEVICE_ID> shell "su 0 -c 'chroot /data/local/tmp/chroot/debian /bin/bash -c \
  \"cd /root/.hermes && set -a && source .env && set +a && \
   /root/.hermes/venv/bin/hermes gateway run --replace\"'"
```
**Note:** `nohup` is often NOT installed in minimal chroots — omit it entirely.
For backgrounding, drop `exec` and append `&` at the end.
For first launch, run foreground to see the initial error message.

## Quick Test (Direct API)
After fixing the token, test immediately by sending a message directly:
```bash
curl -s -X POST "https://api.telegram.org/bot<TOKEN>/sendMessage" \
  -d "chat_id=<GROUP_ID>" \
  -d "text=Test message from bot" \
  -d "message_thread_id=<THREAD_ID>"
```

## Sending File Attachments via Bot API

When the user asks for a file (document, photo, etc.) to be delivered to Telegram, use the Bot API's `sendDocument` endpoint directly. This is necessary when the Hermes Telegram adapter doesn't have a native file-attachment tool.

### Get the token
```bash
source ~/.hermes/.env
# Token is now in $TELEGRAM_BOT_TOKEN
```

### Send a text file as document attachment
```bash
source ~/.hermes/.env && curl -s \
  -F document=@/path/to/file.txt \
  -F caption="Optional caption" \
  "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendDocument?chat_id=-1003926068725"
```

Parameters:
- `chat_id`: The target group/DM. `-1003926068725` = angelife任务组 (Home), `780486548` = DM with angelife tse
- `document=@/path`: Attach a local file (`@` prefix tells curl to read the file)
- `caption`: Optional text shown below the file in the chat
- `?message_thread_id=N`: Required for forum topics (Home group uses thread_id=1)

### Verification
The Bot API returns JSON with `"ok":true` and the sent message's `message_id` on success.

### Pitfalls
- **Token redacted in terminal output**: `grep TELEGRAM_BOT_TOKEN .env` shows `***` in Hermes runtime. Source the .env file directly and use `$TELEGRAM_BOT_TOKEN` in the curl command — the token works at the API level even though it's redacted from display.
- **Chat ID for forum groups**: The Home group is a forum (`is_forum:true`). `sendDocument` without `message_thread_id` fails silently or delivers to the wrong topic. Always include `message_thread_id=<THREAD_ID>` when sending to topic groups.
- **File path must exist**: `curl -F document=@/nonexistent/path` returns a curl error, not a Telegram error. Verify the file exists before sending.
- **File size limit**: Telegram Bot API limits documents to 50MB. Text files under that are fine.

### Example (this session — 2026-07-07)
The user requested `key.txt` as an attachment in the Telegram group:
```bash
source ~/.hermes/.env && curl -s \
  -F document=@/tmp/key_for_telegram.txt \
  -F caption="key.txt备份" \
  "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendDocument?chat_id=-1003926068725"
```
Result: `{"ok":true, "result":{"message_id":8360, ...}}` — file delivered to angelife任务组.

## Prevention
- Never edit `.env` with `echo` or shell heredocs that expand `${VAR}` — use Python's string replace or `sed -i '' 's/^KEY=.*$/KEY=VALUE/'`
- After any `.env` change, verify with `xxd` (not cat) to catch redaction/duplication
- Keep a backup of valid tokens in the user's secure key store (e.g. `~/key.txt`)
- Use `TELEGRAM_BOT_TOKEN` env var in `.env` and **remove** `telegram.bot_token` from config.yaml entirely — env var override is safer

## References
- [`references/shell-quoting-pitfalls.md`](references/shell-quoting-pitfalls.md) — SSH/ADB quoting, macOS vs GNU sed, terminal redaction behavior
