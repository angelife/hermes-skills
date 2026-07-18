# CDP WebSocket: Native Textarea Value Injection Pattern

ChatGPT uses React-controlled textarea. Setting `.innerText` or `.value` directly on `#prompt-textarea` (a DIV) does NOT trigger React's state update — the value appears visually but the app doesn't "see" it.

## The Fix: Native Value Setter

```js
// 1. Get the REAL textarea (not the div#prompt-textarea)
const ta = document.querySelector('textarea');

// 2. Use the native HTMLTextAreaElement value setter (bypasses React's override)
const setter = Object.getOwnPropertyDescriptor(
  window.HTMLTextAreaElement.prototype, 'value'
).set;

// 3. Call it with the text
setter.call(ta, 'your text here');

// 4. Dispatch input event so React picks up the change
ta.dispatchEvent(new Event('input', { bubbles: true }));
```

## Sending: Button Click > Enter Key

In ChatGPT Web:
- **Plain Enter** adds a newline (does NOT send)
- **Ctrl+Enter / Cmd+Enter** is unreliable via JS
- **Clicking the send button** works consistently

```js
// Wait for send button to appear (it's hidden until text is detected)
await new Promise(r => setTimeout(r, 1500));

const btn = document.querySelector('[data-testid="send-button"]');
if (btn && btn.offsetParent !== null) {
  btn.click();
}
```

## Complete Send Pipeline

```python
import json, urllib.request, asyncio, websockets

async def send_to_chatgpt(ws_url, text, wait_response=120):
    async with websockets.connect(ws_url) as ws:
        await ws.send(json.dumps({"id":1,"method":"Runtime.enable"}))
        # wait for enable ack
        while json.loads(await ws.recv()).get('id') != 1: pass

        # Set text via native setter
        await ws.send(json.dumps({"id":2,"method":"Runtime.evaluate","params":{
            "expression": f"""
                var ta = document.querySelector('textarea');
                var s = Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype,'value').set;
                s.call(ta, {json.dumps(text)});
                ta.dispatchEvent(new Event('input', {{bubbles:true}}));
            """,
            "returnByValue": True
        }}))
        while json.loads(await ws.recv()).get('id') != 2: pass

        await asyncio.sleep(2)

        # Click send button
        await ws.send(json.dumps({"id":3,"method":"Runtime.evaluate","params":{
            "expression": """
                var b = document.querySelector('[data-testid="send-button"]');
                if(b && b.offsetParent !== null) { b.click(); }
            """,
            "returnByValue": True
        }}))
```

## Detecting Response Completion

ChatGPT creates an empty assistant element immediately, then fills it after deep-think.
Use `isDoneFn` pattern (see `references/chatgpt-adapter-debug.md`):

```js
var a = document.querySelectorAll('[data-message-author-role="assistant"]');
var l = a[a.length-1];
var text = (l.innerText || '').trim();
var thinking = !!l.querySelector('.result-thinking');
var done = text.length > 20 && !thinking;
```

## Common Failures

1. **Setting innerText on div#prompt-textarea** → visually appears but React doesn't register it → send button never appears
2. **Pressing Enter** → adds newline, doesn't send
3. **Clicking the microphone/voice button** → wrong button at bottom of page, no effect
4. **Async IIFE with returnByValue** → Promise can't be serialized → `KeyError: 'value'`. Use sync functions only.
