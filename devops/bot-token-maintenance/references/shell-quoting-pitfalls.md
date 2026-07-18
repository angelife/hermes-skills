# Shell Quoting & Terminal Redaction Pitfalls

## Terminal Redaction
The terminal tool **automatically redacts** known secret patterns (bot tokens, API keys)
from displayed output. When you `cat` a file containing a valid token, you'll see `***`
even though the actual file content is correct.

**Always verify with hexdump:**
```bash
xxd file.env | grep BOT_TOKEN
adb shell "cat file.env" 2>/dev/null | grep TOKEN | xxd
```
Look for the actual token bytes (starts with `AA...`) vs literal `*` bytes (0x2a).

## SSH Variable Expansion
When running SSH commands, variables in **single quotes do NOT expand**:

```bash
# ❌ WRONG — $VAR stays as literal text
ssh host "curl -H 'Authorization: Bearer $TOKEN' ..."

# ✅ CORRECT — source .env in the same shell context
ssh host ". ~/.env && curl -H 'Authorization: Bearer $TOKEN' ..."

# ✅ ALSO CORRECT — use double quotes with escaped inner quotes
ssh host "curl -H \"Authorization: Bearer $TOKEN\" ..."
```

## ADB + chroot quoting
ADB shell commands go through **three layers** of shell parsing (adb → su → chroot):
- Each layer strips one level of quoting
- Use escaped double quotes `\"...\"` for the innermost shell
- Use single quotes for the su/chroot wrapper

```bash
# Pattern for ADB + su + chroot:
adb shell "su 0 -c 'chroot /data/local/tmp/chroot/debian /bin/bash -c \"command \$VAR\"'"
```
Note: `$VAR` must be escaped as `\$VAR` to prevent expansion at the host shell level.

## macOS sed differs from GNU sed
macOS sed uses `\\*` (not `*`) to match literal asterisks:
```bash
# On macOS / BSD sed:
sed -i '' 's/\\*\\*\\*/REAL_TOKEN/' file   # escape each *

# On Linux / GNU sed:
sed -i 's/\*\*\*/REAL_TOKEN/g' file
```

## Detecting Token Duplication
When running Python or sed replacements, the token can get **duplicated** in the file
(concatenated twice). Check:
```bash
# Count occurrences in the file
grep -o 'TELEGRAM_BOT_TOKEN=' file.env | wc -l  # should be 1

# Or check length
xxd file.env | grep BOT_TOKEN | wc -c  # should be ~64 chars (not ~100+)
```
