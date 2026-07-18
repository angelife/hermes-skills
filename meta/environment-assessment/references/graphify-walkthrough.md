# Graphify 项目地图 — 安装与使用笔记

> 环境评估后，若确认直连外网可用，可装 graphify 给项目建知识图谱。

## 安装

```bash
# 核心安装（不带 LLM 后端）
uv pip install graphifyy

# LLM 命名需要额外包
uv pip install openai
```

⚠️ 包名是 `graphifyy`（两个 y），命令行工具叫 `graphify`（一个 y）。

## 工作流

### 1. 纯代码提取（无 LLM，免费）

```bash
graphify extract <项目路径> --code-only --out <输出目录>
```

输出：`graph.json`（节点+边），不含语义标注。

### 2. 聚类 + 报告

```bash
graphify cluster-only <输出目录> --no-viz
```

生成 `GRAPH_REPORT.md`，社区名称为 `Community N` 占位符。

### 3. LLM 命名社区

需要设置以下环境变量：

```bash
export OPENAI_API_KEY="你的key"
export OPENAI_BASE_URL="https://兼容openai的地址/v1"
export OPENAI_MODEL="模型名"
graphify label <输出目录> --backend openai --max-concurrency 1 --batch-size 50
```

### 4. Hermes 集成

```bash
graphify hermes install
```

写入 `AGENTS.md`，让 Hermes 自动在项目对话中参考图谱。

## 已知问题

| 问题 | 原因 | 解决 |
|------|------|------|
| `No API key for backend 'openai'` | env 没传进去 | `source .env` + `export` 后再运行 |
| `label response is not parseable JSON` | 模型不按 JSON 回复 | 换标准 OpenAI 兼容端点（如 NVIDIA） |
| `Proxy` 下安装失败 | 隧道 EOF | 直连（`unset http_proxy https_proxy`） |
| 大项目提取慢 | 文件多 | 先写 `.graphifyignore` 排除 node_modules/ 等 |
