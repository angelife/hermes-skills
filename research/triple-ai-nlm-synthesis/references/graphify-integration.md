# Graphify — 项目代码知识图谱工具

## 是什么

Graphify (github.com/safishamsi/graphify, 86k⭐) 将项目代码库转为 AI 可查的知识图谱。  
AI 通过查图谱定位代码关系，不需要逐文件读取。

## 本文位置

本机已安装在 `/Users/macos/angelife.github.com/.venv/bin/graphify`。  
Hermes 技能已通过 `graphify hermes install` 集成到 AGENTS.md。

## 基本用法

```bash
cd /path/to/project
source .venv/bin/activate

# 建图/更新图（AST-only，无 API 费用）
graphify update .

# 查询项目结构
graphify query "这个项目如何组织路由？"

# 查看两个节点间关系
graphify path "hugo-site/content" "hugo-site/layouts"

# 解释某个概念
graphify explain "Hugo shortcode"
```

## 集成平台

| 平台 | 命令 | 自动行为 |
|------|------|---------|
| Hermes | `graphify hermes install` | 写入 AGENTS.md |
| Claude Code | `graphify claude install` | 写入 CLAUDE.md + PreToolUse hook |
| Codex | `graphify codex install` | 写入 AGENTS.md |
| Cursor | `graphify cursor install` | 写入 .cursor/rules/graphify.mdc |

## 本项目 (angelife.github.com) 的图谱

- 图谱输出目录：`graphify-out/`
- 社区结构：God nodes（核心入口节点）+ community clustering
- 图文件：`graphify-out/graph.json`
- 架构报告：`graphify-out/GRAPH_REPORT.md`
- Wiki：`graphify-out/wiki/index.md`（如存在）

## 更新策略

修改代码后运行 `graphify update .`（AST-only，不调用 LLM，免费且快）。
