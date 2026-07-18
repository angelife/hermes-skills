---
name: project-knowledge-graph
description: 为项目生成知识图谱（project map）——让 AI 先认识代码关系再动手，避免盲搜文件。基于 graphify 工具实现。
tags:
  - project-mapping
  - knowledge-graph
  - graphify
  - codebase-understanding
---

# Project Knowledge Graph (项目地图)

## When to Use

When asked to:
- "为项目建立地图 / 知识图谱"
- "先扫一遍项目结构"
- "搞清楚这个项目的模块关系"
- Any large unfamiliar project where you need structural context

## Install graphify

```bash
# 推荐直连 PyPI（不走代理反而稳定）
uv pip install graphifyy

# 装 openai 扩展（LLM 社区命名需要）
uv pip install openai
```

## Workflow

### Step 1: Extract — AST 提取

纯本地 AST 解析，不需要 API key。跳过文档/图片/非代码文件（`--code-only`）。

```bash
graphify extract /path/to/project --code-only --out /tmp/graphify_out
```

产物：
- `graphify-out/graph.json` — 节点和边
- `graphify-out/GRAPH_REPORT.md` — 初步报告（社区名是占位符）
- `graphify-out/.graphify_analysis.json` — 分析数据

### Step 2: Cluster — 社区聚类（可选）

```bash
graphify cluster-only /tmp/graphify_out
```

更新社区划分，可加 `--no-viz` 跳过 HTML（大项目用）。

### Step 3: Label — LLM 社区命名

需要 OpenAI 兼容 API + `openai` 包。

```bash
export OPENAI_API_KEY="your-key"
export OPENAI_BASE_URL="https://your-endpoint/v1"
export OPENAI_MODEL="model-name"
graphify label /tmp/graphify_out --backend openai --max-concurrency 1 --batch-size 50
```

### Step 4: Hermes 集成

```bash
# 在项目目录下运行，写入 AGENTS.md
graphify hermes install
```

以后 Hermes 进入该项目目录时自动加载项目知识图谱引导。
注意：graphify 通常装在项目 `.venv` 中，需要先 `source .venv/bin/activate` 激活才能使用 graphify 命令。

### Step 5: 建立图谱（首次）

```bash
# 激活项目虚拟环境
source .venv/bin/activate

# 纯 AST 提取（零 API 费用），会自动更新增量文件
graphify update .

# 产物：
# - graphify-out/graph.json       — 节点和边
# - graphify-out/GRAPH_REPORT.md  — 社区报告
# - graphify-out/graph.html       — 可视化
```

### Step 6: 查询

```bash
graphify query "某个模块的功能" --graph /tmp/graphify_out/graphify-out/graph.json
graphify affected "某个节点名" --graph /tmp/graphify_out/graphify-out/graph.json
graphify explain "某个节点" --graph /tmp/graphify_out/graphify-out/graph.json
```

## Backend Compatibility Notes

| Backend | Compatibility | Notes |
|---------|--------------|-------|
| NVIDIA API (`integrate.api.nvidia.com/v1`) | ✅ 完全兼容 | `meta/llama-3.1-8b-instruct` 返回标准 JSON，推荐 |
| OpenCode Zen (`opencode.ai/zen/v1`) | ❌ JSON 格式不兼容 | `deepseek-v4-flash-free` 不返回 graphify 期望的 JSON |
| Standard OpenAI API | ✅ 完全兼容 | gpt-4o-mini 性价比高 |

## Pitfalls

1. **没有 `openai` 包则 LLM 命名失败** — graphify label 会报 "the 'openai' package is required"。解决方案：`uv pip install openai`
2. **Proxy 干扰** — 走代理时 PyPI 下载可能超时/断流。直连反而更稳定。如果在家，`unset http_proxy https_proxy HTTP_PROXY HTTPS_PROXY` 再装
3. **社区命名环境变量** — `export OPENAI_API_KEY` 必须在运行 `graphify label` 的 shell 中生效；`~/.graphify/config.yaml` 可能不被 label 命令读取
4. **大项目节点多** — 先跑 `--code-only` 快速出图，LLM 命名可以后续单独 `graphify label`
5. **minified JS 污染图谱** — 项目中有大量第三方库（jQuery、prettify 等）时，图谱会包含这些库的函数节点，可能掩盖自有代码结构
