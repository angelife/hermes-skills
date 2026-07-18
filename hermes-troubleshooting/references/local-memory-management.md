# Local Memory Management

## Overview

Hermes Agent has two local memory stores:
- `memory` target: ~2,200 characters
- `user` target: ~1,375 characters

These are plain text files (not a database). When full, `memory(action='add')` may silently fail. You must use `action='replace'` to update existing entries or free space.

## Symptoms of Full Memory

- Usage bar shows near-100% (e.g. `"95% — 2,108/2,200 chars"`)
- `memory(action='add')` returns error or the entry count doesn't increase
- You can't add new durable facts without losing old ones

## Management Strategy

### When memory is full

1. **Prioritize**: Identify the least important entry — old task state, resolved issues, transient environment facts (not user preferences, architecture decisions, or stable conventions)
2. **Replace**: Use `memory(action='replace', target='memory', old_text='<unique substring>', content='new value')` — this updates in place without increasing total size
3. **Consolidate**: Merge multiple related entries into one. For example, combine several small entries about environment details into a single entry

### What belongs in each store

| Store | Good fit | Bad fit |
|-------|----------|---------|
| `memory` | Architecture decisions, project conventions, tool quirks, persistent deployment patterns, API endpoints | Task progress, session outcomes, TODO lists (use `todo` tool) |
| `user` | Communication preferences, recurring corrections, role/identity | One-off instructions, session-specific context |

### Relationship with hindsight shared memory

Local memory is **NOT shared** between agents. It's per-instance. For shared knowledge across multiple Hermes instances (e.g. 土/木/金), use hindsight:

- **hindsight** (`hindsight_retain`, `hindsight_recall`): Shared across instances with same `bank_id`. Automatically retains after each turn.
- **local memory** (`memory`): Per-instance, manual, 2KB cap.

When both are configured, prefer hindsight for persistent knowledge and local memory for session-scoped preferences and identity anchors.

### Prevention

- Periodically audit and prune: remove entries older than 30 days, session completions, and resolved issues
- Use `hindsight_retain` for durable shared knowledge instead of `memory`
- Keep local memory focused on facts that **prevent user corrections across sessions** (user preferences, recurring task patterns, environment invariants)
