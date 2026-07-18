# Session 2026-07-17 — Jina blocked, cre default

## Config before
```lua
engine = "duckduckgo"
render_type = "markdown"  -- uses https://r.jina.ai/http://TARGET
```

## Failure mode
- Search engine path can still look alive
- Opening a result / loading content fails when gateway unreachable
- User-facing: "Unable to load content" or blank

## Proof Jina unusable (this network)
```bash
curl -s --max-time 15 "https://r.jina.ai/http://example.com"
# observed: TLS handshake timeout
```

## Fix
```lua
engine = "duckduckgo"
render_type = "cre"
```
Then: `sync && diskutil eject /Volumes/Kindle` → user fully exits + reopens KOReader.

## Rule for this fleet
- **Default always `cre`**
- Only try `markdown` after live Jina check succeeds on the same egress
- If both cre and Experimental Browser fail: Mac Web Bridge on **8081** (`~/kindle-bridge/proxy.py`)

## Re-verify 2026-07-17 afternoon
- Jina still TLS timeout on this egress
- Bridge still healthy: `http://192.168.0.171:8081/?url=http://example.com` → 200 + Example Domain
- Cannot re-check on-device `webbrowser_configuration.lua` without `/Volumes/Kindle`
- Do **not** claim plugin config is current unless USB mass-storage is mounted this session

## Explain Jina in one line (user asked "jina是啥")
Jina here = remote page-to-Markdown gateway `r.jina.ai`. Not a Kindle local binary. Blocked ⇒ markdown mode dies; cre does not use it.
