# Kindle PW5 (11th Gen) — Session Notes

## Device
- Model: Kindle Paperwhite 5 (11th Gen), codename "malbec"
- Firmware: 5.16.2.1.1 (409748 002)
- Jailbreak: LanguageBreak (firmware ≤ 5.16.2.1.1)
- KOReader: v2026.03 (KindlePaperWhite5)

## Symptoms & Root Causes

### Experimental Browser won't load websites
- Network layer ✅ (ping, DNS, HTTP, HTTPS all work via curl)
- Browser spins indefinitely on any URL
- Root cause: Amazon's Experimental Browser uses ancient WebKit (circa 2015)
  that cannot render modern HTTPS pages
- Secondary: x509 certificate store may be broken from jailbreak

### x509 Certificate errors
Log signatures: `JwtSigner: x509 certificate couldn't be obtained`,
`Request Signing Failure`
- May be present since initial jailbreak but not always symptomatic
- KindleModding universal hotfix 2.5.0 resolves this (updates Java keystore)

## Fixes Applied (in order)

1. **KindleModding universal hotfix 2.5.0** — exited demo mode, fixed cert store
   - Downloaded from GitHub releases
   - Applied via Kindle's "Update your Kindle" menu (`;dsts`)
   - Result: `.demo` files removed, DONT_CHECK_BATTERY removed, device reset

2. **webbrowser.koplugin** (v0.7.0) — KOReader plugin for text-based browsing
   - DuckDuckGo search (no API key) + Jina AI Markdown conversion
   - Default render: CRE mode
   - Configuration file needed: copy `webbrowser_configuration.sample.lua` →
     `webbrowser_configuration.lua`
   - Set engine to `duckduckgo` (Brave needs API key)

## webbrowser.koplugin Limitations
- Search (DuckDuckGo) works reliably
- Page loading may fail — likely `socket.http` SSL issues in KOReader's
  LuaSec on Kindle
- The `ca-bundle.crt` exists at `koreader/data/ca-bundle.crt` but LuaSec
  may not use it properly
- Three render modes: CRE (direct fetch, default), MuPDF (direct fetch),
  Markdown (via Jina AI r.jina.ai)
- Jina AI may be blocked from China networks

## Better Approach (for next time)
- Skip Experimental Browser debugging entirely
- Go straight to KOReader + webbrowser.koplugin
- If SSL fetch fails, try all 3 render modes
- If none work, the Mac-based web proxy (kindle-bridge/proxy.py)
  is the most reliable fallback
