# book-to-skill: Converting Books/Docs into Skills

## Overview

[book-to-skill](https://github.com/your-org/book-to-skill) (5.3k GitHub stars) converts technical PDFs, EPUBs, document folders, and other structured text into a complete Agent Skill directory.

## Output Structure

Created under `~/.claude/skills/<slug>/` (or Hermes equivalent `~/.hermes/skills/`):

| File | Description | Size |
|------|-------------|------|
| `SKILL.md` | Core mental models + chapter index | ~4000 tokens |
| `chapters/` | One file per chapter, loaded on demand | ~800-1200 tokens each |
| `glossary.md` | All key terms, alphabetized, chapter-tagged | varies |
| `patterns.md` | Design patterns, algorithms from the book | varies |
| `cheatsheet.md` | Decision tables + quick-reference rules | varies |

## Key Design Principles

1. **Lazy loading** — chapters are individual files; only asked-about chapters are loaded into context
2. **Smart extraction** — technical books (code, tables, formulas) → Docling (~1.5s/page, preserves structure); plain text → pdftotext (instant)
3. **Output is structure, not summary** — never copies original text; synthesizes, patterns, signal
4. **Incremental updates** — new content can be folded into existing skill directories
5. **Not just books** — any structured text (docs/, brand guides, paper collections, RFCs)

## Use Cases

- Technical books → reference skill for coding
- Documentation folder → project knowledge skill
- Brand books → design system skill
- Paper collections → research skill
- Compliance docs → always-available reference

## 手动提取工作流（pdfminer + 手工写作）

当 book-to-skill CLI 工具不适用（如中文PDF、特殊排版、或需要定制结构）时，可用以下工作流替代：

### 步骤

1. **提取全文**
   ```bash
   python3 -c "
   from pdfminer.high_level import extract_text
   text = extract_text('path/to/book.pdf')
   with open('/tmp/extracted.txt', 'w') as f:
       f.write(text)
   "
   ```
   检查输出大小：`wc -c /tmp/extracted.txt`。一般学科书籍 150-200KB 为正常范围。

2. **分析章节结构**
   对中文书籍，按章节标题模式切分：
   ```bash
   grep -n "^第.*章" /tmp/extracted.txt    # 中文版
   grep -n "^#\|^Chapter" /tmp/extracted.txt  # 英文版
   ```
   记录每章起止行号，确认各章节结构完整性。

3. **编写 SKILL.md（核心）**
   - YAML frontmatter（name, title, author, version, tags, category）
   - 核心心智模型（系统三要件、存量/流量/反馈回路、两种回路类型）
   - 章节索引（指向 references/ 下的文件）
   - 核心框架速查表（陷阱对照表、杠杆点排序、法则清单）
   - 适用场景
   - 参考文件清单

4. **编写 references/ 子文件**
   - `ch01.md` 至 `ch0N.md` — 每章一个文件，内容精简到关键框架+图表+概念，不复制原文
   - `glossary.md` — 术语表（术语+释义，按字母或章节排序）
   - `patterns.md` — 可复用的分析框架/诊断模板/决策矩阵
   - `example-*.md` — 可选：该框架应用于真实问题的案例

5. **处理技能冲突**
   ```bash
   ls ~/.hermes/skills/ | grep <candidate-name>
   ```
   若已存在同名技能，确认来源（`skill_view(name)`），必要时删除旧版再重新创建。

6. **验证**
   - `skill_view(name)` 确认返回完整内容
   - 如果适用，在真实问题上跑一遍该框架确认可操作性

### 适用场景
- 中文技术书籍/写作指南
- 跨领域的元方法论（如系统思考、设计思维）
- 电子书没有结构化标记，需要人工分章
- PDF 中的表格/公式/代码块需要特殊处理

### 与 book-to-skill CLI 工具的对比

| 方面 | CLI 工具 | 手动工作流 |
|------|---------|-----------|
| 速度 | 快（秒级生成） | 慢（需逐一写作） |
| 灵活度 | 低（固定输出结构） | 高（可定制每章节内容） |
| 语言支持 | 英文为主 | 中英文均可 |
| 质量控制 | 自动但可能遗漏 | 人工把关 |
| 冲突处理 | 无 | 手动处理现有技能冲突 |
