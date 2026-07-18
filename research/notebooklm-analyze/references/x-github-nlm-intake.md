# X / GitHub → NLM 摄入（会话定型）

## 何时用

- 用户发 `https://x.com/<user>/status/<id>` 且内容是工具/仓库/论文/架构
- 用户明确说「喂给 NLM」或默认技术消化

## 抓取

```bash
# 单条推文（无 X 登录）
curl -sL "https://api.fxtwitter.com/<user>/status/<id>"

# README
curl -sL "https://raw.githubusercontent.com/<owner>/<repo>/<branch>/README.md"
```

拼装喂 NLM 的文本必须含：
1. 推文原文 + URL
2. README 全文（或关键目录表）
3. **我们系统背景一段**（便于 4 字段「现状对照」；标清非论文原文）

```bash
nlm notebook create "<主题>-消化"
# Python subprocess 调 nlm source add --text ... --title ... --wait
nlm query notebook <id> "只基于本 notebook：1引用 2对照现状 3另起炉灶? 4下一步唯一动作" --timeout 180
```

## 落产物

- NLM 本 ID + URL 写进笔记 frontmatter
- Obsidian：`技术消化/<主题>/YYYY-MM-DD - ..._分析笔记.md`
- 4 字段齐全；至少 1 个可复用物（笔记默认）

## 反例

- 只聊天摘要、不喂 NLM
- 只丢 x.com / github URL 给 `nlm add url`
- 用 Hermes grok 中继假装读了某人时间线
- 教育仓「全量 clone 30 本」当默认动作（先 NLM 收敛优先 notebook）

## 实例锚点（2026-07-17）

- 推文：`@wayen_ai` / `2077261375567745064` → Sutskever 30 NumPy
- NLM：`fe806db0-db3c-41b7-abb3-ba5c519edd80`
- 笔记：`技术消化/Sutskever30/2026-07-17 - Sutskever30-NumPy奠基论文_分析笔记.md`
