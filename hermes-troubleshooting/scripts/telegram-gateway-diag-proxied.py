#!/usr/bin/env python3
"""Telegram Gateway diagnostic that respects HTTP(S)_PROXY / TELEGRAM_PROXY.

Identical report to scripts/telegram-gateway-diag.py but routes through whatever
proxy the gateway is configured with. Critical because:

- The gateway's HTTPXRequest sets a proxy URL explicitly ("[Telegram] Proxy
  detected; passing explicitly to HTTPXRequest: http://127.0.0.1:10808").
- A naive urllib/curl call from a shell will bypass that proxy and report
  "Telegram fine", masking the real outage.

Use this script BEFORE declaring the Telegram API or the proxy dead.

Reads proxy in this precedence:
  1. TELEGRAM_PROXY env var (or in ~/.hermes/.env)
  2. HTTPS_PROXY / https_proxy (gateway's httpx uses HTTPS_PROXY for https URL)
  3. HTTP_PROXY / http_proxy
  4. Direct (no proxy)
"""
import json
import os
import subprocess
import sys
import urllib.request
from pathlib import Path

ENV_PATH = Path.home() / ".hermes" / ".env"
TOKEN_VAR = "TELEGRAM_BOT_TOKEN"
PROXY_VARS = ["TELEGRAM_PROXY", "HTTPS_PROXY", "https_proxy", "HTTP_PROXY", "http_proxy"]


def read_env_file(path: Path) -> dict:
    out = {}
    if not path.exists():
        return out
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        out[k.strip()] = v.strip().strip('"').strip("'")
    return out


def auth_from_env() -> str:
    # Try process env first, then ~/.hermes/.env
    token = os.environ.get(TOKEN_VAR, "")
    if not token:
        env = read_env_file(ENV_PATH)
        token = env.get(TOKEN_VAR, "")
    if not token:
        # Fallback: shell `hermes` CLI (asks for redaction in transcript)
        try:
            r = subprocess.run(
                ["bash", "-lc", f'printenv {TOKEN_VAR}'],
                capture_output=True, text=True, timeout=5,
            )
            token = r.stdout.strip()
        except Exception:
            token = ""
    if not token:
        print(f"ERROR: {TOKEN_VAR} not found in env or {ENV_PATH}", file=sys.stderr)
        sys.exit(2)
    return token


def pick_proxy(env: dict) -> str | None:
    for k in PROXY_VARS:
        v = os.environ.get(k) or env.get(k)
        if v:
            return v
    return None


def tg_api(token: str, method: str, proxy: str | None, timeout: int = 15):
    """If proxy is set, shell out to curl. Else urllib direct (matches urllib's
    no-proxy semantics and avoids $HTTPS_PROXY side effects)."""
    url = f"https://api.telegram.org/bot{token}/{method}"
    if proxy:
        cmd = ["curl", "-sS", "--max-time", str(timeout), "-x", proxy, url]
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout + 5)
        try:
            return json.loads(r.stdout)
        except json.JSONDecodeError:
            return {"error": f"curl exited {r.returncode}: {r.stderr.strip()[:200]}"}
    else:
        try:
            with urllib.request.urlopen(url, timeout=timeout) as resp:
                return json.loads(resp.read())
        except Exception as e:
            return {"error": str(e)}


def main() -> int:
    env = read_env_file(ENV_PATH)
    token = auth_from_env()
    proxy = pick_proxy(env)

    print("=" * 64)
    print("TELEGRAM GATEWAY DIAGNOSTIC (proxy-aware)")
    print("=" * 64)
    print(f"Token source: {'process env' if os.environ.get(TOKEN_VAR) else ENV_PATH}")
    print(f"Proxy: {proxy or '(none — direct connection)'}")
    print()

    # 1. Identity
    me = tg_api(token, "getMe", proxy)
    if not me.get("ok"):
        print(f"FAIL: getMe returned: {me}")
        print("→ If curl exit != 0, the proxy is unreachable.")
        print("→ Verify: curl -x '{proxy}' https://api.telegram.org/bot{token[:8]}.../getMe")
        return 1
    bot = me["result"]
    print(f"Bot: {bot['first_name']} (@{bot['username']})  id={bot['id']}")
    print(f"Can read all group messages: {bot.get('can_read_all_group_messages')}")

    # 2. Webhook / polling / pending
    print("\n--- Connection ---")
    wh = tg_api(token, "getWebhookInfo", proxy)
    if wh.get("ok"):
        r = wh["result"]
        if r.get("url"):
            print(f"Mode: Webhook ({r['url']})")
            print(f"Last error: {r.get('last_error_message', 'none')}")
        else:
            print("Mode: Polling (no webhook)")
        print(f"Pending updates stuck on Telegram: {r.get('pending_update_count', 0)}")
    else:
        print(f"getWebhookInfo failed: {wh}")

    # 3. getUpdates — distinguishes "Telegram has no messages for us" from
    # "the gateway can't reach Telegram". Returns ok=True with result=[] when
    # everything's fine, returns errors when proxy/network/auth are broken.
    print("\n--- getUpdates (short poll) ---")
    upd = tg_api(token, "getUpdates?limit=1&timeout=0", proxy)
    if upd.get("ok"):
        n = len(upd["result"])
        print(f"Updates visible to API: {n} (0 is fine if user hasn't sent anything yet)")
    else:
        print(f"getUpdates failed: {upd}")
        return 1

    # 4. Local gateway process check
    print("\n--- Hermes gateway process ---")
    try:
        r = subprocess.run(
            ["pgrep", "-fl", "hermes_cli.main.*gateway"],
            capture_output=True, text=True, timeout=5,
        )
        if r.stdout.strip():
            for line in r.stdout.strip().splitlines():
                print(line)
        else:
            print("(no gateway process running)")
            print("→ Bootstrap: launchctl bootstrap gui/$(id -u) "
                  "~/Library/LaunchAgents/ai.hermes.gateway.plist")
    except Exception as e:
        print(f"pgrep failed: {e}")

    # 5. fd limit + active TCP socket summary (if a gateway is running)
    print("\n--- Resource headroom ---")
    pid = subprocess.run(
        ["pgrep", "-f", "hermes_cli.main.*gateway"],
        capture_output=True, text=True,
    ).stdout.split()[0] if subprocess.run(
        ["pgrep", "-f", "hermes_cli.main.*gateway"], capture_output=True, text=True
    ).stdout.strip() else None
    if pid:
        try:
            limits = subprocess.run(
                ["launchctl", "print", f"gui/{os.getuid()}/ai.hermes.gateway"],
                capture_output=True, text=True, timeout=10,
            ).stdout
            for line in limits.splitlines():
                if "maxfiles" in line.lower():
                    print(line.strip())
                    break
            tcp = subprocess.run(
                ["netstat", "-an", "-v", "-p", "tcp"],
                capture_output=True, text=True, timeout=10,
            ).stdout
            states = {}
            for line in tcp.splitlines():
                if f" {pid}." in line:
                    parts = line.split()
                    if len(parts) >= 6 and parts[5] in (
                        "ESTABLISHED", "CLOSE_WAIT", "TIME_WAIT", "FIN_WAIT_2", "LAST_ACK"
                    ):
                        states[parts[5]] = states.get(parts[5], 0) + 1
            for k, v in sorted(states.items(), key=lambda x: -x[1]):
                print(f"TCP {k}: {v}")
            if states.get("CLOSE_WAIT", 0) > 5:
                print("⚠ CLOSE_WAIT > 5 = leak from httpx via proxy, gateway will recycle soon")
        except Exception as e:
            print(f"resource check failed: {e}")
    else:
        print("(no gateway pid — skipping)")

    print("\n" + "=" * 64)
    print("DIAGNOSE:")
    if not me.get("ok"):
        print("  ❌ Bot API unreachable via chosen path. Fix proxy / network first.")
    elif not wh.get("ok"):
        print("  ❌ getWebhookInfo failed — usually proxy or DNS.")
    elif wh.get("result", {}).get("pending_update_count", 0) > 0:
        print("  ⚠ Pending updates stuck on Telegram — gateway polling likely broken.")
    elif not pid:
        print("  ⚠ No gateway running — bootstrap launchd service.")
    else:
        print("  ✓ Bot API reachable, no stuck updates, gateway running.")
        print("  → If user still complains: check fd limit / proxy chain / Telegram-side 5min slot.")
    print("=" * 64)
    return 0


if __name__ == "__main__":
    sys.exit(main())
