---
name: notebooklm-analyze
title: "NotebookLM 深度分析 — 文章精读迭代器"
description: "把文章导入 NotebookLM → 深度分析 → 拉回分析结果 → 审查 → 再喂回去迭代。夜间自学核心引擎。"
category: research
tags: [night, reading, analysis, notebooklm, proxy]
---

# NotebookLM 深度分析 — 文章精读迭代器

## 流程

```
文章 → 导入 NotebookLM → 深度分析 → 拉回结果 
→ 审查 → 汇总多篇 → 再喂回去 → 再分析 → 循环
```

## CLI 语法注意事项

```bash
# 创建笔记本 — title 是位置参数，没有 -t 选项
nlm create notebook "笔记本名称"

# 从文本内容添加源（推荐，任何内容都可以）
nlm add text <notebook_id> "<文本内容>" --title "标题" --wait

# 从 URL 添加源（单条）— URL 是位置参数，不是 --url 选项
nlm add url <notebook_id> "https://..." --wait

# 从本地文件添加源（需要读取文件内容作为 text 传入）
CONTENT=$(cat ./文档.md)
nlm add text <notebook_id> "$CONTENT" --title "文档标题" --wait

# 查询指定笔记本
nlm query notebook <notebook_id> "问题"

# 导出分析报告为 Markdown
nlm export report --format markdown > /tmp/nlm_analysis.md
```

## 触发时机

- **微信文章精读** — 用户发链接时（默认工作流）
- **X 推文 / GitHub 教育仓 / 技术种草帖** ⭐ — 用户发 `x.com/.../status/...` 且内容指向工具/仓库/论文时，**默认走 NLM**（用户原话：「喂给 nlm 最合适」），禁止只做聊天摘要交差。流程见下节「X/GitHub → NLM」。
- **技术文档/说明书消化** ⭐ — **优先级第一，超过自己逐行阅读**。当需要理解一个软件/工具的架构、部署条件、配置选项时，不要自己逐行读文档，直接喂 NotebookLM。用户明确说过：「你自己消化太慢」「消化的不如 nlm 好」。此场景执行以下流程：
  1. 获取文档全文（`web_extract` README / 本地缓存文件）
  2. 创建专用笔记本 → `nlm create notebook "XXX 说明书消化"`
  3. 添加为 source → `nlm add source ./文档.md`
  4. 问 3-5 个核心问题（架构、部署要求、与本系统对比）
  5. 拉回分析结果作为消化报告
- **多文档对比** — 同主题多篇需要交叉比对时
- **相似笔记本合并/清壳** — 用户问「两个 notebook 能合并吗」时走「笔记本合并 / 清壳」节

## X / GitHub → NLM（2026-07-17 定型）

```
推文 URL → 抓正文（优先 fxtwitter）
  → 若挂 GitHub：再抓 README 全文
  → 拼「推文+README+我们系统背景」→ nlm add text（禁止只丢 x.com/github 链接指望 NLM 自抓）
  → 强制 4 字段 query
  → 落可复用物：Obsidian 技术消化/<主题>/_分析笔记.md + NLM 本 ID
```

**抓取优先级（单条推文）：**
1. `https://api.fxtwitter.com/{user}/status/{id}` — 无需 X 登录，常够用
2. `web_extract` x.com / twitter.com 镜像
3. `opencli twitter`（daemon `:19825` 健康时）/ `xurl`（已授权时）

**禁止混淆：** 会话里的 `grok-4.5`（中继 API）**没有** x.com 实时时间线；不得声称「Grok 默认读了 X」。真要扫某人时间线 → 走 X 通道，不是聊天模型。

**落库路径：** `~/Documents/Obsidian Vault/技术消化/<主题>/YYYY-MM-DD - <标题>_分析笔记.md`  
（微信文仍走 `微信公众号文章/`；X/GitHub 技术消化走 `技术消化/`。）

详见 `references/x-github-nlm-intake.md`。

## ⚠️ 网络要求

NotebookLM (Google) 在中国大陆被墙。需要代理才能正常使用。

```bash
# 测试代理
curl -s --connect-timeout 5 -x socks5://127.0.0.1:10808 https://www.googleapis.com/
curl -s --connect-timeout 5 -x http://127.0.0.1:7890 https://www.googleapis.com/
```

如果 `nlm` 命令超时，通常是网络问题，不是工具坏了。先测代理再怀疑工具。

## 前提条件：登录

```bash
# 首次需要浏览器完成 Google OAuth
nlm login

# 验证登录
nlm doctor
# 确认显示：Cookies: present, CSRF token: yes, Account: xxx@gmail.com
```

登录后的凭证存在 `~/.notebooklm-mcp-cli/profiles/default/cookies.json`。

## 步骤

### 1. 导入文章

```bash
# 按主题创建笔记本（title 是位置参数，没有 -t 选项）
nlm create notebook "微信文章-2026-07"

# 从 URL 导入 — URL 是位置参数
nlm add url <notebook_id> "https://raw.githubusercontent.com/..." --wait

# 或从本地文件（README、Obsidian 备份等）
CONTENT=$(cat ./文档.md)
nlm add text <notebook_id> "$CONTENT" --title "文档标题" --wait
```

### 2. 触发分析（强制 4 字段输出）

```bash
# 自动生成简报
nlm create report

# 标准对照问法 — notebook_id 是必需的；输出必须含 4 字段
nlm query notebook <notebook_id> "只基于本 notebook 资料回答：
1) 核心洞察（每条附引用源/段落）
2) 对照我们现有系统：已有 / 没有 / 做过类似
3) 是否另起炉灶？能复用什么？
4) 下一步唯一推荐动作（只给 1 个）
禁止泛泛建议；没有依据就写「资料不足」。"
```

**强制输出模板（缺一不可）：**

| 字段 | 含义 |
|------|------|
| 引用源 | 哪篇/哪段说的 |
| 现状对照 | 已有 / 没有 / 做过类似 |
| 是否另起炉灶 | 还是复用现成 |
| 下一步 1 个动作 | 唯一可落地推荐 |

缺字段 → 重问，不得把残缺答案当交付。

### 3. 拉回结果 → 必须落可复用物

```bash
# 导出分析报告为 Markdown
nlm export report --format markdown > /tmp/nlm_analysis.md

# 追加到 Obsidian 分析笔记
cat /tmp/nlm_analysis.md >> ~/Documents/Obsidian\ Vault/.../_分析笔记.md
```

**每轮 NLM 输出必须至少产出 1 个可复用物（不许看完就关）：**

| 可选产物 | 何时用 |
|---------|--------|
| `_分析笔记.md` 追加 4 字段结论 | 默认，几乎每次 |
| 现有 skill 补丁 | 发现可复用流程/坑 |
| 系统配置/代码改动 | 人拍板后执行 |
| cron / 脚本 | 需周期性复用 |

### 4. 迭代循环

```
审查 NotebookLM 分析 → 核对 4 字段齐全 → 落可复用物 →
发现新问题 → 再次提问 → 拉回 → 整合 → 多篇汇总 → 再导入
```

## 相关技能

- **`notebooklm-research-prep`** — 项目前期研究用。搜全资料→喂 nlm→拿结论→再动手。适合「想了解某工具能不能用」的场景，和本技能互补。

## 笔记本合并 / 清壳（无原生 merge）

`nlm notebook` **没有** `merge` / `copy`。相似笔记本要合并时：

```bash
# 1) 列出
nlm notebook list

# 2) 看源（判断是「重复」还是「同主题互补」）
nlm source list <id_a>
nlm source list <id_b>

# 3) 把源本的 URL/文件/文本重新加到目标本
nlm source add <target_id> --url "https://..." --wait
# 或: nlm source add <target_id> --file ./book.pdf --wait
# 或: nlm source add <target_id> --text "..." --title "..." --wait

# 4) 确认目标源齐了 → 再删源本（不可逆；需 --confirm）
nlm notebook delete <source_id> --confirm
```

**用户选定合并方案（A/B/C）后必须执行到 delete 闭环**，只 list/定位本地文件不算完成。无 URL 的 epub 用 Calibre/`mdfind` 找本地后 `nlm source add --file ... --wait`。

### 合并判定（2026-07-17 实测）

| 情况 | 处理 |
|------|------|
| 同名/同主题且 **source_count=0** 空壳 | **直接删**，无合并价值 |
| 同名有源 + 空壳（如 PMTUD 双本） | 留有源本，删空壳；有源本内重复 text 源可 `nlm source delete` 去重 |
| 主题相近但材料不同（例：李博杰 Agent 书本 vs Agentic Design Patterns 本） | **可选并**（交叉问方便）或 **不并** + `nlm cross query` / `nlm batch query` |
| 只想跨本问一次 | 优先 `nlm cross query`，不必物理合并 |

### 清理空壳命令模板

```bash
# 确认空再删
nlm source list <id>   # 必须是 []
nlm notebook delete <id>
```

空壳常见于：创建本后喂源失败、重复建诊断本、OpenBridge 超时后半成品。  
详见 `references/session-20260717-notebook-merge.md`。

## 适合的分析类型

1. **单篇精读**：导入一篇 → 问 3-5 个深度问题 → 拉回笔记
2. **多篇对比**：导入同主题多篇 → 问「共同点和分歧」
3. **知识整合**：导入一批 → 问「和现有系统有什么联系」
4. **趋势识别**：按时间导入 → 问「主题演变路径」
5. **技术说明书消化** ⭐ — README、官方文档、架构说明 → 问核心架构、部署条件、替代方案、与本系统的对比
6. **群文批量交叉 + 夜训任务单** ⭐ — 见 `references/night-unmanned-training-task.md`

## 群文批量交叉 + 无人化夜训（2026-07-17）

用户说「全部整理推给 nlm」或「让 NLM 布置今晚无人化训练 / 完全授权」时：

```
1. 新建主题本 → 精选 12–20 篇全文 nlm add text（禁止只丢 URL）
2. 交叉分析 → 落 技术消化/<主题>/
3. 再 query 夜训任务单（无人值守/失败降级/机制锁死/4–8h）
4. 完全授权 → 按任务单执行，降级不卡死
5. 交付：Briefing + AnalysisTable + ReviewChecklist + 凌晨交付 + RUNLOG
```

产物：`技术消化/夜训-YYYY-MM-DD/` 与 `~/.hermes/state/night-training-YYYY-MM-DD/`。

## 🔴 微信/付费墙文章：必须喂全文，禁止只丢链接

**用户原话（2026-07-17）：「你发地址给他没用 你要把内容发给它 地址它认不出」**

| 来源类型 | 正确做法 | 错误做法 |
|---------|---------|---------|
| `mp.weixin.qq.com` | 先抓全文 → 备份 Obsidian → **`nlm add text` 喂正文** | `nlm source add --url` / `nlm add url` 只丢微信链接 |
| 需登录/JS 渲染页 | 本地 Markdown/TXT 全文 | 指望 NLM 自己抓 URL |
| 公开 raw GitHub / PDF | 可用 `nlm add url` | — |

**CLI 实操：** 先剥 YAML frontmatter 的 `---`（否则 CLI 当选项炸）；长文用 Python `subprocess` 调 `nlm add text`，避免 shell 拆坏；再用 `nlm query notebook <id> "问题" --timeout 180`。

**NLM 中心制：** 架构/设计类文章 → 先喂 NLM 拿统一方案 → 再对照本地现状 → 再动手。禁止自己综合完再「象征性」丢链接。

## Pitfalls

- ❌ **微信链接直接 `nlm add url` / `source add --url`** — NLM 认不出正文（2026-07-17 翻车）
- ❌ **`nlm add text` 传入带 `---` frontmatter 的 Markdown** — CLI 把 `---` 当选项；先剥 frontmatter
- ❌ **shell 直接 `nlm add text id "$(cat file)"`** — 长文易炸；优先 Python subprocess
- ❌ 国内网络连不上 Google → 需要代理（socks5://127.0.0.1:10808 或 HTTP）
- ❌ nlm 命令超时通常是网络问题，先测代理再怀疑工具
- ❌ 不是 `nlm auth status`（没有这个子命令），用 `nlm doctor` 验证
- ❌ `nlm add url` 的 URL 是位置参数，不是 `--url` 选项 — 正确：`nlm add url <id> "https://..." --wait`
- ❌ 添加多个来源时用同一个笔记本 ID，不要重复创建
- ❌ **NLM 建议 ≠ 立刻改代码** — 拉回后必须对照本地实现（已有功能/主路径模型）再拍板
- ❌ **只贴聊天不落产物** — 每轮必须至少 1 个可复用物（笔记/skill/配置/脚本）
- ❌ **缺 4 字段就交付** — 引用源 / 现状对照 / 是否另起炉灶 / 下一步 1 动作；缺则重问
- ❌ **为接 NLM 另装 Claude Cowork / notebooklm-py** — 已有 `nlm` CLI，禁止另起炉灶
- ❌ **X 技术帖只聊天摘要** — 用户默认要 NLM；走「X/GitHub → NLM」
- ❌ **用 grok-4.5 中继冒充读了 X 时间线** — 中继无 live X；单帖用 fxtwitter / opencli / xurl
- ❌ **以为有 `nlm notebook merge`** — 没有；合并=重加源到目标+删源本；跨本问用 `nlm cross query`
- ❌ **空壳本不删堆着** — `source_count=0` 直接删，别当「相似可合并」
- ❌ **用户选了 C 却只调研** — 合并/清壳要 `source add` + `notebook delete --confirm` + 再 list 验证（2026-07-17 翻车）
- ❌ **无 URL 源硬 `source add --url`** — `type=unknown` 必须本地 `--file`
- ✅ 全文备份已在 Obsidian，NotebookLM 宕机不影响已有数据
- ✅ 分析结果拉回后追加到已存的分析笔记，不会丢失

## 高级用法：交叉对比分析

同个笔记本可以添加多个 source（书 + 架构文档 + 代码），然后问对比问题：

```bash
# 1. 创建笔记本
nlm create notebook "AI Agent 书 vs 我们架构"

# 2. 添加多个 source
nlm add url <id> "https://raw.githubusercontent.com/.../book.pdf" --wait
nlm add text <id> "$(cat ./architecture.md)" --title "我们架构" --wait

# 3. 问对比问题
nlm query notebook <id> "请对比这本书的理论框架和我们的架构：哪些做对了？哪些缺失？建议如何调整？"
```
