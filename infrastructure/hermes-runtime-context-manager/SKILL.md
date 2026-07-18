---
name: hermes-runtime-context-manager
version: "1.0"
description: "Hermes Runtime v2 Context Manager — injects shared context into delegate_task calls so child agents inherit project/task state and hindsight memories"
capabilities:
  - generate shared context from project.yaml + task.yaml + hindsight memories
  - inject context into delegate_task calls
  - format context for child agent consumption
triggers:
  - before any delegate_task call
  - when user asks to "share context" or "sync state"
---

# Hermes Runtime Context Manager

Injects shared context into `delegate_task` calls so child agents inherit project/task state and hindsight memories.

## Usage

### 1. Generate shared context

```bash
python3 ~/.hermes/scripts/context_manager.py inject
```

Outputs a markdown-formatted shared context block containing:
- Project name, status, goal
- Current task and blockers
- Next actions
- Recent decisions
- Hindsight memory summary

### 2. Inject into delegate_task

When calling `delegate_task`, append the shared context to the `context` parameter:

```python
# Get shared context
import subprocess, json
result = subprocess.run(
    ["python3", "~/.hermes/scripts/context_manager.py", "inject"],
    capture_output=True, text=True
)
shared_ctx = result.stdout

# Pass to delegate_task
delegate_task(
    goal="...",
    context=f"{shared_ctx}\n\n---\n\nTask-specific context here..."
)
```

### 3. Register a skill's capabilities

```bash
python3 ~/.hermes/scripts/capability_registry.py register <skill-name> \
  --caps '["capability1", "capability2"]' \
  --desc "Description" --version "1.0"
```

### 4. Find skills by capability

```bash
python3 ~/.hermes/scripts/capability_registry.py find "context"
```

### 5. Generate capability map

```bash
python3 ~/.hermes/scripts/capability_registry.py map
```

## Pitfalls

- `context_manager.py inject` reads from `~/.hermes/state/active/` — ensure project.yaml and task.yaml exist before calling
- Capability Registry is file-based (YAML), not a DB — concurrent writes from multiple agents could race. Use `register` sequentially.
- Event Bus events persist to disk — clean up `~/.hermes/runtime/events/history/` periodically
- The `scan` command only discovers skills with `capabilities:` in their SKILL.md frontmatter — most existing skills won't have this yet