# Dual-path Kindle browser diagnosis (2026-07-17)

Verified on: Kindle Paperwhite 5, FW 5.16.2.1.1, KOReader v2026.03, LanguageBreak + Hotfix 2.5.0 marker present.

## Device facts

- Mount: `/Volumes/Kindle`
- Serial USB: Lab126 Internal Storage `G001PX1114150KMW`
- Plugin present: `koreader/plugins/webbrowser.koplugin/`
- Config keys that mattered:
  - `engine = "duckduckgo"`
  - was `render_type = "markdown"` → fixed to `"cre"`
- Old net_report (2026-07-13): WiFi CONNECTED, IP 192.168.0.142, ping/DNS/HTTP OK

## Path A — Experimental Browser (system)

Log signatures still active after hotfix era:

```
x509 certificate couldn't be obtained
Failed to open session with TEE: code 0xffff3024
Unable to allocate memory for DHAv2 certificate
Request Signing Failure. StatusCode: 1
AmazonDHAv2JwtSigner / JwtSigner errors
```

Meaning: OS networking can be healthy while mesquite/cvm cannot sign/validate device certs. Do not treat as "proxy problem" or "PMTUD problem" unless user points there.

Practical bypass: Mac Web Bridge `http://<mac-ip>:8081`

## Path B — KOReader webbrowser.koplugin

Failure mode seen:

- Plugin installed and configured
- History shows direct opens to baidu / local dashboard
- `render_type=markdown` depends on `https://r.jina.ai/...`
- Mac-side probe: `r.jina.ai` TLS handshake timeout; `example.com` HTTP/HTTPS OK

Fix:

```lua
render_type = "cre"
```

Then: `sync` + eject + **full KOReader restart**.

## Web Bridge runtime (this fleet)

- Path: `~/kindle-bridge/proxy.py`
- Port: **8081** (8080 was already serving another local HTML server)
- Verify:

```bash
curl -s http://127.0.0.1:8081/ | head
curl -s 'http://127.0.0.1:8081/?url=http://example.com' | head
```

Expect: 200, body contains `Kindle Web Bridge` / `Example Domain`.

## Operator checklist (next session)

1. Mount Kindle USB → read `version.txt`, hotfix marker, plugin config
2. Grep latest `system/logbackup/*.gz` for x509/TEE/JwtSigner
3. Grep plugin config for `render_type`
4. If markdown → switch to cre, sync, eject, full KOReader restart
5. Start/confirm Web Bridge on free port (prefer 8081)
6. Tell user two exact test paths only — no option soup
