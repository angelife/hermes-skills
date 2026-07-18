# 火同学 Deployment Reference

## Device identity
- Hostname: 火同学 (192.168.1.23)
- OS: macOS Catalina 10.15.8 (x86_64)
- User: macos
- RAM: 8 GB
- Disk: 113 GB total, ~10 GB used
- Battery: Swollen (keep plugged in, avoid heat)
- Bot: @SwarmDiscussionBot (token in .env/huo.tokens.md)
- Hermes v0.18.0 installed via official install script

## Proxy configuration (critical!)

**Three env vars needed for full connectivity:**
- `TELEGRAM_PROXY=socks5://192.168.1.8:10808` — Telegram polling
- `HTTP_PROXY` / `HTTPS_PROXY` — model API calls (opencode.ai etc.)
- `ALL_PROXY` — catch-all

Without `HTTP_PROXY`, the bot connects to Telegram and receives messages but **silently hangs** on API calls (agent.log shows `Stream stale` errors).

Current .env (full proxy config):
```
TELEGRAM_PROXY=socks5://192.168.1.8:10808
HTTP_PROXY=socks5://192.168.1.8:10808
HTTPS_PROXY=socks5://192.168.1.8:10808
ALL_PROXY=socks5://192.168.1.8:10808
NO_PROXY=localhost,127.0.0.1,192.168.0.0/16,10.0.0.0/8
```
- Connected to LAN (en0, likely)
- No proxy configured in OS settings
- Reachable via SSH at 192.168.1.23
- Telegram access via xray SOCKS5 on 土同学: `socks5://192.168.1.8:10808`
- Google Gemini API is blocked (no route to Google from CN)
- ZhiPu API reachable but key may have insufficient balance

## Hermes config
- **Default provider**: opencode-zen (free DeepSeek via `https://opencode.ai/zen/v1`)
- **API key**: Stored in `~/.hermes/.env` as `OPENCODE_ZEN_API_KEY`
- **Fallback provider**: zhipu (`glm-4.5-air`)
- **Model**: `deepseek-v4-flash-free` (free tier)
- **Telegram proxy**: `socks5://192.168.1.8:10808` via xray on 土同学
- **Gateway**: launchd service, auto-start at login
- **Agent memory**: disabled (8 GB RAM constraint)

## Key files on 火同学
| File | Purpose |
|------|---------|
| `~/.hermes/SOUL.md` | **Persona** — defines 火同学 identity, behavior, and communication style |
| `~/.hermes/config.yaml` | Provider + agent config |
| `~/.hermes/.env` | API keys, bot token, proxy |
| `~/.local/bin/hermes` | Hermes CLI launcher |
| `~/.hermes/hermes-agent/venv/bin/hermes` | Actual binary |
| `~/.hermes/logs/gateway.log` | Gateway logs |
| `~/.hermes/logs/agent.log` | Agent session logs |
| `~/.hermes/logs/errors.log` | Error log |
| `~/.hermes/state.db` | Session state (SQLite) |
| `~/.hermes/sessions/sessions.json` | Session index |

## SOUL.md (current persona)

Written on 2026-07-03. Defines 火同学 as 五行团队的火元素. The bot uses "🔥" prefix and answers concisely. Loaded per-turn (no gateway restart needed). Verified working: `hermes -z "自我介绍"` → "🔥 我是火同学，五行团队的火元素——负责行动、即时响应与执行..."

## Diagnostic tips from session

- **Bot connected but "答非所问" (irrelevant response)**: Check SOUL.md. Without a proper persona, the model defaults to generic Nous Research agent behavior and may give off-topic answers. A properly written SOUL.md with role, team, and communication style dramatically improves response relevance.
- **Bot "dead" (connected but no reply)**: Three-layer proxy check. See skill's "Bot not responding — diagnostic checklist" table. The most common cause: ALL_PROXY missing → model API calls hang while Telegram itself works.
- **Gateway restart blocked**: `hermes gateway restart` is blocked from within the agent process tree. Workaround: `kill <PID>` (launchd auto-restarts). Verify with `ps aux | grep gateway`.
- **Env rewrite accident**: When using Python to rewrite `.env`, ensure ALL required keys are included (bot token, API key, proxy). A partial rewrite that drops `TELEGRAM_BOT_TOKEN` or `OPENCODE_ZEN_API_KEY` silently breaks the bot.

## Common operations
```bash
# SSH in
ssh macos@192.168.1.23

# Run hermes (must export PATH)
export PATH="$HOME/.local/bin:$PATH"
hermes --version

# Quick API test
hermes -z "ping" -m deepseek-v4-flash-free --provider opencode-zen

# Gateway status
hermes gateway status

# Restart gateway (if config changed)
# NOTE: Can't restart from inside agent process tree!
# Use: kill <PID> # launchd auto-restarts
```

## Gateway log markers
- `Proxy detected; passing explicitly to HTTPXRequest: socks5://...` — proxy working
- `Connected to Telegram (polling mode)` — connected
- `✓ telegram connected` — green light
