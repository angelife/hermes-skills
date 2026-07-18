# require_mention Fix — 木同学 Telegram Gateway 2026-06-20

## Problem

木同学 (@NVIDIA2012_bot, Docker `hermes-minimaxlab-old`) was visible in the angelife任务组 but only replied when @-mentioned. Unmentioned messages were silently ignored.

## Root Cause

`config.yaml` had `telegram.require_mention: true`, which tells the gateway to only process messages containing `@bot_username`.

Independent from Telegram's BotFather privacy mode (which controls whether Telegram *sends* unmentioned messages to the bot at all). This is a Hermes gateway-level filter applied *after* receiving the message.

## Co-occurring Issue

The bot also had an expired OpenCode Zen API key (`HTTP 401: Invalid API key`), meaning that even when @-mentioned, replies failed silently. The user confirmed the key issue was already resolved.

## Diagnosis Steps

```bash
# 1. Container alive?
docker ps --filter name=hermes-minimaxlab-old --format "{{.Names}} {{.Status}}"

# 2. Gateway process running?
docker exec hermes-minimaxlab-old ps aux | grep "hermes gateway"

# 3. Read the telegram config block
docker exec hermes-minimaxlab-old grep -n -A10 "^telegram:" /opt/data/config.yaml

# Output confirmed:
# telegram:
#   reactions: false
#   channel_prompts: {}
#   allowed_chats: ''
#   exclusive_bot_mentions: false
#   require_mention: true          ← THE BUG
#   observe_unmentioned_group_messages: true
#   enabled: true
```

## Fix

```bash
# 1. Patch config
docker exec hermes-minimaxlab-old sed -i 's/require_mention: true/require_mention: false/' /opt/data/config.yaml

# 2. Verify
docker exec hermes-minimaxlab-old grep "require_mention" /opt/data/config.yaml
# All platforms' require_mention should be false now

# 3. Restart container to pick up the config change
docker restart hermes-minimaxlab-old

# 4. Wait for gateway to finish draining old sessions
sleep 15
docker exec hermes-minimaxlab-old cat /opt/data/gateway_state.json | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'Gateway: {d[\"gateway_state\"]}, Telegram: {d[\"platforms\"][\"telegram\"][\"state\"]}')"
```

## Verification

- Bot should now respond to all group messages, not just @-mentions
- Check gateway logs for successful response after restart
- If bot still silent, check model API key (providers section) — 401 errors block all replies

## Pitfalls

- Multiple platform blocks (`telegram:`, `mattermost:`, `discord:`) each have their own `require_mention`. The `sed` command with `'s/.../.../'` without a line number will change ALL occurrences. This is fine if you want all platforms to have the same setting. For a targeted change, use line-specific sed.
- A live gateway does NOT hot-reload config changes — container restart is mandatory.
- **`docker restart` may NOT restart the gateway.** In this session, after `docker restart hermes-minimaxlab-old`, the container came back up but the gateway process (`hermes gateway run`) never started. The container's default CMD is `main-wrapper.sh` with no args, which runs `hermes` (interactive shell), not the gateway. The gateway is an s6-managed service that may have a `down` file intentionally keeping it stopped. Always verify:
  ```bash
  # The single definitive check
  docker exec <container> ps aux | grep "hermes gateway"
  ```
  If empty, the gateway needs manual start. The `gateway_state.json` may lie — it showed `"gateway_state":"draining"` with an old PID even after the gateway had exited.
- **Gateway liveness triage after docker restart:**
  1. Container up? → `docker ps`
  2. Gateway process running? → `docker exec <container> ps aux | grep "hermes gateway"` (DEFINITIVE)
  3. s6 service has `down` file? → `docker exec <container> ls /run/service/gateway-default/down 2>/dev/null`
  4. Check gateway_state.json (stale indicator only, not definitive) → `docker exec <container> cat /opt/data/gateway_state.json`
- The `gateway_state.json` may show `draining` for a while after restart if old sessions need cleanup. The gateway is still functional during draining. But if `ps aux` shows no gateway process, that `draining` state is stale.
