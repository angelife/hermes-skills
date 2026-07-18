# Telegram Gateway Status Check

## Quick verification commands

```bash
# Check if Hermes process is running
ps aux | grep '[p]ython.*hermes'

# Check Hermes status
hermes status

# Tail recent log entries
tail -20 /Users/macos/.hermes/logs/gateway.log

# Verify Telegram gateway is listed
pgrep -fl telegram
```

## Expected output (sample)

```
macos   3973   8.4  1.2 41953600 199616 s000  S+    7:25AM   0:12.62 /usr/local/Cellar/python@3.11/3.11.12_1/Frameworks/Python.framework/Versions/3.11/Resources/Python.app/Contents/MacOS/Python /Users/macos/.local/bin/hermes
```

If the process is not found, reinstall via `hermes restart` or check logs for errors.

## Style preference note

- Keep responses concise.
- Avoid filler text.
- Use exact hardware button combinations when describing Android operations.
- Provide direct status updates; avoid speculative explanations.