---
name: notebooklm-document-analysis
title: NotebookLM Document Analysis
description: "Upload documents (EPUB, PDF, text) to NotebookLM and run comprehensive, source-grounded analysis via async queries. Covers the end-to-end pipeline: locate source, create notebook, upload, query, poll, extract structured answer."
trigger:
  - user asks to "analyze this book/document" or "put this in NotebookLM"
  - user flags your initial analysis as insufficient and wants deeper treatment
  - multi-source document review requiring synthesized insights
---

# NotebookLM Document Analysis Workflow

## When to Use

The user wants deep, source-grounded analysis of a document — a book, research paper, article collection, or technical manual. This goes beyond summarization: they want structured multi-angle analysis with citations.

**Signal phrases**: "丢进notebooklm", "让NotebookLM分析", "这个文档你分析一下", "我觉得你分析的不够全面".

## Prerequisites

- NotebookLM MCP server running (check with `mcp__notebooklm__server_info`)
- Source document accessible on the local filesystem
- Supported formats: EPUB, PDF, TXT, MD, DOCX (see `source_add` tool for full list)

## Workflow

### Step 1: Locate the Source

The document may be at:
- **iBooks**: `~/Library/Containers/com.apple.BKAgentService/Data/Documents/iBooks/Books/<hash>/<hash>.epub`
- **Downloads**: `~/Downloads/Telegram Desktop/` or `~/Downloads/`
- **Projects directory**: anywhere under the working project
- **Obsidian vault**: user's notes directory

Use `search_files(target='files')` or `ls` to locate it. Confirm with the user when the path is ambiguous.

For iBooks EPUBs: navigate the EPUB container's directory to find the text content (usually `OEBPS/` or a numbered dir like `16/GoogleDoc/` with XHTML files). Note that iBooks may split the EPUB into per-chapter directories.

### Step 2: Choose Upload Strategy

| Strategy | When | How |
|----------|------|-----|
| **Full file upload** | Document <=~20MB, single file | `source_add(notebook_id, source_type='file', file_path=abs_path, wait=True)` |
| **Text content paste** | Pages/URLs, or when file path fails | Extract text, paste as `source_type='text'` |
| **URL** | Public web document | `source_add(notebook_id, source_type='url', url=url, wait=True)` |

For EPUB: NotebookLM natively supports EPUB format — upload the `.epub` file directly.

### Step 3: Create a Notebook

Use `mcp__notebooklm__notebook_create(title="Descriptive Title")`. Save the returned `notebook_id` for subsequent operations.

### Step 4: Add Source

```
mcp__notebooklm__source_add(
  notebook_id="...",
  source_type="file",
  file_path="/absolute/path/to/file.epub",
  wait=True,
  wait_timeout=120
)
```

**Important**: The file path must be absolute and accessible on the machine running the MCP server. Use the Mac filesystem path, not a relative path.

### Step 5: Query for Analysis

For **large documents** (full books, 50+ pages), ALWAYS use the **async query** path:

1. Start query: `notebook_query_start(notebook_id, query, timeout=300)`
2. Poll with `notebook_query_status(query_id)` until `status='completed'`
3. The result may be very large (150KB+) — parse it efficiently

For **small documents** (single article, <10 pages), `notebook_query` with a reasonable timeout works fine.

### Step 6: Process Results

The query response is a nested JSON structure. Parse it in two steps:

```
import json
outer = json.loads(raw_result)
inner = json.loads(outer["result"])
answer = inner["result"]["answer"]  # The actual analysis text
```

For large answers (>10KB), use `execute_code` to extract and present sections rather than dumping raw text.

### Step 7: Present to User

If the user asked because your own analysis was insufficient, present NotebookLM's results as the primary deliverable. Structure the output clearly with sections matching the query breakdown.

The notebook remains accessible at the NotebookLM URL for the user to explore directly:
`https://notebooklm.google.com/notebook/<notebook_id>`

## Effective Query Design

Craft prompts that ask for specific structure. The following pattern worked well:

> "请对这本书做全面的深度分析，用中文回答，包含以下内容：
> 1. **全书架构与核心论点**
> 2. **每个章节的核心要旨**（逐一简述）
> 3. **成熟度等级与能力跃迁**
> 4. **最有价值的三个洞察/警告**
> 5. **实际适用分析**（针对我们的项目，给出具体改进方向，含'为什么'和'怎么做'）"

NotebookLM excels at:
- Extracting themes across a full book
- Grounding insights in specific source citations
- Multi-angle analysis (not just summary)
- Practical, actionable recommendations

## Pitfalls

- **Connection timeouts**: The synchronous `notebook_query` may timeout on large books (peer closed connection). Always use `notebook_query_start` + polling for full-book queries.
- **Large results**: The answer can be 150KB+. Don't try to dump it raw — parse the JSON and extract structured sections.
- **File path accessibility**: The MCP server runs on the local machine. Files must be accessible at the same absolute path. Use `wait=True` to confirm upload succeeded.
- **iBooks path topology**: iBooks container formats vary. Some organize by numbered directories (`16/GoogleDoc/`), others by `OEBPS/`. Check the directory structure after finding the `.epub`.
- **Multiple files**: If the document is split across files (e.g., iBooks per-chapter XHTML), prefer uploading the whole EPUB rather than individual files.
