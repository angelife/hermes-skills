# OpenBridge — Chrome Extension Browser Bridge

**Repo**: `github.com/60ke/openBridge` (42 commits, 8 stars, MIT)
**Architecture**: Chrome extension + local daemon + MCP/stdio API
**Ports**: daemon 10087 (WS), local API 10088 (HTTP)

## Why It Matters

Unlike our CDP bridge (`ask.js` + Playwright), OpenBridge uses a Chrome EXTENSION.
Extensions are NOT detectable as automation — `navigator.webdriver` stays false,
no CDP flags, no remote-debugging port. This fundamentally changes the
CAPTCHA/Cloudflare equation.

## Architecture

```
AI client / MCP client / Codex skill
        |
        | stdio MCP or local HTTP API
        v
OpenBridge daemon (loopback only)
        |
        | ws://127.0.0.1:10087/bridge
        v
OpenBridge Chrome extension
        |
        v
User's real Chrome tabs (with login cookies)
```

## Install (Intel Mac)

```bash
# 1. Get the source
git clone https://github.com/60ke/openBridge.git ~/.openbridge/repo
cd ~/.openbridge/repo

# 2. Fix pnpm approve-builds (stuck on interactive prompt)
echo -e "allowBuilds:\n  esbuild: true\n  spawn-sync: true" > pnpm-workspace.yaml

# 3. Build
pnpm install && pnpm build

# 4. Start daemon
node packages/daemon/dist/cli/index.js start

# 5. Load Chrome extension
# Open chrome://extensions → Developer mode → Load unpacked
# Select ~/.openbridge/repo/packages/extension/.output/chrome-mv3
```

## Usage (after daemon + extension connected)

```bash
# Health check
curl -s http://127.0.0.1:10088/health

# List tabs
curl -s -X POST http://127.0.0.1:10088/command \
  -H 'Content-Type: application/json' \
  -d '{"toolName":"browser_list_tabs","args":{}}'

# Navigate
curl -s -X POST http://127.0.0.1:10088/command \
  -H 'Content-Type: application/json' \
  -d '{"toolName":"browser_navigate","args":{"url":"https://gemini.google.com/app"}}'

# Snapshot (get page state with refs)
curl -s -X POST http://127.0.0.1:10088/command \
  -H 'Content-Type: application/json' \
  -d '{"toolName":"browser_snapshot","args":{}}'
```

## Tools Available

browser_list_tabs, browser_new_tab, browser_select_tab, browser_navigate,
browser_snapshot, browser_click, browser_mouse_click, browser_fill,
browser_type, browser_key_type, browser_send_keys, browser_screenshot,
browser_evaluate, browser_close_tab, browser_close_session,
browser_find_tab, browser_upload, browser_save_as_pdf, browser_network

## Why Not Replacement (yet)

- Extension must be loaded manually (Chrome Web Store or unpacked)
- `pnpm build` requires pnpm v11+ and occasional approve-builds fix
- Not fully battle-tested for our Gemini/ChatGPT workflows
- But the ARCHITECTURE is superior — worth tracking and testing against
