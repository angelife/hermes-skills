# OpenBridge — Chrome Extension Browser Bridge (CDP Alternative)

Repo: [github.com/60ke/openBridge](https://github.com/60ke/openBridge) (42 commits, 8 stars)
Architecture: Local daemon + Chrome extension + local HTTP API

## Why OpenBridge Over CDP

| Factor | CDP Bridge | OpenBridge |
|--------|-----------|------------|
| Detection | CDP attach easily detected | Chrome extension, invisible |
| Login state | Separate profile needs manual login | Uses user's real Chrome tabs |
| Stealth | None, triggers CAPTCHA | Extension = real browser |
| Tab management | One page at a time | Full tab CRUD |
| API | Roll-your-own JSON | REST API + MCP stdio |
| Integration | Custom ask.js | Standard MCP protocol |

## Install

```bash
# 1. Install daemon (requires pnpm)
git clone https://github.com/60ke/openBridge.git ~/.openbridge/repo
cd ~/.openbridge/repo

# pnpm v11+ requires explicit build approval
# Edit pnpm-workspace.yaml:
#   allowBuilds:
#     esbuild: true
#     spawn-sync: true

pnpm install
pnpm build

# 2. Start daemon
node packages/daemon/dist/cli/index.js start --api-port 10088

# 3. Load Chrome extension
# Open chrome://extensions → Developer mode → Load unpacked
# Select: ~/.openbridge/repo/packages/extension/.output/chrome-mv3
```

## Install (quick script)

```bash
curl -fsSL https://raw.githubusercontent.com/60ke/openBridge/master/install.sh | bash
```

## Verify

```bash
node ~/.openbridge/repo/packages/daemon/dist/cli/index.js status
# Expected: Daemon Running, Extension Connected (1), Pairing Paired

# List all Chrome tabs
curl -s -X POST http://127.0.0.1:10088/command \
  -H 'Content-Type: application/json' \
  -d '{"toolName":"browser_list_tabs","args":{}}'
```

## ask-openbridge.js — Unified CLI

Located at `~/.hermes/skills/web-ai-cdp-bridge/scripts/ask-openbridge.js`

Replaces `ask.js` for Gemini interaction. No CDP needed — uses OpenBridge API directly.

```bash
node ask-openbridge.js "your prompt"
# Finds Gemini tab → types → sends → reads response → prints to stdout
```

Flow:
1. `browser_list_tabs` → find Gemini tab (URL contains `gemini.google.com/app`, not `glic`)
2. If no tab found, `browser_new_tab` + `browser_navigate` to Gemini
3. `browser_snapshot` → find composer ref (editable textbox named "问问 Gemini" or "为 Gemini 输入提示")
4. `browser_type(ref, text)` → type prompt
5. `browser_send_keys({"keys":"Enter"})` → send
6. Poll `browser_snapshot` every 3s → split on "Gemini 说" → last section = response
7. Return response when stable for 3 samples or 15s elapsed

Environment: `OPENBRIDGE_PORT` (default 10088).

## Commands

```bash
# Tab operations
browser_new_tab, browser_select_tab, browser_list_tabs, browser_close_tab
browser_navigate, browser_snapshot, browser_screenshot

# Interaction
browser_click, browser_mouse_click, browser_fill, browser_type
browser_key_type, browser_send_keys

# Advanced
browser_evaluate (disabled by default, enable in extension popup)
browser_network, browser_upload, browser_save_as_pdf
```

## Gemini Interaction Flow

1. `browser_list_tabs` → find existing Gemini tab ID
2. `browser_select_tab` → switch to Gemini
3. `browser_snapshot` → get accessibility tree, find composer ref (editable textbox)
4. `browser_type(ref, text)` → type prompt into composer
5. `browser_send_keys({"keys":"Enter"})` → send (Gemini uses Enter)
6. Wait 5-15s for Gemini to respond
7. `browser_snapshot` → read response text from StaticText nodes

## Pitfalls

- **`browser_fill`** uses CSS selector, NOT ref. Use `browser_type(ref, text)` for ref-based input.
- **`browser_evaluate`** disabled by default. Enable in extension popup if needed.
- **Proxy**: New tabs opened via OpenBridge may not inherit Chrome's proxy settings. Use existing tabs when possible.
- **Navigation timeout**: Default ~15s. Retry if page doesn't load (especially Gemini).
- **Screenshot path**: Not returned in API response directly — check daemon log file.
- **npm install fails**: `@openbridge-org/daemon` has pnpm workspace protocol references. Use the install script instead.
- **NOT_PAIRED**: Chrome closed or extension reloaded. Re-open Chrome and check chrome://extensions.

## Daemon Management

```bash
cd ~/.openbridge/repo
node packages/daemon/dist/cli/index.js start
node packages/daemon/dist/cli/index.js stop
node packages/daemon/dist/cli/index.js status
node packages/daemon/dist/cli/index.js restart
node packages/daemon/dist/cli/index.js logs --follow
node packages/daemon/dist/cli/index.js mcp     # MCP stdio mode
```
