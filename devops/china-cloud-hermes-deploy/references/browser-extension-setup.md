# hermes-browser-extension — Session Notes

## Overview

Community browser extension by Jon Komet (GitHub: abundantbeing/hermes-browser-extension, v0.1.7, MIT).
Chrome/Edge side panel that connects to Hermes Gateway API server at port 8642.

Not on Chrome Web Store — must be built from source and loaded as unpacked extension.

## Build & Install

```bash
git clone https://github.com/abundantbeing/hermes-browser-extension.git
cd hermes-browser-extension
npm install
npm run build          # produdes dist/
```

In Chrome: chrome://extensions -> Developer mode -> Load unpacked -> select dist/

## Gateway API Server Config

Added to ~/.hermes/.env:

```
API_SERVER_ENABLED=true
API_SERVER_HOST=127.0.0.1
API_SERVER_PORT=8642
API_SERVER_KEY=xia-chong-bridge-2026
API_SERVER_CORS_ORIGINS=chrome-extension://EXTENSION_ID
```

Verify:
```bash
curl http://127.0.0.1:8642/health
curl -H "Authorization: Bearer <key>" http://127.0.0.1:8642/v1/models
```

## cua-driver Interaction (for Browser Automation)

cua-driver v0.5.1 was installed and running on Mac (daemon PID 24220).
Permissions: accessibility=true, screen_recording=true, screen_recording_capturable=true.
Daemon socket: ~/Library/Caches/cua-driver/cua-driver.sock

### Known Quirks (macOS Chrome)

- `computer_use` tool (Hermes wrapper) captures 1568x980 but SOM mode returns only 2 AXWindow elements on Chrome pages — the accessibility tree from cua-driver is sparse on rendered web content.
- `get_window_state` with window_id on Chrome times out (15s+) for pages with complex DOM.
- `query_dom` via `cua-driver call page` returns macOS menu bar items (system AX), not web page DOM. To access web page content, JS injection is needed but blocked by "JavaScript from Apple Events is disabled" security restriction.
- `zoom` via cua-driver works for screenshots (PNG base64 in `screenshot_png_b64` field).
- `click` via cua-driver can post click events to Chrome PID even when window is backgrounded.
- `list_windows` shows Chrome window with PID and window_id even when `is_on_screen=False`.

### Chrome Window Detection

To find the AI Shell Chrome window:
```bash
echo '{}' | cua-driver call list_windows 2>&1 | python3 -c "
import json,sys
data = json.load(sys.stdin)
for w in data.get('windows', []):
    if w.get('app_name') == 'Google Chrome':
        b = w['bounds']
        if b['width'] > 100 and b['height'] > 100:
            print(f'wid={w[\"window_id\"]} title=\"{w[\"title\"]}\" bounds=({b[\"x\"]},{b[\"y\"]},{b[\"width\"]}x{b[\"height\"]})')
"
```

## Use Case: AI Shell Container

The extension lets Hermes see the AI Shell terminal page content through the side panel.
Combined with `computer_use` for desktop-level clicking, this is an alternative to Tampermonkey for keepalive: the agent can see the extension button and click it.

## Chrome Window State Issue

This session found that Chrome windows all showed `is_on_screen=False` in `list_windows` even though the display was active. The `on_screen` flag flips to `True` when the page is explicitly navigated to. If captures return 0x0, try navigating Chrome explicitly:

```bash
open -a "Google Chrome" "chrome://extensions/"
```
