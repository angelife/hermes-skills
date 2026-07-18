# MCP Wrapper Pattern — OpenBridge → AI Web

Wrap any OpenBridge-backed Web AI (Gemini, ChatGPT, Claude, etc.) as a Hermes MCP Server, so tools appear natively in every session.

## Architecture

```
Hermes Agent → MCP Client (stdio) → Python MCP Server → OpenBridge (port 10088) → Chrome CDP → Web AI
```

- MCP Server runs as a subprocess managed by Hermes's native MCP client
- Talks to OpenBridge daemon via `httpx` POST to `http://127.0.0.1:10088/command`
- No API key needed — reuses Chrome's existing login session

## Reference Implementation

`~/.hermes/mcp-servers/gemini-web-mcp/main.py` — wraps gemini.google.com. ~280 lines.

### Key components

```python
# MCP server struct
server = Server("gemini-web-mcp")

@server.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="ask_gemini",
            description="Send a prompt to Gemini Web via OpenBridge",
            inputSchema={
                "type": "object",
                "properties": {
                    "prompt": {"type": "string", "description": "The prompt"}
                },
                "required": ["prompt"]
            }
        )
    ]

@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    # 1. Open/find tab → navigate to web AI URL
    # 2. Click "New chat" to start fresh (critical — see pitfalls)
    # 3. Type prompt → submit
    # 4. Wait for response via snapshot polling
    # 5. Extract text, return
```

### OpenBridge API calls (via httpx)

| Action | Payload |
|--------|---------|
| List tabs | `{"toolName": "browser_list_tabs", "args": {}}` |
| New tab | `{"toolName": "browser_new_tab", "args": {"url": "https://gemini.google.com"}}` |
| Select tab | `{"toolName": "browser_select_tab", "args": {"tabId": 12345}}` |
| Type text | `{"toolName": "browser_type", "args": {"ref": "@e3", "text": "..."}}` |
| Send keys | `{"toolName": "browser_send_keys", "args": {"keys": "Enter"}}` |
| Snapshot | `{"toolName": "browser_snapshot", "args": {}}` |
| Click ref | `{"toolName": "browser_click_ref", "args": {"ref": "@e8"}}` |
| Navigate | `{"toolName": "browser_navigate", "args": {"url": "https://..."}}` |

## Setup

```bash
# Create venv with MCP SDK
cd ~/.hermes/mcp-servers/<name>
python3 -m venv .venv
.venv/bin/pip install mcp httpx

# Add to Hermes config (preferred method — writes correct YAML)
hermes mcp add <name> \
  --command "$PWD/.venv/bin/python3" \
  --args "$PWD/main.py"
```

## Critical Pitfalls

### 1. `tabId` is an integer from OpenBridge API

The `browser_list_tabs` and `browser_new_tab` endpoints return `tabId` as a JSON **number** (e.g., `1629829812`), NOT a string.

```python
# WRONG — crashes with type error
ob_call("browser_select_tab", {"tabId": str(tab_id)})

# CORRECT — pass native int to OpenBridge
ob_call("browser_select_tab", {"tabId": tab_id})

# For display, convert to str
details = f"Tab: {'open (' + str(tab_id) + ')' if tab_id else 'not open'}"
```

**All `ob_call` points** that receive `tab_id` as a parameter MUST pass the native int. `str(tab_id)` corrupts the OpenBridge RPC call.

### 2. Web AI loads the last conversation (not fresh)

Opening a URL like `https://gemini.google.com/app` loads the most recent conversation. The SPA redirects to `/app/<conversation_uuid>`. This means:
- Old response text is visible in the DOM
- Response detection triggers on stale content
- The new prompt gets appended to an existing conversation

**Fix:** After opening the tab, look for and click the "New chat" button before typing.

```python
def click_new_chat() -> bool:
    """Find and click 'New chat' button in the Web AI UI."""
    snap = ob_call("browser_snapshot")
    nodes = (snap.get("data") or {}).get("nodes") or []
    for n in nodes:
        name = n.get("name", "")
        role = n.get("role", "")
        ref_id = n.get("ref")
        if role == "button" and name in ("New chat", "新建对话", "+ New chat"):
            if ref_id:
                result = ob_call("browser_click_ref", {"ref": ref_id})
                return result.get("status") != "error"
    return False
```

The button names to try: `"New chat"` (English), `"新建对话"` (Chinese), `"+ New chat"`.

### 3. Response detection via turn counting

Since old responses are in the DOM, detecting "new response" requires comparing the number of turns before and after submission. For Gemini, count "Gemini 说" occurrences in `document.body.innerText`. For ChatGPT/Claude, use their respective role indicators.

Without `click_new_chat()`, old turn markers cause premature response detection.

### 4. MCP server has no hot-reload

The MCP server process is spawned at session start and kept alive for the session duration.

- `hermes mcp test <name>` spawns a fresh subprocess (for testing code changes) but does NOT update the live session
- The live MCP server process only picks up code changes on **session restart**
- To verify changes: run `hermes mcp test`, then restart session

Architectural note: The MCP server runs in-child (stdin/stdout) within the Hermes agent process. There is no standalone PID to kill and restart.

### 5. Accessibility tree snapshot format

`browser_snapshot` returns a list of `nodes[]`, each with:
- `name` — accessible name of the element
- `role` — ARIA role (button, textbox, StaticText, etc.)
- `ref` — reference ID for subsequent `browser_click_ref` calls

The snapshot does NOT expose CSS selectors. All element interactions go through `ref` IDs.

Finding the input field: search for `textbox` or `searchbox` roles with `editable=true` or `focused=true`.

### 6. Chinese text input

When the OpenBridge daemon types into a contenteditable field via `browser_type`, CJK characters are handled automatically. No manual `insertText` handling needed (unlike the old Playwright CDP bridge).

### 7. `browser_type` only types, does NOT submit

Regardless of trailing newlines, `browser_type` only types characters. Must call `browser_keypress` or `browser_send_keys` with `Enter` to submit.

### 8. Response timeout

The `wait_for_response` loop typically polls every 0.5-1 seconds for up to 180 seconds. Each cycle:
1. Get `browser_snapshot`
2. Extract text from `StaticText` nodes (filter: `len > 5`)
3. Check for response indicator markers
4. Check stability: 3 consecutive identical samples
5. If stable indicator present → return

For long responses (code blocks, multi-paragraph), expect 30-60 seconds.

## Translation Layer: Python JSON → OpenBridge

The `ob_call()` helper serializes args to JSON, POSTs to `http://127.0.0.1:10088/command`, and parses the response. Standard structure:

```python
import httpx

def ob_call(tool_name: str, args: dict = None) -> dict:
    try:
        resp = httpx.post(
            "http://127.0.0.1:10088/command",
            json={"toolName": tool_name, "args": args or {}},
            timeout=30.0
        )
        return resp.json()
    except Exception as e:
        return {"status": "error", "error": str(e)}
```

The MCP server's `call_tool` handler wraps this in `async` via `asyncio.to_thread()` since httpx calls are synchronous.

## Pitfalls (original, still valid)

- **`InitializationOptions` requires `capabilities`** — MCP SDK `>=1.0` validates all fields. Pass `capabilities=server.get_capabilities(notification_options=NotificationOptions(), experimental_capabilities={})` explicitly.
- **`hermes config set mcp_servers` stores JSON as string** — YAML parser returns a `str`, Hermes' `isinstance(mcp_servers, dict)` check silently fails. Use `hermes mcp add` instead.
- **`hermes mcp add` rewrites server config on each call** — it discards extra fields (e.g. `timeout`, `connect_timeout`). Re-add those manually after if needed.
- **Tools only in new sessions** — `hermes mcp add` discovers tools successfully but they don't inject into the current conversation. Start a new session to use them.
- **OpenBridge daemon must be running** — verify: `curl -s http://127.0.0.1:10088/command -X POST -H 'Content-Type: application/json' -d '{"toolName":"browser_list_tabs","args":{}}'`
- **Chrome must be alive with Gemini logged in** — if Chrome crashes or session expires, tools fail silently.
