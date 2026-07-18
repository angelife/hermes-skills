---
name: hermes-runtime-architecture
description: >-
  Hermes Runtime Architecture 设计文档的骨架和核心论点。
  讨论终点：长期 Agent 的连续性来自 Runtime，而不是来自模型的上下文窗口。
version: 1.1.0
---

# Hermes Runtime Architecture

副标题：Persistent Execution Runtime for Long-running AI Agents

## 核心原则

> **LLM 是 Runtime 的推理器，而不是 Runtime 本身。**

> **连续性来自 Runtime，而不是来自模型的上下文窗口。**

## 为什么不是 Memory 文档

讨论经历了一次 paradigm shift：

```
问题：为什么 /new 后会失忆？
  ↓
方案：怎样做长期记忆？
  ↓
本质：长期 Agent 应该如何运行？
```

最终结论：缺的不是 Memory，而是一个独立于模型的 Runtime。

---

## 文档六章结构

### 第一章：为什么 Memory 解决不了长期协作

核心论点：长 Context ≠ 长期协作，更多 Memory ≠ 连续工作。

| 现有方案 | 覆盖什么 | 不覆盖什么 |
|---|---|---|
| SOUL / system prompt | Identity（我是谁） | 不知道在做什么 |
| Skills | Procedural Knowledge（怎么做） | 不知道当前进度 |
| Hindsight / RAG | Retrieval（过去有什么，需主动搜） | 不会自动恢复上下文 |
| Memory KV | 少量事实 | 满即挤，无状态管理 |
| **缺 → Runtime** | **Working State** | **当前目标、阻塞、决策、下一步** |

### 第二章：五类信息模型

五类信息，生命周期不同，不应混在同一个 "Memory" 抽象里：

| 类型 | 生命周期 | 更新频率 |
|---|---|---|
| Identity | 月/年级别 | 极低 |
| Procedural Knowledge | 周/月级别 | 低 |
| Retrieval Memory | 永久 | 中 |
| Working State（三层：Global → Project → Task） | 小时/天/月 | 高 |
| Context Window | 分钟级（每轮） | 每轮 |

### 第三章：Runtime Model（正文核心）

```
Runtime
├── Identity（SOUL / system prompt）
├── Goal Manager（长期目标，独立于具体任务）
├── Scheduler（多任务切换：Runnable / Running / Waiting / Blocked / Finished）
├── State Manager（三层：Global → Project → Task → Conversation）
├── Resource Manager（ADB 连接、SSH、API key、MCP session、Git workspace 等外部资源）
├── Intent Router（判断用户输入相关层级，决定恢复多少 State）
├── Planner（基于当前 State 决策下一步）
├── Executor（执行具体操作）
├── Event Store（Domain Event 模型，非推理过程日志）
├── Snapshot Manager（Working Snapshot + Milestone Snapshot）
├── Archive（已完成项目的 State 归档，只保留结论）
└── LLM（推理引擎，不负责记忆）
```

### 3.5 Two-Dimensional State Space

The Runtime Model above describes a single-agent architecture. In production, the Hermes fleet operates in two orthogonal dimensions:

```
                        ┌─────────────────────────────────────┐
  BREADTH (fleet)       │  hermes-multi-bot-todo              │
  cross-bot             │  _EVENTS.jsonl → _TODO.md           │
  coordination          │  Lock / Claim / Heartbeat / Reconcile│
                        │  Active: git-shared repo             │
                        └──────────────────┬──────────────────┘
                                           │ complementary,
                                           │ not overlapping
                        ┌──────────────────▼──────────────────┐
  DEPTH (per-agent)     │  ~/.hermes/state/                   │
  execution continuity  │  global → project → task            │
                        │  snapshots / events / state-restore │
                        │  Active: v1.0 frozen, observation   │
                        └─────────────────────────────────────┘
```

| Dimension | Scope | Purpose | Storage | Recovery |
|-----------|-------|---------|---------|----------|
| **Depth** | Per-bot | Execution continuity, decisions, blockers | `~/.hermes/state/` local | `state-restore` on `/new` |
| **Breadth** | Fleet | Task coordination, who does what | `_EVENTS.jsonl` + `_TODO.md` shared | git clone + reconcile |

The two layers do not overlap:
- **Depth** answers "where am I in my work" (execution context, cross-session)
- **Breadth** answers "who is doing what across the fleet" (task allocation, cross-bot)

Both are needed for a fully continuous agent fleet. A future v2.0 could connect them — for example, a "task claimed" event in the shared TODO could signal a working state transition in the per-bot state.

### 第四章：State 生命周期

```
Create → Update → Checkpoint → Merge → Split → Archive → Delete + TTL
```

State 不是永久保存。做完的项目归档，只保留结论，删除 Working State。

三层 State（Global / Project / Task）各有独立生命周期。

### 第五章：启动流程（新 /new 后的恢复）

```
User Input
    ↓
Intent Router ──→ 判断相关性层级（Level 0-4）
    ↓
Load Identity
    ↓
Load Global Snapshot（用户全局偏好）
    ↓
Load Project Snapshot（若相关）
    ↓
Load Task Snapshot（若相关）
    ↓
Recall on Demand（Hindsight 按需查，不提前灌）
    ↓
Planner
    ↓
Executor
```

Level 0 = 无需恢复（写诗）；Level 4 = 完整恢复 + Hindsight recall。

### 第六章：为什么这不是 RAG

| 问题 | RAG | Runtime |
|---|---|---|
| 找回历史 | ✅ | 可调用 RAG |
| 恢复工作状态 | ❌ | ✅ |
| 保存目标 | ❌ | ✅ |
| 保存任务进度 | ❌ | ✅ |
| 调度多个项目 | ❌ | ✅ |
| 生命周期管理 | ❌ | ✅ |

## Event 模型

采用 Domain Event 模式，不是推理过程日志：

```
GoalCreated
TaskStarted / TaskPaused / TaskResumed / TaskCompleted
DecisionRecorded
PreferenceUpdated
ResourceAllocated / ResourceReleased
FailureDetected
HypothesisRejected
SnapshotCreated / Archived
```

Event Log → Periodic Checkpoint → 保留 Milestone Snapshot。

## Snapshot 分两种

- **Working Snapshot**：高频（例如每 5 分钟），用于 crash 恢复，可丢弃
- **Milestone Snapshot**：任务完成 / 重大决策时生成，永久保存

## 最终设计原则

> **长期 Agent 不应被建模为"一次次独立的对话"，而应被建模为"一个持续运行的系统"。在这个系统中，Identity 定义主体，Goal 定义方向，State 描述当前执行位置，Scheduler 管理任务切换，Event Log 记录演化过程，Snapshot 提供恢复点，而 LLM 只是负责在当前 Runtime 状态下进行推理。模型可以更换、上下文可以清空、会话可以重建，但 Runtime 保持连续，因此协作也保持连续。**

## 参考讨论

- 起点：cua-driver 空闲高 CPU 诊断（Hermes Agent lifecycle 缺陷）
- 中间：从 "Hermes 没在不用时关掉子进程" 到 "缺 Session State 层"
- 终点：Agent OS 架构，以 Runtime 为中心而非以 LLM 为中心
