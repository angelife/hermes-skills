# Daily Knowledge Pipeline — Hermes + OpenCLI + Obsidian

Concrete implementation from 2026-07-03 session. A fully automatic daily knowledge collection, compilation, and storage pipeline.

## Architecture

```
每天 9:00
   │
   ▼
采集脚本  (~/.hermes/scripts/daily-knowledge-collect.sh)
   │  知乎热榜 (Zhihu API, not opencli zhihu hot)
   │  微信文章 (opencli weixin search)
   │  GitHub Trending (GitHub API)
   ▼
Hermes cron (script= collects data → prompt= compiles → stores)
   │  清洗、去重、摘要
   │  分类（技术趋势/好文章/实用工具/个人思考）
   │  写入 Obsidian 结构笔记
   ▼
Obsidian vault (~/Documents/Obsidian Vault/知识简报/YYYY/MM/YYYY-MM-DD-知识简报.md)
   │
   ▼
Telegram 推送
```

## Components

### 1. Collection Script

Path: `~/.hermes/scripts/daily-knowledge-collect.sh`

A bash script that uses OpenCLI + Zhihu API + GitHub API to collect from 3-4 sources.
The script's stdout becomes the Hermes cron job's context.

**Zhihu hot list** — uses the official Zhihu developer API (not `opencli zhihu hot` which may fail):
```python
# Key: ZHIHU_API_KEY from ~/.hermes/.env
# Endpoint: https://developer.zhihu.com/api/v1/content/hot_list
# Headers: Authorization: Bearer <key>, X-Request-Timestamp: <unix epoch>
# Returns 30 items max, no pagination. Items have Title, ContentText, Url, RankingScore
```
Use this pattern when opencli zhihu hot returns nothing. The Zhihu API key is always available.

**WeChat articles** — `opencli weixin search "关键词"` — relies on Sogou WeChat search via Chrome extension. May need Chrome session active.

**GitHub trending** — `curl -s 'https://api.github.com/search/repositories?q=created:>$(date -v-7d +%Y-%m-%d)&sort=stars&order=desc&per_page=5'` — no API key needed.

### 2. Cron Job

```bash
# Create the cron
cronjob action=create
  name="每日知识采集与编译"
  script="daily-knowledge-collect.sh"  # runs first, stdout = context
  skills='["obsidian"]'
  prompt="## 任务：每日知识编译 ..."
  schedule="0 9 * * *"
  attach_to_session=true
```

Key parameters:
- `script`: The collection script (runs before prompt, output = context)
- `skills: ["obsidian"]`: Loads Obsidian skill so the agent can write to vault
- `prompt`: Instructs Hermes to compile the raw data into structured notes, write to Obsidian
- `deliver`: Delivers summary to Telegram
- `attach_to_session: true`: Creates a continuable thread

### 3. Note Structure (Obsidian)

File: `知识简报/YYYY/MM/YYYY-MM-DD-知识简报.md`

```markdown
# 知识简报 YYYY-MM-DD

## 📡 技术趋势
...

## 📚 好文章
...

## 🔧 实用工具
...

## 💡 我的思考
...
```

### 4. Compilation Prompt Template

```
## 任务：每日知识编译

你收到的是 OpenCLI 采集的今日原始数据。你的工作：

1. **阅读采集数据** — 来自知乎热榜、微信文章精选、GitHub 热门
2. **去重与筛选** — 去掉低质量内容，保留值得记录的知识点
3. **编译结构化笔记** — 按以下格式输出：
   ## 📡 技术趋势
   ## 📚 好文章
   ## 🔧 实用工具
   ## 💡 我的思考
4. **写入 Obsidian** — 使用 obsidian 技能将编译后的笔记写入到
   `/Users/macos/Documents/Obsidian Vault/知识简报/YYYY/MM/YYYY-MM-DD-知识简报.md`
```

## When to Use This Pattern

- User asks "搭建知识采集系统" / "全自动知识库" / "daily digest"
- User wants to collect from specific web sources on a schedule
- User has both OpenCLI and Obsidian available
- User wants Hermes cron to both collect AND compile (not just relay)

## Pitfalls

1. **Zhihu API with Python from bash** — use embedded python3 -c "" with proper quoting. The single quotes inside the Python string must not conflict with the outer shell quotes.
2. **WeChat article search via OpenCLI** requires Chrome extension session. May fail if extension expired. Not critical — the pipeline runs with partial data.
3. **Script output must be structured** — the cron context is raw text. Use clear `--- [SOURCE] ---` separators so Hermes can identify which source produced which output.
4. **Obsidian vault path with spaces** — always quote in tools: `"/Users/macos/Documents/Obsidian Vault/"`.
5. **First run should be manual** — verify the pipeline end-to-end before scheduling daily cron.
6. **Script is NOT idempotent** — it appends to Obsidian. If cron fails mid-way, check the vault for partial writes.
