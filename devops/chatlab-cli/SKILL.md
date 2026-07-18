---
name: chatlab-cli
description: "Install, configure, and use ChatLab CLI for chat history analysis across QQ/WeChat/Telegram/WhatsApp/Discord/Instagram/LINE formats."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos]
metadata:
  hermes:
    tags: [ChatLab, Data-Analysis, Chat-History, CLI]
---

# ChatLab CLI

CLI tool for importing and analyzing chat history from 14+ platforms (QQ, WeChat, Telegram, WhatsApp, Discord, Instagram, LINE, etc.).

## Installation

### macOS — Known Compilation Issue

On macOS, `npm install -g chatlab-cli` may fail during `better-sqlite3` compilation with:

```
fatal error: 'climits' file not found
```

This happens because the Node.js buildpack's SDK headers aren't discoverable by node-gyp. Fix:

```bash
export CXXFLAGS="-isysroot $(xcrun --show-sdk-path) -I$(xcrun --show-sdk-path)/usr/include/c++/v1"
export CFLAGS="-isysroot $(xcrun --show-sdk-path)"
export CPPFLAGS="-isysroot $(xcrun --show-sdk-path)"
npm install -g chatlab-cli
```

Alternative: `pnpm install -g chatlab-cli` or download desktop DMG from GitHub releases.

### Linux

```bash
npm install -g chatlab-cli
# or
pip install chatlab
```

## Usage

```bash
# List supported import formats
chatlab formats

# Import a chat history file
chatlab import path/to/file.json --format weflow
chatlab import path/to/file.txt --format whatsapp-native-txt

# Analyze imported sessions
chatlab sessions list
chatlab stats
chatlab members

# AI-powered chat analysis
chatlab chat "<session-id>" "Summarize the key decisions made"
```

## Supported Formats

| Format ID | Platform | File Type |
|-----------|----------|-----------|
| `weflow` | WeChat | JSON |
| `ycccccccy-echotrace` | WeChat | JSON |
| `shuakami-qq-exporter` | QQ | JSON |
| `telegram-native` | Telegram | JSON |
| `whatsapp-native-txt` | WhatsApp | TXT |
| `discord-native` | Discord | JSON |
| `instagram-native` | Instagram | JSON |
| `line-native-txt` | LINE | TXT |
| `chatlab` | Any | JSON |
| `chatlab-jsonl` | Any | JSONL |

## Pitfalls

1. **Native WeChat `.db` is NOT importable** — must use WeFlow or echotrace exporter first
2. **`--format` is optional** but recommended when auto-detection fails
3. **Desktop app vs CLI** — the GUI app is separate from the CLI; they serve different purposes
4. **Memory-scanning tools for WeChat** — on newer macOS, key extraction from WeChat process memory often returns zero keys even after re-signing (see `wechat-data-analysis` skill)

## Related Skills

- `wechat-data-analysis` — WeChat-specific decryption and export workflows