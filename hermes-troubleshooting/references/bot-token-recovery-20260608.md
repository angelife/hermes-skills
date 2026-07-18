# Session Reference: Bot Token Mismatch Recovery

**Date:** 2026-06-08
**Session:** User requested Telegram Bot recovery

## Problem

Gateway PID 27776 was alive but Telegram connection failed with "token already in use".
The actual issue was:
1. Gateway process died (no more PIDs) but launchd plist remained stale
2. Bot token in `.env` didn't match the bot user wanted to recover
3. `--replace` flag caused token conflicts when old process didn't die cleanly

## User's Bot Config (from session)

| Bot | Username | Token |
|-----|----------|-------|
| 土 | @sir_chan_bot | 874390...cqWY |
| 水 | @masterchan19840907_bot | 874326...jTP8 |

Config used: `TELEGRAM_ALLOWED_USERS=780486548`, `TELEGRAM_HOME_CHANNEL=780486548`

## Resolution Steps

1. Killed stale gateway PIDs
2. Updated `TELEGRAM_BOT_TOKEN` in `.env` to new bot's token
3. Bootstrapped launchd service
4. Verified "Connected to Telegram (polling mode)" in logs
5. Bot commands auto-registered (30 visible + 155 hidden)

## Key Log Indicators of Healthy Bot

```
INFO gateway.platforms.telegram: [Telegram] Connected to Telegram (polling mode)
INFO gateway.run: ✓ telegram connected
INFO gateway.run: Gateway running with 1 platform(s)
INFO gateway.run: Channel directory built: 1 target(s)
INFO gateway.run: Cron ticker started (interval=60s)
INFO gateway.run: kanban dispatcher: embedded in gateway (interval=60.0s)
```

## Key Log Indicators of Failure

```
ERROR gateway.platforms.base: [Telegram] Telegram bot token already in use (PID XXXXX)
ERROR gateway.run: Gateway hit a non-retryable startup conflict: telegram
ERROR gateway.run: Non-retryable client error: HTTP 403
```