---
name: kanban-workflow
description: "Hermes Kanban 操作规范 — 初始化、任务链、状态机、模式库（P1-P8）、双机协作、故障排除。适用任何需要跨 Agent 协作、持久任务队列、人类介入审批的场景。"
category: workflow
---

# Hermes Kanban Workflow

> **Trigger**: 用户提到"看板""Kanban""任务接力""多Agent协作""P1流水线""P2链式"等关键词。
> **Core principle**: Kanban 是持久化工作队列，不是函数调用。任务状态自动流转，失败可恢复，人类可介入。

## Environment

- Kanban DB: `~/.hermes/kanban.db` (SQLite, per-machine)
- Gateway 必须运行（dispatcher 在 gateway 里，每 60s 扫板）
- Dispatcher 自动分解任务为子任务，自动推进依赖链

## Common Commands

| Action | Command |
|--------|---------|
| Initialize | `hermes kanban init` |
| Create task | `hermes kanban create "title" --assignee default [--body "..."] [--triage]` |
| Create with parent | `hermes kanban create "title" --parent T_PARENT_ID` |
| List board | `hermes kanban list` (◻=todo, ▶=ready, ●=running, ✓=done, ?=triage, ⊘=blocked) |
| Promote task | `hermes kanban promote T_ID [--force]` (force bypasses dependency check) |
| Block task | `hermes kanban block T_ID "reason" --kind needs_input` |
| Unblock | `hermes kanban unblock T_ID` |
| Comment | `hermes kanban comment T_ID "text"` |
| Link tasks | `hermes kanban link T_CHILD --parent T_PARENT` |
| Archive | `hermes kanban archive T_ID` |
| Watch live | `hermes kanban watch` |
| Dashboard | `hermes dashboard` |

## Task Lifecycle

```
triage → todo → ready → running → blocked → done / archived
  ↑          ↓
specify   promote --force
```

- **triage**: 需要 specifier 完善描述, 手动 `promote --force` 解放
- **todo**: 等待依赖链上游完成
- **ready**: dispatcher 可接管
- **running**: 正在被 agent 执行，配 workspace 目录
- **blocked**: 卡住等人或依赖 (⊘ 符号)
- **done**: 完成，有产出物

## 8 种协作模式（P1-P8）

| # | Mode | Shape | Use case |
|---|------|-------|----------|
| P1 | Fan-out | 1→N | 并行研究/编码 |
| P2 | Pipeline | A→B→C | 链式角色接力 |
| P3 | Voting | N→1 | 多视角评审 |
| P4 | Journal | 时间累积 | 每日简报/周报 |
| P5 | Human-loop | 阻塞+决策 | 关键决策卡人 |
| P6 | @mention | 主动 escalate | 跨域协作 |
| P7 | Thread ws | 隔离 workspace | 多群并行 |
| P8 | Fleet | 1×N | 集群批量任务 |

> P1 + P2 + P5 cover 90% 场景。

## Cross-Machine Kanban (multi-agent)

- Each Hermes instance has its own separate `kanban.db` (per-machine SQLite, not shared)
- For multi-machine Kanban, the DB needs to be on a shared filesystem or use a network backplane
- To demonstrate cross-machine participation:
  1. SSH into each machine (`ssh macos@192.168.1.23`)
  2. Initialize Kanban on each (`hermes kanban init`)
  3. Create tasks on each machine independently
  4. Show concrete evidence: different CPU architectures, uptimes, produced artifacts

## Pitfalls

- ❌ `hermes kanban update` does NOT exist — use `promote` / `unblock` / `complete`
- ❌ `--reason` is NOT a flag on block — it's a positional argument: `kanban block T_ID "reason"`
- ❌ Parent task in `triage` blocks children from being promoted — use `--force` to override
- ❌ `specify` requires LLM — if LLM unavailable, promote directly with `--force`
- ❌ Tasks in `triage` can't be scheduled directly — promote to `todo` first
- ⚠️ Gateways on different machines have independent dispatchers — no shared scheduling

## Verification

```bash
hermes kanban list        # 看全板
hermes kanban log T_ID    # 看执行日志
hermes kanban runs T_ID   # 看运行历史
curl localhost:8420/health  # Gateway 状态
```
