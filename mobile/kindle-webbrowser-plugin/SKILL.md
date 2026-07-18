---
name: kindle-webbrowser-plugin
description: Install, configure, and troubleshoot the webbrowser.koplugin (text-based web browser) on a jailbroken Kindle Paperwhite running KOReader. Covers download, deployment, config setup, DuckDuckGo default, render mode switching, and HTTPS/SSL fetch debugging.
---

# Kindle Webbrowser Plugin (webbrowser.koplugin)

Install and troubleshoot the text-based web browser plugin for KOReader on jailbroken Kindle e-ink devices.

## Trigger

Use when:
- User wants a web browser on a jailbroken Kindle with KOReader
- webbrowser.koplugin is installed but pages won't load
- Search works but opening results fails
- Plugin shows "Unable to load content" or "configuration file not found"

## Installation

### Step 1: Download

```bash
cd /tmp
curl -sL --max-time 30 "https://github.com/omer-faruq/webbrowser.koplugin/archive/refs/tags/v0.7.0.tar.gz" -o wb.tar.gz
tar xzf wb.tar.gz
```

### Step 2: Copy to Kindle

```bash
mkdir -p /Volumes/Kindle/koreader/plugins/webbrowser.koplugin/
cp -r webbrowser.koplugin-0.7.0/* /Volumes/Kindle/koreader/plugins/webbrowser.koplugin/
```

### Step 3: Configuration

The plugin requires `webbrowser_configuration.lua` (not `.sample.lua`):

```bash
cp /Volumes/Kindle/koreader/plugins/webbrowser.koplugin/webbrowser_configuration.sample.lua \
   /Volumes/Kindle/koreader/plugins/webbrowser.koplugin/webbrowser_configuration.lua
```

**Set DuckDuckGo as default engine** (no API key needed):

```lua
engine = "duckduckgo",  -- instead of "brave_api"
```

**Default render mode must be `"cre"`** (direct fetch via `socket.http`):

```lua
render_type = "cre",  -- NOT markdown unless r.jina.ai is proven reachable
```

Do **not** default to `"markdown"`. Markdown depends on Jina AI gateway `r.jina.ai`. On many China/home networks that host TLS-times-out; search may still work while opening results fails with "Unable to load content".

Only switch to markdown after an explicit reachability check succeeds:

```bash
curl -s --max-time 15 "https://r.jina.ai/http://example.com" | head
```

### Step 4: Eject and test

```bash
sync && diskutil eject /Volumes/Kindle
```

User must fully exit and reopen KOReader for plugin discovery.

## Plugin Entry Point

The plugin registers via `addToMainMenu` with `sorting_hint = "search"`, so it appears under KOReader's **Search** menu area, not Tools. If not visible, check Plugin Manager to confirm it's loaded.

## Troubleshooting HTTPS/SSL Fetch Failures

### Symptom: Search works, clicking result shows "Unable to load content"

The plugin uses KOReader's `socket.http` with `ssl.https` (LuaSec) for HTTPS fetching. On jailbroken Kindles this can fail even when curl works.

**KOReader has SSL support bundled:**
- `koreader/common/ssl.lua` + `ssl.so`
- `koreader/common/ssl/https.lua`
- `koreader/data/ca-bundle.crt`
- `koreader/libs/libssl.so.60`

### Render Modes

| Mode | Method | Dependency | Reliability |
|------|--------|------------|-------------|
| `cre` | Direct HTTPS fetch via socket.http | KOReader LuaSec + CA bundle | May fail on jailbroken devices |
| `mupdf` | Direct HTTPS fetch (same as cre) | MuPDF renderer | Same as cre |
| `markdown` | Via Jina AI gateway (r.jina.ai) | Internet access to r.jina.ai | May be blocked in China |

### Fix Steps (order matters)

1. **Confirm current config** on USB mount:
   ```bash
   grep -E 'engine|render_type' /Volumes/Kindle/koreader/plugins/webbrowser.koplugin/webbrowser_configuration.lua
   ```
2. **Force `cre` first** (default for this fleet / China networks):
   ```lua
   engine = "duckduckgo",
   render_type = "cre",
   ```
   Then `sync && diskutil eject /Volumes/Kindle`. User must **fully exit + reopen KOReader**.
3. **Only if cre still fails**, check Jina reachability from Mac on the same egress:
   ```bash
   curl -s --max-time 15 "https://r.jina.ai/http://example.com" | head
   ```
   - Reachable → may try `render_type = "markdown"`
   - TLS timeout / blocked → **never** use markdown; go to Web Bridge
4. **Mac Web Bridge fallback** — if plugin still fails, or user needs Experimental Browser:
   - Code: `~/kindle-bridge/proxy.py`
   - Prefer port **8081** if 8080 is already taken
   - Kindle opens: `http://<mac-lan-ip>:8081`
   - Keep Mac + Kindle on same WiFi; keep proxy process running

### Dual-path diagnosis (do not mix)

| Path | Symptom | Root cause | Fix |
|------|---------|------------|-----|
| Experimental Browser | every URL spins / blank | x509 / TEE cert broken in system logs | Web Bridge or hotfix |
| webbrowser.koplugin | search OK, open result fails | `render_type=markdown` + Jina blocked | set `render_type=cre` |

Network can be 100% fine (ping/DNS/HTTP/HTTPS curl OK) while both paths still fail for independent reasons.

## Pitfalls

- **Write must flush** — After copying files to the Kindle, `sync` before `diskutil eject`. An interrupted eject (timeout) can silently lose writes even though `cp` reported success.
- **Plugin not showing** — KOReader only scans `plugins/` at startup. Full restart is required (not just sleep/resume).
- **DuckDuckGo may return 302** — From some networks (China), the HTML search endpoint redirects. The plugin handles this internally but curl tests may show 302.
- **Brave API default** — The sample config defaults to `brave_api` which requires a Brave Search API key. Always switch to `duckduckgo` for no-key operation.
- **markdown is not a free upgrade** — In China / filtered egress, markdown is usually *worse* than cre because it hard-depends on `r.jina.ai`.
- **Port 8080 often occupied** — Local dashboards/test servers may already bind 8080; use 8081 for Kindle Web Bridge and give the user the exact URL.
- **Explain Jina when asked** — Jina here means the page-to-Markdown gateway `r.jina.ai`, not a local Kindle binary. If blocked: search may work, open-result fails.
- **Never use browser path for file transfer** — Same-LAN + `python -m http.server` is **not** a transfer plan when Experimental Browser / webbrowser is known broken (x509/TEE or Jina). User correction 2026-07-17: 「浏览器问题 之前不是没解决么」. For PDF/books use Calibre wireless, SSH.koplugin, or USB mass storage — see `kindle-diagnostics` 传文件 section. Details: `references/session-20260717-no-http-for-books.md`.
- **Bridge URL must be HTTP** — Plugin history may show `https://<mac-ip>:8081`. That fails on broken x509/TEE. Always deliver `http://<mac-ip>:8081`. Details: `references/session-20260717-usb-http-not-https.md`.
- **Config already cre is not done** — On USB mount with full-authorization, still stamp config, write HOW_TO + net_diag, verify SSH keys, sync, eject, restart bridge. Don't stop at "already correct".
