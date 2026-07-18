# Browser Automation Toolchain — 2026-07-12

Three complementary tools for browser automation, each covering a different need:

## Tool Comparison

| Tool | Role | Backend | Best for |
|------|------|---------|----------|
| OpenBridge | Execution | Port 10088 (Node.js daemon) | All browser actions — the chosen backend |
| Browser-BC | Recording → Skill | Port 8099 (Python server) | Fixed workflows, repeated operations |
| NanoBrowser | Planning → Execution | Chrome extension (no server) | One-shot exploratory tasks |

## OpenBridge

Preferred browser execution backend (replaces CDP).

- Status check: `cd ~/.openbridge/repo && node packages/daemon/dist/cli/index.js status`
- API port: 10088
- Entry point: `~/.hermes/skills/web-ai-cdp-bridge/scripts/ask-openbridge.js`

## Browser-BC (Journey Forge Local)

Located at `~/Browser-BC/`.

### Installation

```bash
git clone https://github.com/Einsia/Browser-BC.git ~/Browser-BC
cd ~/Browser-BC && python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt
cd extension && npm install && npm run build
```

### Configuration

```bash
# .env.local — do NOT include /v1 in SF_LLM_BASE (code appends it)
SF_LLM_KEY=<your-api-key>
SF_LLM_BASE=https://api.deepseek.com        # NOT /v1
SF_DISTILL_MODEL=deepseek-chat
SF_CLASSIFY_MODEL=deepseek-chat
JFL_AUTODISTILL=1
JFL_PORT=8099
```

### Start server

```bash
cd ~/Browser-BC && source venv/bin/activate && export $(grep -v '^#' .env.local | xargs) && python3 server/server.py
```

### Workflow

1. Open Chrome → load extension from `extension/dist/chrome-mv3/` (Developer mode)
2. Click extension → Start Recording → walk through the operation
3. Stop → Upload → auto-distill starts
4. Output: `data/harness/skills/<domain>/<capability>/SKILL.md` + TRACE_GUIDE.md + meta.json
5. The SKILL.md can be copied to `~/.hermes/skills/` for reuse with Hermes + OpenBridge

### Pitfalls

- **SF_LLM_BASE /v1**: The harness code appends `/v1/chat/completions`. If base includes `/v1`, the URL becomes `https://.../v1/v1/chat/completions` → **404**.
- **DeepSeek balance**: `HTTP 402 Insufficient Balance` means the API key is out of credits. Switch to NVIDIA API.
- **NVIDIA API for distillation**: Use `https://integrate.api.nvidia.com/v1` with model `meta/llama-3.3-70b-instruct`. Free tier has rate limits but works.
- **.env loading**: The server reads env vars from the process environment, NOT from `.env.local` automatically. You must `export $(grep -v '^#' .env.local | xargs)` before starting.

## NanoBrowser

Chrome Web Store extension for AI browser automation. Multi-agent (Planner + Navigator).

### Configuration (NVIDIA API)

| Setting | Value |
|---------|-------|
| Base URL | `https://integrate.api.nvidia.com/v1` |
| API Key | NVIDIA nvapi key |
| Planner Model | `meta/llama-3.3-70b-instruct` |
| Navigator Model | `meta/llama-3.1-8b-instruct` |

Settings are stored in Chrome's LevelDB at `~/Library/Application Support/Google/Chrome/Default/Local Extension Settings/imbddededgmcgfhfpcjmijokokekbkal/`.

### Limitations

- Cannot navigate to `chrome-extension://` URLs via headless browser — settings must be configured through the extension's own side panel / options page
- NVIDIA free tier: ~20-50 req/min rate limit
