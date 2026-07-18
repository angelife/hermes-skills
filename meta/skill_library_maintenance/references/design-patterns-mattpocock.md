# Matt Pocock Skill Design Patterns

Source: [mattpocock/skills](https://github.com/mattpocock/skills) (160K⭐) — "Skills for Real Engineers."

## Pattern 1: disable-model-invocation

Add `disable-model-invocation: true` in frontmatter for **pure-execution skills** that should ONLY run when explicitly loaded, NOT participate in autotrigger.

```yaml
---
name: my-pure-execution-skill
description: "Use when X needs Y"
disable-model-invocation: true
---
```

**Applied to (this fleet):** moa-sourcing-rules, state-restore, state-save, reporting-and-handover-style, health-diagnosis-workflow, environment-assessment, shared-reporting-handoff, shared-bot-healthcheck, angelife-minimal-execution-style, angelife-mobile-remote-workflow.

## Pattern 2: Compositional Chain

Entry-point skills are tiny (<500B) and delegate to sub-skills:

```
grill-with-docs  (245B)  →  /domain-modeling
to-spec          (3KB)   →  produces PRD
to-tickets       (5.8KB) →  vertical slices
implement        (433B)  →  /tdd → /code-review
code-review      (6.7KB) →  parallel sub-agents
```

## Pattern 3: Template-Driven Output

Structured PRD template (from to-spec):

```
## Problem Statement
## Solution
## User Stories (As a <role>, I want <feature>, so that <benefit>)
## Implementation Decisions ({choice} — {rationale})
## Testing Decisions ({what} at {which seam})
## Out of Scope
```

## Pattern 4: Two-Axis Independent Review

Run Standards and Spec review as **parallel sub-agents** → report side-by-side, never merged. Prevents one axis masking the other.

## Pattern 5: Vertical Slicing

Tracer-bullet tickets: each cuts complete path (schema→API→UI→tests), independently demoable, with explicit "Blocked by" edges.
