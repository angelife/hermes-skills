# ChatGPT Web Adapter Debugging

## Problem: isDoneFn needed for Deep-Think Mode

ChatGPT creates an empty `[data-message-author-role="assistant"]` element **immediately** when you send a message, then fills it after deep-think completes. Without `isDoneFn`, the reader sees "new turn detected" instantly, extracts empty body text, and returns garbage.

**Fix (in adapter) — threshold progression 20→5→1:**
```js
isDoneFn: function() {
  var a = document.querySelectorAll('[data-message-author-role="assistant"]');
  if (!a.length) return false;
  var l = a[a.length-1];
  var t = (l.innerText || '').trim();
  if (t.length < 1) return false;                          // any content is valid (even "C")
  if (l.querySelector('.result-thinking')) return false;     // still deep-thinking
  var btns = document.querySelectorAll('button');
  for (var i = 0; i < btns.length; i++) {
    var txt = (btns[i].getAttribute('aria-label') || btns[i].textContent || '').toLowerCase();
    if (txt.includes('stop') || txt.includes('停止') || txt.includes('generat')) return false;
  }
  return true;
}
```

**Fix (in reader.js — `waitForResponse`):**
```js
// After hasNewTurn = true, before extractText:
if (config.isDoneFn) {
  var done = await page.evaluate(config.isDoneFn).catch(function(){return false;});
  if (!done) { stableCount = 0; lastText = ''; continue; }
}
```

## Problem: Async IIFE + returnByValue = Exception

`Runtime.evaluate` with `returnByValue: true` cannot serialize a Promise. An async IIFE returns a Promise, which produces `result.exceptionDetails` instead of `result.result.value` → `KeyError: 'value'`.

**Wrong:**
```js
(async function() { ... })()  // returns Promise → can't serialize
```

**Right — single-step synchronous:**
```js
(function() {
  var ta = document.querySelector('textarea');
  var s = Object.getOwnPropertyDescriptor(...).set;
  s.call(ta, text);
  ta.dispatchEvent(new Event('input', {bubbles: true}));
  return 'done';
})()
```

For multi-step operations (set text → wait → click), split into separate `Runtime.evaluate` calls with `asyncio.sleep` between them.

## Cloudflare Blocking

ChatGPT's `[data-message-author-role="assistant"]` only matches assistant messages. The `countTurns()` logic needs total message count (user + assistant) to detect "new turn appeared."

**Wrong:**
```js
turnSelector: '[data-message-author-role="assistant"]'  // counts only assistant → always off by half
```

**Right:**
```js
countTurnsFn: function() {
  return document.querySelectorAll('[data-message-author-role]').length;
}
```

## Problem: responseSelector fails on new ChatGPT DOM

ChatGPT wraps responses in nested divs with class `.result-thinking`, `.markdown`, etc. CSS selectors break frequently.

**Fix:** Set `responseSelector: null` so reader.js falls back to `document.body.innerText`.

## Debugging ChatGPT Page State

When adapter times out or returns empty:

1. Check message count:
   ```js
   document.querySelectorAll('[data-message-author-role]').length
   ```

2. Check input area:
   ```js
   const ta = document.querySelector('#prompt-textarea');
   ta?.innerText || 'no textarea';
   ```

3. Check send button:
   ```js
   document.querySelector('[data-testid="send-button"]')?.textContent
   ```

4. Check if deep thinking is active:
   ```js
   !!document.querySelector('.result-thinking')  // true = still thinking
   ```

5. Check for stop button (generation complete):
   ```js
   !!document.querySelector('[data-testid*="stop"], [aria-label*="Stop"]')
   ```

## Cloudflare Blocking

When navigating to chatgpt.com via CDP, you may see "Just a moment..." — this is Cloudflare bot detection. The CDP bridge cannot bypass this automatically. Workaround: use the existing logged-in Chrome session via CDP attach.
