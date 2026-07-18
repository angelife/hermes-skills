---
name: kanban
description: "Hermes Kanban multi-agent workflow — orchestration routing, worker lifecycle, pitfalls, and recovery. Covers both the orchestrator role (task decomposition, fan-out, dependency linking) and the worker role (handoffs, blocks, retries, workspace handling)."
version: 4.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
environments: [kanban]
metadata:
  hermes:
    tags: [kanban, multi-agent, orchestration, workflow, collaboration, routing]
---

# Kanban Multi-Agent Workflow

The Hermes Kanban system manages cross-profile task routing, execution, and handoffs. This umbrella covers both the **orchestrator** role (decomposing requests into tasks, linking dependencies, routing to specialists) and the **worker** role (executing a claimed task, writing durable handoffs, recovery).

---

## Core Lifecycle (auto-injected as KANBAN_GUIDANCE)

Every kanban worker gets a 6-step lifecycle in their system prompt:
1. **Orient** — `kanban_show` to read task body + parent handoffs
2. **Plan** — decide approach within the workspace
3. **Work** — use tools to produce output
4. **Heartbeat** — optional progress signals for long tasks
5. **Block** or **Complete** — hand off to a reviewer or mark done
6. **Summary** — structured metadata for downstream consumers

---

## 1. Orchestrator Role

**Full reference**: `references/orchestrator.md`

### When to use the board (vs. doing work directly)

Create Kanban tasks when:
- Multiple specialists are needed (research + analysis + writing)
- Work should survive crash/restart
- The user may want to interject (human-in-the-loop)
- Multiple subtasks can run in parallel
- Review/iteration is expected
- The audit trail matters

### Key Rules

1. **Discover available profiles first** — `hermes profile list` or ask the user. The dispatcher silently fails on unknown assignee names.
2. **Decompose, don't execute** — create tasks for the right specialists, don't do the work yourself.
3. **Split multi-lane requests** — each independent workstream gets its own card.
4. **Link dependencies properly** — pass `parents=[...]` in `kanban_create`.
5. **Create parents first**, capture their IDs, pass to children.
6. **Run independent lanes in parallel** — don't link cards that don't need each other's output.

### Task Graph Pattern

```
Research-A ──┐
              ├── Synthesize ──► Prose Draft
Research-B ──┘
```

### Goal-mode cards
For open-ended tasks: `kanban_create(title="...", goal_mode=True, goal_max_turns=15)` wraps the worker in a judge loop that keeps running until acceptance criteria are met.

---

## 2. Worker Role

**Full reference**: `references/worker.md`

### Workspace Kinds

| Kind | Behavior |
|------|----------|
| `scratch` | Fresh tmp dir, GC'd on archive |
| `dir:<path>` | Shared persistent directory |
| `worktree` | Git worktree at resolved path |

### Good Handoff Patterns

**Coding task:**
```python
kanban_complete(
    summary="shipped rate limiter — token bucket, 14 tests pass",
    metadata={"changed_files": ["rate_limiter.py", "tests/test_rate_limiter.py"],
              "tests_run": 14, "tests_passed": 14}
)
```

**Review-required tasks:** Use `kanban_comment()` for structured data + `kanban_block(reason="review-required: ...")` instead of complete.

**Research task:**
```python
kanban_complete(
    summary="3 libraries reviewed; vLLM wins on throughput",
    metadata={"sources_read": 12, "recommendation": "vLLM"}
)
```

### Heartbeats
Good: `"epoch 12/50, loss 0.31"`, `"scanned 1.2M rows"`. Bad: `"still working"`. Every few minutes max.

### Block Reasons That Get Answered Fast
Bad: `"stuck"`. Good: `"Rate limit key choice: IP (simple, NAT-unsafe) or user_id (requires auth)?"`
Leave longer context in a `kanban_comment()`.

### Retry Diagnostics

| Outcome | Meaning |
|---------|---------|
| `timed_out` | Hit max runtime — chunk or shorten work |
| `crashed` | OOM/segfault — reduce memory |
| `spawn_failed` | Usually credential/config issue — ask human |
| `reclaimed` | Task was archived — check status before proceeding |

### Worker Anti-Patterns

- Do NOT call `delegate_task` as a substitute for `kanban_create`
- Do NOT call `clarify` (headless — use `kanban_block`)
- Do NOT modify files outside `$HERMES_KANBAN_WORKSPACE` unless task body says to
- Do NOT complete a task you didn't finish — block it instead
- Do NOT invent `task_id`s in `created_cards` — only list captured return values

### Claiming Created Cards
Only list IDs you captured from a successful `kanban_create` return value. The kernel verifies each ID exists and was created by your profile.

---

## 3. Recovery

When a worker profile keeps crashing:
1. **Reclaim** — abort the running worker, reset to `ready`
2. **Reassign** — switch to a different profile
3. **Change profile model** — edit profile config, then reclaim

Hallucination warnings appear when `kanban_complete(created_cards=[...])` lists IDs that don't exist or weren't created by this profile.

---

## 4. Notification Routing

Configure cross-profile Kanban task notifications:
```yaml
notification_sources: ['*']          # All profiles
notification_sources: ['default', 'work']  # Specific profiles
```

---

## 5. CLI Fallback

Every tool has a CLI equivalent:
- `kanban_complete` ↔ `hermes kanban complete <id> --summary "..." --metadata '{}'`
- `kanban_block` ↔ `hermes kanban block <id> "reason"`
- `kanban_create` ↔ `hermes kanban create "title" --assignee <profile>`
