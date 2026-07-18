# Browser Provider Architecture — Session Notes

## Session Context

Session date: 2026-07-10
Trigger: Gemini Web CAPTCHA blocking CDP bridge for AI image generation

## Problem

Hermes Agent uses Chrome CDP (port 9222) + Playwright to interact with `gemini.google.com` for free Imagen image generation. Google's anti-bot detection (reCAPTCHA / Sorry Page) frequently blocks the bridge because:

1. CDP attach exposes automation signals (`navigator.webdriver`, TLS fingerprint)
2. Proxy exit IP has low reputation (datacenter IP)
3. No automated CAPTCHA solving

## Research: BrowserAct

GitHub: `browser-act/skills` — 4.3k stars
Three-layer anti-detection: stealth fingerprint, auto-captcha-solve, remote-human-assist

**Installation blocked**: macOS x86_64 has no wheel (only `macosx_11_0_arm64` available)

## ChatGPT Architectural Review

ChatGPT evaluated the analysis document and concluded:

### Key Findings

1. **BrowserAct is overestimated** — it's a browser infrastructure enhancer, not a CAPTCHA solver
2. **undetected-chromedriver is wrong direction** — it's Selenium ecosystem, switching means rewriting all interaction logic
3. **Best path**: Browser Provider abstraction layer first, then Playwright stealth patches

### Recommended Priority

1. D: Standardize manual CAPTCHA fallback (★★★★★)
2. A: Playwright persistent context + stealth (★★★★☆)
3. C: Gemini API as long-term fallback (★★★★☆)
4. B: undetected-chromedriver (★)

### Architecture Decision

```
Problem is NOT "find stronger browser tool"
Problem IS "Hermes lacks browser execution abstraction"
```

## Implementation

### Files Created

- `provider/interface.py` — Three-layer abstract interface + data classes
- `provider/cdp_provider.py` — CDP backend wrapping existing Node.js scripts
- `provider/challenge.py` — CAPTCHA state machine
- `provider/human_assist.py` — ConsoleHumanAssist / TelegramHumanAssist

### State Machine Flow

```
DETECTED → AUTO_SOLVING → [ok → RESOLVED]
                          ↘ [fail → HUMAN_REQUESTED → HUMAN_WAITING → RESOLVED]
                                                                      ↘ TIMEOUT
```

### Verification

All interfaces pass Python validation test. CDPProvider wraps existing ask.js and capture-image.js with zero destructive changes.

## Lessons Learned

- Stealth ≠ CAPTCHA disappearance. Google risk assessment combines IP reputation, account history, cookies, behavior patterns, TLS/network characteristics, geographic consistency.
- Playwright persistent context with real Chrome profile is more effective than pure stealth patches.
- HumanAssist state machine is the highest ROI improvement — makes the system resilient when CAPTCHA appears instead of deadlocking.
