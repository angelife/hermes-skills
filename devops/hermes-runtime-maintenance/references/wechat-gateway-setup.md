# WeChat (Weixin) Gateway Setup via Hermes CLI

> Reference file under `hermes-runtime-maintenance`.
> Covers the interactive TUI session for configuring the WeChat/Weixin messaging platform
> adapter via `hermes gateway setup`, including QR login flow.

## When to Use This

- User wants Hermes to send/receive WeChat messages (personal account)
- You need to add a new messaging platform adapter to a running Hermes Gateway

## Prerequisites

- Python packages: `aiohttp cryptography` (install separately if not bundled)
- User's phone with WeChat installed (for QR scan)
- Hermes Gateway running (verified by `hermes gateway setup` showing "Gateway service is installed and running")

## Setup Flow

### 1. Start the Setup Wizard

```bash
hermes gateway setup
```

This launches a terminal TUI. Since we're automating from an agent context, run it in a
PTY background process:

```bash
# In terminal tool:
hermes gateway setup
# → Use background=true + pty=true
```

### 2. Navigate to WeChat (Weixin)

The TUI presents a numbered list of 27+ platforms. WeChat is option **3**.
Send the number via process submit:

```bash
# Wait for the "Choice [default 27]:" prompt, then:
process(action="submit", session_id="...", data="3")
```

### 3. Confirm QR Login

The wizard displays an info screen then asks "Start QR login now? [Y/n]:"

```bash
# Wait for the "[Y/n]:" prompt, then:
process(action="submit", session_id="...", data="Y")
```

### 4. Capture the QR URL

The wizard displays:
```
请使用微信扫描以下二维码：
https://liteapp.weixin.qq.com/q/7GiQu1?qrcode=XXXX&bot_type=3
[ASCII QR code]
```

**Important:** The QR code has a short TTL (~3 minutes). Extract the URL from
the process log immediately and share it with the user. The URL opens a WeChat
lite page that shows the QR code.

The QR uses Tencent's **iLink Bot API** — this is a separate bot identity, NOT
the user's personal WeChat account. The bot appears in the user's WeChat contacts
after scanning.

### 5. User Scans QR Code

User opens the URL in WeChat → scans the QR code → confirms login on their phone.
The wizard then receives the `account_id` and `token` from iLink and saves them
automatically to `~/.hermes/weixin/accounts/` and the env vars to `~/.hermes/.env`.

### 6. Verify Credentials Saved

```bash
grep WEIXIN ~/.hermes/.env
ls ~/.hermes/weixin/accounts/   # should contain account config
```

### 7. Restart Gateway

```bash
hermes gateway restart
```

After restart, the WeChat adapter begins long-polling for messages.

## Known Limitations

| Limitation | Details |
|-----------|---------|
| **Bot identity** | iLink bot (`...@im.bot`) is separate from user's personal account |
| **Group messages** | Most iLink bot identities cannot receive ordinary WeChat group events — DMs only |
| **QR TTL** | ~3 minutes — user must scan quickly |
| **Persistence** | If the setup wizard is killed before confirmation, credentials are NOT saved; must redo |
| **Gateway restart** | Cannot be done from inside the gateway process itself (SIGTERM propagates) |

## Pitfalls

- **Setup wizard killed too early**: Wait for the "微信连接成功" confirmation message
  before killing the setup process. The QR scan creates the bot on the iLink side,
  but credentials are only saved to disk after the wizard receives the confirmation.
- **Multiple gateway instances**: If the gateway is already running, the TUI still works
  (it doesn't require the gateway to be stopped). But after saving credentials,
  the running gateway needs to be restarted to pick up the new platform.
- **No weixin directory after QR scan**: If `~/.hermes/weixin/` doesn't exist after the
  scan, the credentials were not saved — kill and redo the full flow.
