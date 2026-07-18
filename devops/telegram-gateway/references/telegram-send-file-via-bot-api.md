# Sending File Attachments via Telegram Bot API

When user asks "把文件发到群里" or "作为附件发给我", use the Telegram Bot API
`sendDocument` endpoint directly via curl. This sends a real file attachment
(not inline text) to the target chat.

## Prerequisites

- Bot token: stored in `TELEGRAM_BOT_TOKEN` env var in `~/.hermes/.env`
- Chat ID of the target group/DM

## Command Pattern

```bash
source /Users/macos/.hermes/.env && \
curl -s -F document=@/path/to/file \
  "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendDocument?chat_id=<CHAT_ID>&caption=<optional_caption>"
```

### Parameters

| Field | Description |
|-------|-------------|
| `document=@/path/to/file` | File to attach (curl `-F` with `@` prefix) |
| `chat_id` | Target chat ID (e.g. `-1003926068725` for angelife任务组) |
| `caption` | Optional message text shown below the file |

## Verification

Response contains `"ok":true` with a `result` block including `message_id`,
`file_name`, `file_size`, and `sender_tag`.

## Chat IDs (this installation)

| Target | Chat ID |
|--------|---------|
| angelife任务组 (Home) | `-1003926068725` |
| User DM (angelife tse) | `780486548` |

## Common Pitfalls

- **Redacted bot token in terminal output**: `TELEGRAM_BOT_TOKEN` appears as
  `8743908333:***` in `cat`/`grep` output. Always use `source .env` to get the
  actual value into the shell — do NOT read it from terminal display.
- **File contains secrets**: The `-F document=@file` sends raw bytes. If the
  file is sensitive, the user must explicitly authorize the send.
- **MIME type**: Telegram auto-detects from file extension. `.txt` → `text/plain`.
- **Complete vs abbreviated**: When user says "完整的", use the base64 bypass
  (see M18 in angelife-minimal-execution-style) to get verbatim original bytes
  before sending. Never placeholder-replace content.
- **Chat ID must be correct**: Sending to a group requires the negative ID.
  Sending to a DM uses the user's numeric ID (positive).

## See Also

- [Telegram Bot API — sendDocument](https://core.telegram.org/bots/api#senddocument)
