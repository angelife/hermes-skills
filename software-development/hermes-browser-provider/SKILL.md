---
name: hermes-browser-provider
description: >-
  Hermes 浏览器执行抽象层 — 三层接口（BrowserProvider / ChallengeHandler / HumanAssist）
  支持 CDP / Playwright / OpenBridge 后端，内置 CAPTCHA 状态机、检查点回滚和人工介入兜底。
  所有决策通过 ChatGPT 详细提问后自动化执行。
category: software-development
version: 1.2
---

# Hermes Browser Provider

## Architecture

```
BrowserProvider      — navigate / click / input / screenshot / find_images
ChallengeHandler     — detect / solve / escalate (captcha, login, block)
HumanAssist          — request / wait / resume (manual override)
Checkpointer         — save/restore page state (rollback on bad state)
ImageProvider        — Gemini Web → Pillow placeholder
```

## Provider Selection

```python
from provider.cdp_provider import create_provider

p = create_provider("smart")       # Playwright(stealth) → CDP auto fallback
p = create_provider("cdp")         # attach existing Chrome (port 9222)
p = create_provider("playwright")  # persistent profile + stealth patches
```

## OpenBridge (Chrome Extension Bridge)

**Repo:** `github.com/60ke/openBridge`
**Architecture:** Chrome extension + Node.js daemon + REST API at port 10088
**Key advantage:** Undetectable by websites (real Chrome, no CDP automation markers)

### Install

```bash
git clone https://github.com/60ke/openBridge.git ~/.openbridge/repo
cd ~/.openbridge/repo
pnpm install
pnpm build
node packages/daemon/dist/cli/index.js start
```

Load the Chrome extension from `packages/extension/.output/chrome-mv3`:
1. Open `chrome://extensions`
2. Enable Developer Mode
3. Load unpacked → select the output directory

### Usage

```bash
# ask-openbridge.js — send prompt to Gemini via OpenBridge API
cd ~/.hermes/skills/web-ai-cdp-bridge/scripts
node ask-openbridge.js "your prompt"

# Daemon management
cd ~/.openbridge/repo
node packages/daemon/dist/cli/index.js {status|stop|restart|logs --follow}
```

### API Commands

```
browser_list_tabs, browser_select_tab, browser_new_tab
browser_navigate, browser_snapshot, browser_screenshot
browser_type, browser_fill, browser_send_keys, browser_click
browser_evaluate (disabled by default — enable in extension popup)
```

**NOT_PAIRED error:** Chrome extension not connected. Reopen Chrome and reload extension.

## ChatGPT-First Decision Loop

**User constraint:** All decisions, confusion, and blockers must go through ChatGPT first.

### Asking ChatGPT (corrected by user)

1. **Be very specific** — include exact code, logs, file paths, what was tried and why it failed
2. **Advance the conversation** — don't send the same question twice; build on the response
3. **One decision per query** — present options with tradeoffs, let ChatGPT pick
4. **Full context** — error message, code snippet, environment details

✅ Good: `"A completed. B's detect_challenge covers 6 patterns but auto_solve returns False. Should I implement Cloudflare checkbox click first, or improve detection first? Here's the current code: [...]"`

❌ Bad: `"下一步？回复：B或A"`

### CDP → ChatGPT WebSocket Tips

**Textarea input (React-controlled):**
```js
var ta = document.querySelector('textarea');
var s = Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype, 'value').set;
s.call(ta, text);
ta.dispatchEvent(new Event('input', {bubbles: true}));
```

**Send on Mac ChatGPT:** Cmd+Enter (modifiers=8), NOT plain Enter. Or click `[data-testid="send-button"]`.

**Avoid async IIFE:** `Runtime.evaluate` + `returnByValue: true` cannot serialize async function returns. Use sync functions only.

**New chat loads history:** `/?new` restores conversation from localStorage. To truly start fresh, navigate to main page and verify textarea exists with `msgs=0`.

## File Structure

```
provider/
  __init__.py              # package marker
  interface.py             # BrowserProvider / ChallengeHandler / HumanAssist ABCs
  cdp_provider.py          # CDP backend + create_provider factory
  playwright_provider.py   # PlaywrightProvider + LoginAwareProvider (auto-fallback)
  challenge.py             # CAPTCHA state machine + detect_challenge (6 patterns)
  human_assist.py          # ConsoleHumanAssist / TelegramHumanAssist
  image_provider.py        # Image generation: Gemini Web → Pillow(placeholder). NO FAL.
  checkpoint.py            # Browser page state save/restore (rollback on CAPTCHA/block)

scripts/
  ask.js                   # CDP bridge to Web AI (gemini/chatgpt/claude/perplexity)
  ask-openbridge.js        # OpenBridge bridge to Gemini (no CAPTCHA)
  playwright-browser.js    # Persistent-context browser with stealth
  capture-image.js         # Extract image from page via CDP
  browser-login.py         # Bootstrap login for Playwright profile
  adapters/
    gemini.js              # detectChallengeFn, isDoneFn, text-evolution, extractFn
    chatgpt.js             # isDoneFn, countTurnsFn, threshold=1
    claude.js, perplexity.js # (unused)
  core/
    reader.js              # isDoneFn support, detectChallengeFn, text-evolution fallback
    composer.js            # type/paste text input
    browser.js             # CDP connection
```

## Workflows

### Ask Gemini (auto-fallback: Playwright → CDP → OpenBridge)

```bash
# Old CDP bridge (may trigger CAPTCHA):
node ask.js gemini "prompt"

# New OpenBridge (no CAPTCHA, uses real Chrome):
node ask-openbridge.js "prompt"
```

### CAPTCHA Handling

```python
from provider.challenge import ChallengeStateMachine, detect_challenge
sm = ChallengeStateMachine()
ch = detect_challenge(page_state)
if ch.detected:
    session = sm.detect(page_state, ch)
    await sm.request_human(session)
```

detect_challenge recognizes 6 patterns (scored by URL + text match + severity bonus):
- recaptcha, turnstile (Cloudflare), hcaptcha, login_required, blocked, session_expired

### Checkpoint/Rollback — CDP操作后悔药

```python
from provider.checkpoint import Checkpointer
cp = Checkpointer(page)
await cp.save("before-send")
# ... risky browser op ...
bad, reason = await cp.is_bad_state()
if bad: await cp.restore()
```

Bad state detection: page title ("Just a moment..."), URL (accounts.google.com, login), text ("unusual traffic", "异常流量").

### Image Generation (no FAL — costs money)

```python
from provider.image_provider import ImageProvider
p = ImageProvider()
result = await p.generate("prompt", "landscape", slug="my-post")
```

Fallback chain: Gemini Web (CDP/OpenBridge) → Pillow placeholder.

**⚠️ FAL.ai has no free tier.** Pay-per-use ($0.02-0.04/image). Never install FAL_KEY without explicit user approval. User rejected this.

## Key Technical Decisions

1. **Three-layer interface** — split BrowserProvider / ChallengeHandler / HumanAssist instead of one giant ABC
2. **smart provider default** — auto fallback Playwright → CDP based on login status file
3. **Node.js subprocess** — avoid Python playwright (not installed), reuse existing Node.js playwright-core
4. **isDoneFn threshold = 1** — ChatGPT often replies single letters ("A", "B", "C") for direction; threshold must be 1
5. **Text-evolution fallback** — Gemini merges responses into one block, turn count doesn't increment; reader falls back to body text length change
6. **No FAL** — user confirmed: paid service, don't use

## Known Issues

- CDP bridge (ask.js) triggers Cloudflare/CAPTCHA frequently
- OpenBridge extension disconnects when Chrome closes
- ChatGPT CDP bridge has stability issues (Cloudflare, deep-think hang)
- Playwright profile needs one-time Gemini login
- ChatLab CLI install needs CXXFLAGS on macOS: `export CXXFLAGS="-isysroot $(xcrun --show-sdk-path)"` before `npm install -g chatlab-cli` (better-sqlite3 fails without it)
