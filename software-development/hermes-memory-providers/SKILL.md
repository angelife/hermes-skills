---
name: hermes-memory-providers
description: "配置 Hermes Agent 外部内存提供商。默认用 hindsight（推荐），不建议用内置 memory。含单 agent 持久化和多 agent 共享记忆两种模式。"
version: 1.0.0
---

# Hermes Memory Providers

## 核心原则

**hindsight > 内置 memory** — 内置 memory 只是 2KB 的文本文件，hindsight 是语义检索+实体图谱+自动 retain/recall 的完整记忆系统。

**hindsight 是舰队共享记忆层** — hindsight 服务设计就是多 bot 共享的。所有 agent 用相同 `bank_id` 指向同一个 hindsight 服务即可实现共享记忆。不要假设 hindsight 是"本地单机"的——先查配置再下结论。

**默认行为**：hindsight 启用后，auto-retain 和 auto-recall 默认开启。不需要手动调用 `memory` 工具。

## 评估替代 Provider 的检查清单

**在提议换掉 hindsight 或加装其他记忆系统之前，必须先回答：**

1. **hindsight 当前是怎么部署的？** 本地 solo？多 bot 共享同一服务？服务在哪台机器？bank_id 策略是什么？
2. **当前方案的瓶颈到底是什么？** 准确率不够？token 太贵？没有跨 bot 共享？——先查配置再下结论，不要猜。
3. **新工具的增量价值是什么？** 如果问题在"召回不高"，先调 hindsight budget 等级再考虑换；如果问题在"没共享"，先确认当前不是共享模式。
4. **新工具部署在哪？** 不要往现有 hindsight 同一台机器上叠——两个记忆系统混在一起导致混乱。

**典型踩坑记录：** 本 session 中，提出 OpenViking 时直接说"hindsight 是本地的，OpenViking 才能共享"——翻历史就知道 hindsight 已经在跑多 bot 共享。正确流程是先查 hindsight 的 `base_url` 和 `bank_id` 配置确认拓扑，再评估新工具是否能带来 hindsight 做不到的。

## 配置 Hindsight

### 单 Agent
```yaml
# ~/.hermes/config.yaml
memory:
  provider: hindsight
  config:
    hindsight:
      api_key: ${HINDSIGHT_API_KEY}
      base_url: http://127.0.0.1:8888  # 本地部署
      bank_id: hermes                    # 记忆库名称
```

`.env` 中加：`HINDSIGHT_API_KEY=none`（本地部署不需要真 key）

### 多 Agent 共享记忆
所有 agent 用相同 `bank_id` 指向同一个 hindsight 服务：
```yaml
memory:
  provider: hindsight
  config:
    hindsight:
      api_key: ${HINDSIGHT_API_KEY}
      base_url: http://192.168.1.8:8888  # 指向土同学的 hindsight
      bank_id: fleet
```

每个 agent 独立配置（不能共享 config）。密钥装了不等于记忆力接上了——必须显式设 `memory.provider: hindsight`。

### 隔离策略
```yaml
# 每个 profile 独立记忆
bank_id_template: "hermes-{profile}"

# 或显式指定
bank_id: hermes-tu   # 土同学专属
bank_id: hermes-jin  # 金同学专属
```

## 验证

```bash
# 检查 provider（注意：'' 或 null = 未启用）
grep -A5 "^memory:" ~/.hermes/config.yaml | grep provider
# 期望：provider: hindsight

# 健康检查
curl -s http://localhost:8888/health
# 期望：{"status":"healthy","database":"connected"}

# 测试回想
curl -s http://127.0.0.1:8888/v1/default/banks/hermes/memories/recall \
  -X POST -d '{"query":"test"}' | python3 -m json.tool

# 查看统计
curl -s http://127.0.0.1:8888/v1/default/banks/hermes/stats | python3 -m json.tool
```

## 记忆防线锁死（夜训/机制锁死常用）

NLM/文章常建议：`mode=local_external` + `auto_retain=true` + **`retain_every_n_turns=10`**（降频降噪）。

**本机实际路径（优先改这里，不是文章里的 `/opt/data/hindsight/...`）：**
- `~/.hermes/hindsight/config.json`
- 同步副本：`~/.hermes-docker/minimaxlab/hindsight/config.json`（若存在）

```json
{
  "mode": "local_external",
  "bank_id": "hermes",
  "recall_budget": "low",
  "memory_mode": "hybrid",
  "auto_retain": true,
  "auto_recall": true,
  "retain_async": true,
  "retain_every_n_turns": 10
}
```

**注意：** 文章路径 `/opt/data/hindsight/config.json` 是容器内路径；Mac 主机侧先改 `~/.hermes/hindsight/config.json`。Docker 容器 `hindsight` 监听 `8888`。

## 关键坑：不要绕开 Hindsight 自建记忆系统

**Hindsight 是唯一指定的记忆层。** 当需要新功能时，扩展 Hindsight 的 API（它有完整 REST API + MCP），不要另起炉灶写自定义 memory server。

| 错误做法 | 正确做法 |
|----------|----------|
| `python3 memory_server.py --port 28083` | 用 Hindsight API 直接存取 |
| 写新 SQLite 表存记忆 | 用 Hindsight 的 observations/entities |
| 造自己的 recall 端点 | 调 `hindsight/v1/.../memories/recall` |

**理由**：Hindsight 有完整的 auto-retain（自动存每轮对话）、auto-recall（自动注入相关记忆）、consolidation pipeline、实体图谱、语义检索——自建平替缺失后四项，且造成 Agent 混乱（该用哪个记忆源？）。
测试：`curl http://127.0.0.1:8888/v1/default/banks/hermes/stats` — Hindsight 活着就别碰记忆层代码。

## 什么不该往 Hindsight 存

**外部内容不进记忆。** Hindsight 是为个人观察/经验/决策/复盘设计的，不是内容仓库。

| ❌ 不要存 | ✅ 可以存 |
|----------|----------|
| 外部文章链接（公众号、博客、新闻） | 个人判断、决策理由、学到的东西 |
| 第三方文档/教程/代码片段 | 遇到的坑、解决方案、验证结果 |
| 别人写的公开内容 | 看文章后的个人思考总结 |
| 批量未处理的数据 | 处理后提炼的结论和模式 |

**正确做法**：对想推荐的文章，问用户"要不要看"。读后有收获再把提炼出的洞察存为 observation，不是整篇文章链接往里倒。

| 症状 | 原因 | 修复 |
|------|------|------|
| `provider: ''` 或 `provider: null` | memory provider 未启用 | 显式设为 `hindsight` |
| `.env` 有 key 但 provider 不生效 | 环境变量 ≠ provider 配置 | 检查 `config.yaml` 中 `memory.provider` |
| auto-retain 不工作 | provider 刚配好，需新会话生效 | 重启 gateway |
| `base_url` 连不上 | 本机 hindsight 没跑，或指向了错误的 IP | `ps aux \| grep hindsight` 检查进程 |
| recall 返回空 | 新 bank_id 还没数据，或 query 不匹配 | 用 `recall` API 检查，而非对话记忆 |
| 多个 agent 记忆不共享 | 每个 agent 的 `memory.provider` 必须独立配置 | 各 agent 分别设 `bank_id: fleet` |

## 其他 Provider（不推荐）

| Provider | 状态 | 理由 |
|----------|------|------|
| mem0 | ⛔ 不推荐 | 依赖外部服务，隐私不可控 |
| honcho | ⛔ 不推荐 | 项目停滞，API 不稳定 |

## 参考
- references/hindsight-config-examples.md — 完整配置示例
- references/auto-retail-behavior.md — auto-retain/recall 行为说明
