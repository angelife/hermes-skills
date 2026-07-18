# Hermes WeChat (Weixin) iLink Bot Setup

## Overview
Configure Hermes Gateway to connect to personal WeChat accounts via Tencent's iLink Bot API. The adapter uses long-polling (no public endpoint needed).

## Prerequisites
- Hermes Gateway installed and running
- `aiohttp` and `cryptography` Python packages
- A personal WeChat account on phone

## Setup Steps

### 1. Install dependencies
```bash
pip install aiohttp cryptography
```

### 2. Run the interactive wizard
```bash
hermes gateway setup
```

### 3. Navigate in the TUI
The wizard shows a numbered list of ~27 platforms. Select **Weixin / WeChat** by entering its number (typically **3**, verify from the list).

### 4. Confirm QR login
When prompted `Start QR login now? [Y/n]:`, press Enter (default Y).

### 5. Scan QR code with WeChat
A QR code renders as ASCII art in the terminal. A URL link is also printed (e.g. `https://liteapp.weixin.qq.com/q/...`). Open the URL on the phone to scan, or screenshot the QR and scan from album.

### 6. Confirm on phone
Tap "Confirm login" on the WeChat app.

### 7. Verify
The wizard saves `account_id` and `token` to `~/.hermes/.env` automatically. Gateway now polls iLink API for messages.

## Limitations
- iLink bot is a **separate identity** (`...@im.bot`), not your personal WeChat account
- **Ordinary WeChat groups do not deliver** — iLink bot accounts typically cannot receive group events
- Only DM messages to the bot work reliably
- For group reading, use the ADB database pull approach (`android-wechat-db-decrypt` skill)

## Environment Variables (post-setup)
Set these in `~/.hermes/.env`:
```bash
WEIXIN_ACCOUNT_ID=your-account-id
WEIXIN_DM_POLICY=open
WEIXIN_ALLOWED_USERS=user_id_1,user_id_2
```
