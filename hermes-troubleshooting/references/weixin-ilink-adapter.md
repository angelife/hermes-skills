# WeChat (Weixin) iLink Bot Adapter — Setup & Known Issues

## Overview

Hermes connects to personal WeChat accounts via **Tencent iLink Bot API**. This is a separate bot identity (`@im.bot`), **not** a scriptable personal WeChat account.

## Setup Flow

```bash
hermes gateway setup
```

1. Select **Weixin / WeChat** (option 3 from the platform menu)
2. Read the intro, then answer **Y** to "Start QR login now?"
3. A QR code URL is displayed (e.g. `https://liteapp.weixin.qq.com/q/7GiQu1?qrcode=...&bot_type=3`)
4. **User opens URL in WeChat on phone** → scans the QR → confirms login
5. Wizard stores credentials automatically to `~/.hermes/weixin/accounts/<account_id>.json`
6. Configure **DM pairing**:
   - Option 1: "Use DM pairing approval" (recommended) — user must pair before bot accepts DMs
   - Option 2: "Allow all direct messages" — anyone can DM the bot
7. Configure **group chats**: defaults to "Disable group chats" (recommended — iLink bots can't join regular groups anyway)
8. Set **home channel** (Y to use the WeChat user ID)
9. **Restart gateway** to pick up changes

## Credential Storage

- `~/.hermes/weixin/accounts/<account_id>.json` — token, base_url, user_id
- `~/.hermes/weixin/accounts/<account_id>.sync.json` — sync state
- `~/.hermes/weixin/accounts/<account_id>.context-tokens.json` — context tokens

## Pairing Approval

After setup, when a user DMs the bot for the first time, the bot replies with a pairing code:

```
Here's your pairing code: XXXXXXXX
Ask the bot owner to run: hermes pairing approve weixin XXXXXXXX
```

Run the approve command from the host:

```bash
hermes pairing approve weixin XXXXXXXX
```

Once approved, the user is recognized on next message.

## Key Limitations (iLink Bot Identity)

| Limitation | Detail |
|-----------|--------|
| **Bot identity is separate** | The iLink bot (`aafc20df8008@im.bot`) is NOT your personal WeChat account |
| **Groups don't work** | `@im.bot` identities typically cannot be invited to ordinary WeChat groups |
| **Group events not delivered** | iLink does not deliver ordinary-group events to most bot accounts |
| **Only DMs work reliably** | The adapter's primary working channel is direct messages to the bot |

## Pitfalls

- **QR code expires quickly** (a few minutes). User must scan promptly after generation.
- **Killing the setup wizard before confirmation loses credentials.** The wizard only saves the token after receiving the iLink confirmation response. Always wait for "微信连接成功" before exiting.
- **Cannot restart gateway from inside gateway session.** Run `hermes gateway restart` from a separate shell.
- **Model config drift affects the gateway.** If the gateway can't start, check `~/.hermes/logs/gateway.log` for errors.

## Verification

Check gateway log for WeChat adapter connection:

```bash
tail -30 ~/.hermes/logs/gateway.log | grep -i weixin
```

Expected output on successful connection:

```
INFO gateway.run: Queued inbound message during gateway startup restore: platform=weixin chat=...
INFO gateway.platforms.weixin: [Weixin] inbound from=... type=dm media=0
```

## Related

- Hermes docs: [Weixin Setup](https://raw.githubusercontent.com/NousResearch/hermes-agent/refs/heads/main/website/docs/user-guide/messaging/weixin.md)
- This adapter uses iLink Bot API, distinct from WeCom (Enterprise WeChat) adapter.
