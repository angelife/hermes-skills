# OpenViking — 结构化 Agent 记忆系统

> ByteDance/火山引擎开源, v0.4.9, 26.7k stars
> GitHub: github.com/volcengine/OpenViking
> Docs: docs.openviking.ai

## 核心思路

把记忆做成**虚拟文件系统 (AGFS)**。Agent 用 `ls`/`find`/`grep` 操作记忆，路径定位 + 关键词命中代替纯向量语义搜索。

## 架构

三个组件：
- **Server** (端口 1933): 记忆存/查/向量化，纯 CPU 可跑
- **CLI** (`ov ls`/`ov find`): 直接查看记忆
- **Agent 集成**: 通过 REST API 或 MCP 协议连接

## 记忆生命周期

1. 对话结束 → Agent 自动调用 `commit()`
2. commit 分两步：对话归档生成 L0/L1 摘要 → LLM 提取 8 类记忆（偏好/工具/事件/模式等）
3. 写入 AGFS 文件系统 + 重新向量化
4. 每次 commit 成本约 ¥0.01
5. 下次对话自动预取相关记忆注入上下文

## Hermes 集成

一条命令：`hermes memory setup` → 选 openviking → 填服务地址
对话自动预取 + 结束自动 commit，完全无感。
新增 5 个工具：`viking_search`、`viking_read`、`viking_browse` 等。

## Benchmark (v0.3.22, LoCoMo)

| Agent | 原生准确率 | +OpenViking | token 节省 |
|-------|-----------|-------------|-----------|
| OpenClaw | 24.2% | 82.1% | -91% |
| Hermes | 33.4% | 82.9% | -34% |
| Claude Code | 57.2% | 80.3% | -63% |

Hermes 原生 = 33.4% → 83%，提升 2.5 倍。token 省 34%。

## 与 7 层架构的关系

| 7层架构层 | OpenViking 对应 | 说明 |
|-----------|----------------|------|
| L1 Workspace | — | OpenViking 不涉及，CREATIVE.md 继续独立 |
| L2 Sessions | session 间持久化 | OpenViking 跨对话保持，可替代 sqlite 事实库 |
| L3 Structured Facts | 8 类结构化记忆 | OpenViking 自动提取 8 类，比手工 `fact_store.py add` 更省力 |
| L4 Fabric | AGFS 文件系统 | OpenViking 的虚拟文件系统 > 手工维护 fabric 卡片 |
| L5 语义检索 | 内置向量索引 | OpenViking 自带，无需单独维护 Qdrant/TF-IDF |
| L6 LLM Wiki | — | 仍需单独方案 |
| L7 Ground Truth | — | 不受影响 |

## 已知陷阱

- **O(n²)成本陷阱** (Issue #505): 每次 commit 与所有已有记忆做相似度比对，500+ 条后 embedding 成本暴涨。v0.4.x 部分修复但未完全解决。
- **语义队列卡住** (Issue #864): 高并发下语义搜索队列偶发阻塞。
- **许可证**: 主项目 AGPLv3（商业用途注意），CLI 和示例代码 Apache 2.0。
- **需常驻服务**: 不像纯 CLI 工具，需要长期跑 server（CPU 4GB 够）。
