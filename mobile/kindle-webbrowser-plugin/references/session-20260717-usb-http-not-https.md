# Session 2026-07-17 — USB mount: HTTP not HTTPS

## Discovery
`webbrowser_website_history.json` showed repeated opens of:
```
https://192.168.0.171:8081
```
while the Mac bridge only serves plain HTTP on 8081. With system x509/TEE broken, https-to-local-bridge fails even when the bridge is healthy.

## On-disk state when mounted
```lua
engine = "duckduckgo"
render_type = "cre"
```
Already correct. Still wrote stamp + HOW_TO + net_diag + verified authorized_keys + sync + eject.

## Bridge home page should say
- Use HTTP only: `http://192.168.0.171:8081`
- Do NOT use https for this bridge
- Quick links: example.com / Wikipedia / HN via `/?url=`

## Agent launch
Restart bridge with Hermes `terminal(background=true)`, not shell `nohup`.
