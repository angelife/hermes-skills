---
name: wechat-data-analysis
description: "Extract, decrypt, and analyze WeChat chat history — export formats, decryption workflows, ChatLab integration, and known pitfalls."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [macos]
metadata:
  hermes:
    tags: [WeChat, Data-Analysis, Decryption, ChatLab]
---

# WeChat Data Analysis

Tools and workflows for extracting, decrypting, and analyzing WeChat chat history on macOS.

## Platform Decision

When macOS decryption is blocked (SIP prevents `task_for_pid`, LLDB breakpoint fails), **switch to Android route** if the same WeChat account can be accessed on a rooted Android device:

- iOS → Android: Use WeChat's built-in "迁移到另一台手机" to transfer chat history cross-platform
- Android root + ADB: See `android-wechat-db-decrypt` skill for the working pipeline
- The Android formula key is `MD5("1234567890ABCDEF" + uin)[:7]` + `PRAGMA cipher_compatibility = 1`
- This is the only reliably working path as of 2026-07

## Supported Export Formats (for ChatLab)

ChatLab `import` supports these WeChat-related formats:

| Format ID | Source | File Extension |
|-----------|--------|----------------|
| `weflow` | WeFlow app export | `.json` |
| `ycccc ccy-echotrace` | echotrace export | `.json` |
| `shuakami-qq-exporter` | QQ Chat Exporter | `.json` |

**Native WeChat `.db` files are NOT directly importable** — they use WCDB (SQLCipher 4) encryption and require key extraction first.

## WeChat Database Structure

Located at:
```
~/Library/Containers/com.tencent.xinWeChat/Data/Documents/xwechat_files/<wxid>/db_storage/
├── message/message_0.db          # Chat messages (encrypted)
├── contact/contact.db             # Contacts (encrypted)
├── session/session.db             # Session list (encrypted)
├── sns/sns.db                     # Moments (encrypted)
└── ...
```

Each `.db` is encrypted with per-file AES-256 key cached in WeChat process memory.

## Decryption Workflow (macOS)

### Prerequisites

1. **WeChat 4.x running** — must be logged in
2. **Remove Hardened Runtime** — prevents `task_for_pid` memory reads:
   ```bash
   sudo codesign --force --deep --sign - /Applications/WeChat.app
   ```
3. **Python dependency**:
   ```bash
   pip3 install pycryptodome
   ```

### Tool: wechat-export-macos

Repository: `https://github.com/ydotdog/wechat-export-macos`

Steps:
1. Clone repo
2. Compile C scanner: `cc -O2 -o find_all_keys_macos find_all_keys_macos.c -framework Foundation`
3. Extract keys: `sudo ./find_all_keys_macos`
4. Decrypt: `python3 decrypt_db.py`
5. Export: `python3 export_chat.py --list` then `--name "<contact>" --output <path>`

**Known issue**: On WeChat 4.x, the C scanner may find DB files and salts but extract **zero keys** from memory. The scanner uses Mach VM API (`task_for_pid`) which may fail silently on newer macOS security configurations even after re-signing.

### Alternative: WeFlow App

WeFlow can export WeChat chats as JSON. However:
- No official DMG release available on GitHub
- Requires manual download/build from source
- Output format compatible with ChatLab `--format weflow`

### Alternative: Third-party Tools

- `wechatDataBackup` — Windows-only tool
- `wechat-export-macos` — see above
- `WechatExplorer` — Electron app, supports AI summary generation

## ChatLab Integration

After obtaining exported JSON/TXT files:

```bash
# List supported formats
chatlab formats

# Import
chatlab import path/to/export.json --format weflow

# Analyze
chatlab sessions list
chatlab stats
chatlab members
```

## Pitfalls

1. **Never assume native `.db` is importable** — always check `chatlab formats` first
2. **Hardened Runtime blocks memory scanning** — re-signing is required before key extraction
3. **⚠️ Ad-hoc re-signing BREAKS WeChat backup (iPhone→Mac)** — `codesign --force --deep --sign -` invalidates Apple's original code signature, which macOS may restrict for local network (Bonjour/mDNS) communication. After re-signing, iPhone→Mac chat backup feature stops working. **Fix**: re-install clean WeChat from official site, keep the original signature for backup use; only re-sign a copy if you must.
4. **WeChat update breaks re-signing** — re-run `codesign` after each WeChat update
5. **macOS SIP** — if `task_for_pid` still fails after re-signing, SIP may need to be disabled (not recommended for production machines)
5. **Media files not included** — text-only export; images/videos stored separately in `xwechat_files/Message/`
6. **Group chats show wxid, not names** — need to cross-reference with `contact.db` for display names

## Content Analysis Methodology

### ⚠️ 文章链接处理规则（被用户严厉纠正过）

**从微信群提取外部文章链接时，绝对不要自动存入 Hindsight 记忆层。**

Hindsight 是为个人经验/观察/知识沉淀设计的。外部公众号文章链接属于「外部引用」，不应该作为记忆存储。

正确流程：

| 步骤 | 做什么 | 为什么 |
|------|--------|--------|
| 1 | 提取链接 → 汇报标题和摘要给用户 | 让用户决定看哪篇 |
| 2 | 用户选中的才读取全文 | 不浪费 token 读不相关的 |
| 3 | 提炼有价值的洞察 | 只有从文章中提炼的结论/方法/代码才值得存储 |
| 4 | 有价值的洞察 → 存入 Hindsight observation 或技能 | 结构化、可复用 |
| 5 | 原始链接 → 丢弃 | 需要时去微信群搜即可 |

**反例**（本 session 犯的错）：
```
84 篇公众号链接 → 全量导入 Memory Server → 用户问"目的是啥" → 删掉
```

**正解**：
```
提取链接 → 挑出跟项目相关的 5 篇 → 问用户看哪篇 → 读完后提炼结论
```

---

When the user asks you to **"分析 / analyze"** chat content, the default approach must be **read the actual text**, not count rows. Users will correct you if you only produce statistics.

### The Stats Trap (被用户严厉纠正过)

**Wrong** (this session's initial output — stats only):
```
群1: 8833条消息
- 文本: 5962条发出, 1176条收到
- 图片: 660条发出
- 活跃时段: 10:00-13:00
```

**Right** (what the user actually wanted — narrative):
```
Time | Who | What
4月 | 你 | 连做4个梦, 在群里逐帧解梦 — 梦到地龙、火车开进海里...
5月 | 你 | 长篇黑客哲学
    | 群友 | "群主, 你是教父级别人物了"
6月 | 你 | 17年反邪教、政治批判、AI蒸馏实践
    | 群友 | 广州楼顶220元/月, 投非洲仓库...

总结: 这不是聊天群, 是你的思想日记群
```

### Analysis Protocol

| Step | What to do | Why |
|------|-----------|-----|
| 1 | **读内容** — pull actual text messages by date/type | 数字告诉你量, 内容告诉你质 |
| 2 | **找叙事流** — 按时间线组织主题变化 | 4月梦, 5月黑客, 6月反邪教 — 每个阶段不同关注 |
| 3 | **摘对话** — 提取群友回复, 看谁在说话 | 孤岛独白 vs 双向对话, 完全不同的性质 |
| 4 | **识别人物** — 谁是这个群的参与者 | 主群可能只有2-3人在活跃 |
| 5 | **下判断** — 这个群本质是什么 | 闲聊群/思想日记/资源分享/机器人推送 — 差异极大 |
| 6 | **对比异常** — 迁移前后对比 | iPhone 数据迁入后增长了10倍, 说明旧数据不完整 |

### SQL Queries for Content Reading

```sql
-- 按日期提取群聊内容
SELECT datetime(createTime/1000,'unixepoch','+8 hours') AS t,
       CASE WHEN isSend=1 THEN '我' ELSE substr(content,1,15) END AS who,
       substr(content,1,150) AS msg
FROM message WHERE talker='<chatroom>' AND type=1
AND date(createTime/1000,'unixepoch','+8 hours') = '<YYYY-MM-DD>'
ORDER BY createTime;

-- 提取群友全部回复 (isSend=0, content格式: <发送者wxid>:<消息>)
SELECT datetime(createTime/1000,'unixepoch','+8 hours') AS t,
       substr(content, 1, 120) AS msg
FROM message WHERE talker='<chatroom>' AND type=1 AND isSend=0
ORDER BY createTime;

-- 全量文本导出到文件供分析
sqlite3 /tmp/EnMicroMsg_decrypted.db "
SELECT datetime(createTime/1000,'unixepoch','+8 hours') || '|' ||
       CASE WHEN isSend=1 THEN '我' ELSE '群友' END || '|' ||
       CASE WHEN isSend=0 THEN substr(content,instr(content,':')+1) ELSE content END
FROM message WHERE talker='<chatroom>' AND type=1
ORDER BY createTime;
" > /tmp/group_chat_full.txt
```

### 迁移后数据对比

当 iPhone 数据迁移到 Android 后重新拉取分析，必须做迁移前后对比：

```sql
-- 旧库 vs 新库
sqlite3 /tmp/EnMicroMsg_decrypted2.db "SELECT COUNT(*), COUNT(DISTINCT talker) FROM message;"
sqlite3 /tmp/EnMicroMsg_decrypted3.db "SELECT COUNT(*), COUNT(DISTINCT talker) FROM message;"

-- 新增群聊列表
sqlite3 /tmp/EnMicroMsg_decrypted3.db "
SELECT talker FROM message WHERE talker LIKE '%@chatroom'
EXCEPT
SELECT talker FROM message_old WHERE talker LIKE '%@chatroom';
"
```

对比不仅展示量变, 也是理解数据完整性的关键: 如果从1个群变成4个群, 说明旧的Android数据只是iPhone的子集。

## Quick Reference

| Command | Purpose |
|---------|---------|
| chatlab formats | Show supported import formats |
| chatlab sessions list | List imported sessions |
| chatlab stats | Statistics overview |
| chatlab members | Member activity ranking |
| chatlab chat <session> <question> | AI analysis of specific session |

## Linked Reference Files

| File | Covers |
|------|--------|
| references/pull-wechat-automation.md | Auto-pull cron job, ADB USB/TCP fallback, article link extraction, SQLCipher malformed-query workarounds |
| references/chatroom-analysis.md | SQL query suite for chatroom content extraction |
| references/group-overview-scan.md | Quick group inventory from Decrypted.db — list all chatrooms, identify by nickname, message counts, type distribution, last activity. First step before deep analysis |
| references/group-content-analysis-guide.md | Full narrative/thematic analysis pipeline — profiles, timeline, character judgment. Use when user says "分析一下 [群名]" |
| references/free-model-context-windows.md | Free model context window measurements (opencode-zen) |