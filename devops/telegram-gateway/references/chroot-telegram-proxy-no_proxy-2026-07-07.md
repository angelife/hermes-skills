# Mi8 chroot Hermes Telegram proxy + NO_PROXY incident

- Date: 2026-07-07
- Device: Xiaomi Mi8 dipper
- Hermes path: `/data/local/tmp/chroot/debian/root/.hermes`
- Symptom: gateway log showed `httpx.ConnectError` and kept retrying Telegram fallback IPs.
- Cause: `NO_PROXY` in `/root/.hermes/.env` explicitly excluded `api.telegram.org` and Telegram fallback IPs. Hermes source (`gateway/platforms/base.py`) respects `NO_PROXY`, so `HTTPS_PROXY` was ignored for Telegram.
- Evidence:
  - `/proc/<pid>/environ` confirmed `HTTPS_PROXY`, `HTTP_PROXY`, and `NO_PROXY=api.telegram.org,149.154.166.110,149.154.167.220`
  - After removing `NO_PROXY` from a retained copy of `.env`, gateway log changed from `httpx.ConnectError` to `Proxy detected; passing explicitly to HTTPXRequest: http://192.168.1.8:10808`
- Secondary evidence: after correcting `.env` token from numeric user-id-like value to valid bot token from BotFather, the next failure mode switched directly to Telegram `401 Unauthorized` via curl, then `token rejected by the server` in Hermes logs. This confirms proxy is otherwise functional.
- Also affected Mi6 (2026-07-07, same session): Same NO_PROXY in `.env` caused `httpx.ConnectError`. Mechanism was **`set -a` + `.env` overwrite** — the startup script exported `NO_PROXY=127.0.0.1,localhost,192.168.1.0/24`, then `set -a; . .env; set +a` loaded `.env` which had `NO_PROXY=api.telegram.org,149.154.166.110,149.154.167.220`, silently overwriting the safe value.
- `set -a` causes `.env` values to WIN over script-level `export` statements placed before the `source .env` line. Place trusted defaults AFTER `set +a` or audit `.env` for conflicting `NO_PROXY`/`no_proxy` entries.
- On Linux/Mac, `os.environ.get("NO_PROXY")` is case-sensitive — `.env` may have both `no_proxy` and `NO_PROXY` separately. Removing only one is insufficient.
- Lessons:
  - Do not write `NO_PROXY=api.telegram.org` for Telegram Hermes gateways.
  - `set -a` + `.env` sourcing means `.env` values always WIN over earlier script exports. Audit both vars on readback.
  - `.env` on chroot devices must be treated as a full-file write, not in-place `sed` patch.
  - After `.env` edits, verify with `/proc/<pid>/environ` + a small chroot-side helper that prints only `PROXY` keys.
  - Check BOTH `no_proxy` and `NO_PROXY` — Hermes `resolve_proxy_url` reads from `os.environ` which is case-sensitive; the `.env` may have both variants.
