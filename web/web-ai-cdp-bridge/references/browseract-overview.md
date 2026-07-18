# BrowserAct — Anti-detection Browser Automation

Source: https://github.com/browser-act/skills

Three-layer anti-detection architecture:

1. **Environment layer** — stealth fingerprint spoofing, TLS rotation, proxy switching
2. **Execution layer** — solve-captcha auto-solves CAPTCHAs; stealth-extract pulls protected pages
3. **Human layer** — remote-assist generates live URL for user takeover, agent continues after

## Installation

```bash
uv tool install browser-act-cli --python 3.12
```

Note: wheels only available for macOS arm64, linux_x86_64, windows_amd64. Does NOT support macOS x86_64.

## Key Commands

```bash
browser-act get-skills core --skill-version 2.0.2
browser-act stealth-extract <url>
browser-act --session my-task browser open <id> <url>
browser-act --session my-task state
browser-act --session my-task click 3
```

## Three Browser Modes

| Mode | Scenario | Key trait |
|------|----------|-----------|
| chrome | Reuse local Chrome login | Profile import or CDP attach |
| stealth privacy | Batch scraping without login | Fresh fingerprint per session + proxy rotation |
| stealth fixed identity | Logged-in accounts, multi-browser parallel | Stable fingerprint + stable IP |

## Free vs Paid

Free (no signup): basic browser automation, chrome-direct
Free (login only): stealth browsers ≤5, stealth-extract, solve-captcha, remote-assist, skill-forge
Paid: stealth browsers >5, dynamic/static proxies

## Why it matters for web-ai-cdp-bridge

Our CDP bridge solves the "connect to browser" problem but hits CAPTCHA walls. BrowserAct adds:
- Fingerprint spoofing (navigator.webdriver, canvas, GPU, audio, fonts, screen params)
- Auto solve-captcha (Google reCAPTCHA v3, hCaptcha, Cloudflare, etc.)
- Human handoff when auto-solve fails

Install BrowserAct to upgrade the bridge from "works until CAPTCHA" to "works continuously".