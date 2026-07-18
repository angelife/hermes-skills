# Rule Elevation Principle

## Context

During diagnostic work in July 2026, a class of failure was identified: methodology rules that existed in a skill's `references/*.md` file were not being followed because the agent never loaded that specific reference file — despite having loaded the parent skill and seen the reference link.

## The Problem

A SKILL.md can grow large (100KB+). When it does, the agent's reading pattern is:
1. Load the skill with `skill_view(name)`
2. Read the first ~30-50 lines
3. See a reference like `**See**: references/diagnostic-methodology.md`
4. Stop reading (treating "seen the reference" as "the reference is noted")
5. Not follow through to load the reference file

Adding "remember to load references" instructions is **the same failure mode** as the original problem — the rule already existed but wasn't followed. History shows this approach is unreliable.

## The Fix

When a rule in a reference file is important enough that violating it causes real harm:
- **Inline** a short summary of the rule into the parent SKILL.md's first screen
- Keep the full explanation/examples in the reference file
- Change the reference line to signal optional depth, not required prerequisite

This is the "方案2" approach: fix the mechanism, not the instruction.

## Applied to This Skill (`moa-sourcing-rules`)

If `moa-sourcing-rules` grows large and accumulates rules across multiple `references/*.md` files, the same risk applies. Audit periodically: is any rule in a reference file important enough to cause harm if skipped? If so, promote a summary to SKILL.md.
