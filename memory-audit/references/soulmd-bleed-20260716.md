# SOUL.md Bleed — 2026-07-16 Case Study

## Context

Day 4 of memory audit (observation phase). MEMORY.md had grown to 3679 chars / 21 entries (167% of 2200 target) — worsening from Day 3's 3196 chars (145%).

## Discovery

8 out of 21 MEMORY entries were direct extractions from SOUL.md rules:

| Entry | Source | Chars |
|-------|--------|-------|
| 先问AI再动手 | SOUL.md 行动原则 → 先问AI | 128 |
| 核心工作流：先查已有 | SOUL.md → 收敛原则 | 173 |
| 少就是多，宁缺毋滥 | SOUL.md → 收敛原则 | 109 |
| NIGHT WORK | SOUL.md → 昼夜分工 | 155 |
| THREE-STRIKES | SOUL.md → 三次规则 | 75 |
| MECHANISM OVER RULES | SOUL.md → 强制前检 | 181 |
| KNOWLEDGE SYSTEM | SOUL.md 技能体系？ | 128 |
| WORKING CONDITIONS | SOUL.md → 不可变规则？ | 120 |

**Total: 1069 chars / 29% of all MEMORY content** — all duplicating SOUL.md which is permanently injected into every system prompt.

## Root Cause

The mechanism that copies SOUL.md into memory doesn't have a "does this already exist in SOUL.md" guard. Each time a new session loads SOUL.md and sees a useful rule, it writes it as a new memory entry. No mechanism checks if this exact rule is already permanently available in the system prompt.

## Detection Signature

- MEMORY entries are all `[PREF]` classification
- Each entry maps 1:1 to a SOUL.md section heading or rule
- Entries are single, standalone principles (not environment facts or tech configs)
- Character count climbs without adding new information

## Recommended Fix

Mark all SOUL.md-derived entries as `[建议删除]` during audit. SOUL.md is always injected — memory should only hold *environment facts* and *user-specific deviations/interpretations* of those rules, not the rules themselves.

## Related

- Day 4 audit log: `memory-audit-20260716.txt`
- Same pattern may affect `daily-journal` — its SOUL.md re-read ritual may be the source of memory writes