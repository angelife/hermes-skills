# ChatLab CLI — 聊天记录分析

**Repo:** github.com/ChatLab/ChatLab  
**CLI:** npmjs.com/package/chatlab-cli  
**Version installed:** 0.30.2  

## Install on macOS

```bash
# better-sqlite3 needs the macOS SDK path
export CXXFLAGS="-isysroot $(xcrun --show-sdk-path)"
export CFLAGS="-isysroot $(xcrun --show-sdk-path)"
npm install -g chatlab-cli
```

Without `CXXFLAGS`, `better-sqlite3` fails with: `fatal error: 'climits' file not found` — Node.js 23's node-gyp doesn't auto-detect the C++ standard library path.

## Commands

| Command | Description |
|---------|------------|
| `chatlab sessions` | List chat sessions |
| `chatlab messages list` | Query messages |
| `chatlab members <session-id>` | Member activity ranking |
| `chatlab stats <session-id>` | Session statistics |
| `chatlab update` | Update to latest version |

## Usage

```bash
chatlab sessions
chatlab messages list --session <id> --limit 20
chatlab stats <session-id> --type overview
chatlab members <session-id>
```

## Data Import

ChatLab requires exported chat data (not directly accessible via CLI). Export from:
- **WeChat Desktop:** Settings → Export Chat History → select session → export
- **WhatsApp/Discord:** use platform's export feature
- Then import into ChatLab (desktop app) or pass to CLI via file path

## AI Analysis

ChatLab has an AI Agent for natural-language queries. Can be queried through the CLI or desktop app.
