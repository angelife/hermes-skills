# Session 2026-07-17 — Experimental Browser blank for days + dual path

## Device
- Kindle Paperwhite (Lab126 USB Vendor 0x1949), serial G001PX1114150KMW
- Jailbroken + KOReader + webbrowser.koplugin present
- USB mass storage at `/Volumes/Kindle` when mounted

## User symptom
- Experimental Browser stuck on `https://www.baidu.com/...` blank gray page for many days
- Later: address bar "输入无效" / frozen
- User asked whether factory reset is the simplest fix

## Evidence already on device (USB)
- `documents/net_report.txt` pattern: network layer green (WiFi/IP/DNS/HTTP/HTTPS curl OK in prior diags)
- System logbackup lines (class):
  - `JwtSigner: x509 certificate couldn't be obtained`
  - `Unable to read device identifiers`
  - `Request Signing Failure`
- Plugin config found with:
  - `engine = "duckduckgo"`
  - `render_type = "markdown"`  ← depends on `https://r.jina.ai/...`

## Mac-side checks that mattered
- `https://r.jina.ai/http://example.com` → TLS handshake timeout (blocked/unusable)
- `http://example.com` / `https://example.com` from Mac OK
- Local port 8080 already occupied by a simple HTTP server → use **8081**
- Web Bridge `~/kindle-bridge/proxy.py` on `0.0.0.0:8081`:
  - `GET /` → 200 Kindle Web Bridge home
  - `GET /?url=http://example.com` → 200 with Example Domain
  - `GET /?url=https://www.baidu.com` → 200 (proxy path works)

## Actions taken
1. Change plugin: `render_type = "cre"` (keep duckduckgo)
2. `sync` + `diskutil eject /Volumes/Kindle`
3. Start Mac Web Bridge on 8081
4. Coach user:
   - Do not keep opening Baidu in Experimental Browser
   - Force reboot if input stuck
   - Preferred: KOReader → Search → Web Browser
   - Optional: system browser only to `http://<mac-lan-ip>:8081`

## Factory reset ranking (user Q)
**Not simplest.** Order: bypass (plugin/Bridge) → Universal Hotfix → cache/hard reboot → factory last (re-JB risk + data loss; may not fix TEE/x509).

## Coaching phrases that worked
- "空白是证书坏了的预期现象，不是网断了"
- "只输 `http://192.168.0.171:8081`，必须 http，不要直接 baidu"
- "出厂不是优先方案"

## Follow-ups if still broken
1. Confirm KOReader fully restarted after cre change
2. If cre still fails: keep Bridge; do not flip back to markdown unless Jina reachability proven
3. If user insists on system browser: Universal Hotfix 2.5.0 (watch for 1% stuck history)
