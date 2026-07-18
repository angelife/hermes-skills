---
name: macos-native-apps
description: "Automate macOS native apps — Notes, Reminders, Find My, and iMessage — from the terminal."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [macos]
metadata:
  hermes:
    tags: [macOS, Apple, Notes, Reminders, FindMy, iMessage, automation]
---

# macOS Native Apps

Manage Apple's native macOS apps from the terminal. Each app has its own CLI tool (or AppleScript-based workaround) that provides programmatic access to features that sync across all Apple devices via iCloud.

## When to Use This Umbrella Skill

User asks to interact with any built-in macOS/Apple app: Notes, Reminders, Find My, or iMessage. Pick the relevant section below.

**Related**: `macos-computer-use` for general macOS desktop automation (screenshots, clicks, keyboard).

---

## 1. Apple Notes (`memo` CLI)

Use `memo` to manage Apple Notes via terminal. Notes sync via iCloud.

### Prerequisites

```bash
brew tap antoniorodr/memo && brew install antoniorodr/memo/memo
```

Grant Automation access to Notes.app when prompted (System Settings → Privacy → Automation).

### Quick Reference

```bash
# View notes
memo notes                        # List all notes
memo notes -f "Folder Name"       # Filter by folder
memo notes -s "query"             # Search notes (fuzzy)

# Create notes
memo notes -a                     # Interactive editor
memo notes -a "Note Title"        # Quick add with title

# Edit notes
memo notes -e                     # Interactive selection to edit

# Delete notes
memo notes -d                     # Interactive selection to delete

# Move notes between folders
memo notes -m                     # Interactive

# Export notes
memo notes -ex                    # Export to HTML/Markdown
```

### Limitations
- Cannot edit notes containing images or attachments
- Interactive prompts require terminal access (use `pty=true` if needed)
- macOS only — requires Apple Notes.app

---

## 2. Apple Reminders (`remindctl` CLI)

Use `remindctl` to manage Apple Reminders via terminal. Tasks sync via iCloud.

### Prerequisites

```bash
brew install steipete/tap/remindctl
```

Grant Reminders permission when prompted. Check status: `remindctl status`, request: `remindctl authorize`.

### Quick Reference

```bash
# View reminders
remindctl                    # Today's reminders
remindctl today              # Today
remindctl tomorrow           # Tomorrow
remindctl week               # This week
remindctl overdue            # Past due
remindctl all                # Everything
remindctl 2026-01-04         # Specific date

# Manage lists
remindctl list               # List all lists
remindctl list Work          # Show specific list
remindctl list Projects --create    # Create list
remindctl list Work --delete        # Delete list

# Create reminders
remindctl add "Buy milk"
remindctl add --title "Call mom" --list Personal --due tomorrow
remindctl add --title "Meeting prep" --due "2026-02-15 09:00"

# Due time vs alarm / early nudge
# --due sets the due date/time
# --alarm sets the notification trigger
remindctl add --title "Hairdresser" --due "2026-05-15 14:00" --alarm "2026-05-15 13:30"

# Complete / delete
remindctl complete 1 2 3          # Complete by ID
remindctl delete 4A83 --force     # Delete by ID

# Output formats
remindctl today --json       # JSON for scripting
remindctl today --plain      # TSV format
remindctl today --quiet      # Counts only
```

### Date Formats

`today`, `tomorrow`, `yesterday`, `YYYY-MM-DD`, `YYYY-MM-DD HH:mm`, ISO 8601.

### Rules
- When user says "remind me", clarify: Apple Reminders (syncs to phone) vs agent cronjob alert
- Always confirm reminder content and due date before creating
- Use `--json` for programmatic parsing

---

## 3. Find My (Apple Devices & AirTags)

Track Apple devices and AirTags via the FindMy.app. No CLI exists — uses AppleScript + screen capture.

### Prerequisites

- macOS with Find My app and iCloud signed in
- Screen Recording permission (System Settings → Privacy → Screen Recording)
- **Optional**: `brew install steipete/tap/peekaboo` (better UI automation)

### Method 1: AppleScript + Screenshot (Basic)

```bash
# Open Find My app
osascript -e 'tell application "FindMy" to activate'
sleep 3

# Take a screenshot
screencapture -w -o /tmp/findmy.png

# Analyze with vision
# vision_analyze(image_url="/tmp/findmy.png", question="What devices/items are shown and what are their locations?")
```

### Method 2: Peekaboo (Recommended)

```bash
# Open Find My
osascript -e 'tell application "FindMy" to activate'
sleep 3

# Capture and annotate UI
peekaboo see --app "FindMy" --annotate --path /tmp/findmy-ui.png

# Click a specific element
peekaboo click --on B3 --app "FindMy"

# Capture detail view
peekaboo image --app "FindMy" --path /tmp/findmy-detail.png
```

### Track AirTag Location Over Time

AirTags **only update location while the FindMy page is actively displayed** — keep it in the foreground.

```bash
osascript -e 'tell application "FindMy" to activate'
sleep 3
while true; do
    screencapture -w -o /tmp/findmy-$(date +%H%M%S).png
    sleep 300  # Every 5 minutes
done
```

### Limitations
- No CLI or API — must use UI automation
- Location accuracy depends on FindMy network
- AppleScript may break across macOS versions

---

## 4. iMessage (`imsg` CLI)

Send and receive iMessages/SMS via macOS Messages.app.

### Prerequisites

```bash
brew install steipete/tap/imsg
```

Grant Full Disk Access for terminal (System Settings → Privacy → Full Disk Access). Grant Automation permission for Messages.app when prompted.

### Quick Reference

```bash
# List chats
imsg chats --limit 10 --json

# View history
imsg history --chat-id 1 --limit 20 --json
imsg history --chat-id 1 --limit 20 --attachments --json

# Send messages
imsg send --to "+141****1212" --text "Hello!"
imsg send --to "+141****1212" --text "Check this" --file /path/to/image.jpg
imsg send --to "+141****1212" --text "Hi" --service imessage
imsg send --to "+141****1212" --text "Hi" --service sms

# Watch for new messages
imsg watch --chat-id 1 --attachments
```

### Service Options
- `--service imessage` — Force iMessage
- `--service sms` — Force SMS (green bubble)
- `--service auto` — Let Messages.app decide (default)

### Rules
- **Always confirm recipient and message content** before sending
- **Never send to unknown numbers** without explicit user approval
- **Verify file paths** exist before attaching
- **Don't spam** — rate-limit yourself

---

## Gotchas

- All tools are macOS-only — will not work on Linux/Windows
- System permission prompts (Automation, Accessibility, Screen Recording, Full Disk Access) must be granted interactively the first time
- AppleScript-based tools (FindMy) are fragile across macOS version upgrades
