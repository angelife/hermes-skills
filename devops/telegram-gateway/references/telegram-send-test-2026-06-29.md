# Quick Test: Hermes Telegram Send

- **Command**: `hermes send --to telegram "Hello, this is a test message from Hermes."`
- **Result**: Exit code `0`, output `Sent to telegram home channel (chat_id: -1003926068725)`
- **Verification**: Checked `~/.hermes/logs/gateway.log` for `Sent to telegram` entry.
- **Notes**: Works for direct messaging without launching full agent; can be used for connectivity checks. Media attachments can be sent by prefixing `MEDIA:/path/to/file` in the message text.