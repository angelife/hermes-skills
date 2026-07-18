# CDP WebSocket Runtime.evaluate: Async IIFE Trap

## The Problem

`Runtime.evaluate` with `returnByValue: true` **cannot serialize Promise return values**.
An async IIFE returns a Promise, which the CDP protocol cannot convert to a JSON value.

```javascript
// ❌ Returns {} — the async Promise can't be serialized
(async function() {
  const ta = document.querySelector('textarea');
  const s = Object.getOwnPropertyDescriptor(...);
  s.call(ta, text);
  ta.dispatchEvent(new Event('input', {bubbles: true}));
  return 'done';
})()
```

## The Fix

Use **synchronous functions only** for `returnByValue` evaluations.
If you need async (e.g. `await`), use `returnByValue: false` and read the result differently,
or make the function synchronous:

```javascript
// ✅ Returns 'done' — sync IIFE
(function() {
  const ta = document.querySelector('textarea');
  const s = Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype, 'value').set;
  s.call(ta, text);
  ta.dispatchEvent(new Event('input', {bubbles: true}));
  return 'done';
})()
```

## Detection

If your `Runtime.evaluate` response contains `"result": { ... }` but no `"result": { "value": ... }`,
it likely means the expression returned a Promise (async) that couldn't be serialized.

## Exception Handling

When the evaluate result has `exceptionDetails` instead of `result.value`, catch it:

```python
m = json.loads(await ws.recv())
r = m.get('result', {})
if 'exceptionDetails' in r:
    print(f"EXCEPTION: {r['exceptionDetails']['text']}")
    return None
return r.get('result', {}).get('value')
```
