---
name: skill_library_maintenance
description: Skill for reviewing conversations and updating the Hermes skill library based on user signals.
---
# Library Maintenance Skill

This skill records the **procedure for reviewing a conversation and updating the Hermes skill library** in response to user signals. It is intended to be used by any agent whose task involves library maintenance, ensuring consistent handling of corrections, workflow changes, and new techniques.

## Signals that trigger a library update
- **Style / tone / format corrections** (`stop doing X`, `this is too verbose`, `just give me the answer`, `you always do Y and I hate it`).
- **Workflow or sequence corrections** (user corrected the order of steps, pointed out missing steps, or demanded a different approach).
- **Emergence of a non‑trivial technique, workaround, or debugging pattern** that a future session could reuse.
- **Discovery that a loaded or consulted skill is wrong, incomplete, or outdated** (needs patching).

## Preferred update flow (class‑level actions)
1. **Update a currently‑loaded skill** – Patch the skill that was just used (via `skill_manage action='patch'`).  
2. **Update an existing umbrella skill** – If no loaded skill covers the domain, patch the relevant class‑level skill (found via `skills_list`).  
3. **Add a support file** under an existing umbrella:  
   - `references/` – session‑specific markdown (error transcripts, reproduction recipes, domain excerpts).  
   - `templates/` – starter files (configs, scaffolding).  
   - `scripts/` – reusable static scripts (verification, probe, fixture generation).  
   *Add a one‑line pointer to any new support file in the skill’s `SKILL.md`.*  
4. **Create a new class‑level umbrella skill** – Only when no existing skill covers the class. The name must be at the class level (e.g., `skill_library_maintenance`) and not a one‑off PR number or error string.

## A meta-rule about rule minting (most-violated, frequently self-violated)

When you write ("patch in") a new rule into a skill — especially rules of the form "every X must do Y" or "no X without Y" — there is almost always one **in-flight instance** of the rule being violated at that exact moment. The previous transcript usually has it sitting right there, and the instinct is to either:

(a) silently exempt the in-flight instance ("this time is fine, rules start next time")
(b) defer the cost ("write now, comply later")

Both are post-hoc rationalizations. The user will almost certainly catch them, because the new rule's first test is the in-flight case — that's where the rule either proves itself or becomes decoration.

**Correct procedure — instant decision needed, three paths:**

1. **Retroactive apply (default):** the new rule takes effect NOW. For the in-flight item, do the rule's required step *before* continuing the modifying action — e.g. before rewriting a report, build the version-changelog; before deleting an entry, decide its disposition and write it down. Cost is one preparation step, but the rule stays credible.
2. **Explicit transition-period exemption:** if retroactive apply is materially costly or carries risk of *more* damage (e.g., the in-flight case is too tangled to safely capture), state the exemption in the same patch: "this is a one-time cold-start exception; from the next item onward the rule is hard." Don't dress it up as "I'll patch it later" — write the exemption so future agents see it.
3. **Roll back the rule:** if the first two options would have been needed, the rule itself may be wrong. Minting a rule you immediately can't follow is itself a signal.

**Pitfall:** option (a) and (b) are the most common and the most likely to draw a correction. Default to (1). Only choose (2) with visible labeling; (3) is rare but real.

## A meta-rule about pre-minting verification (most-violated #2)

Before adding a new rule to any skill (especially rules of the form "causal speculation must be labeled" or "no fabricated numbers"), **first check whether the library already has that rule**.

Procedure:

1. **Search the skill library** — grep pattern across all SKILL.md + references/ for keywords related to the proposed rule (e.g., "causal", "speculation", "未验证", "推测").
2. **Check diagnostic-methodology.md** (if troubleshooting-adjacent) — this reference file in `hermes-troubleshooting` is the canonical home for diagnostic-reporting rules. Duplicating its content elsewhere creates stale forks.
3. **Only mint if gap confirmed** — if the existing rule is worded differently, decide: is the gap in *coverage* (missing rule) or *retrieval* (rule exists but wasn't followed)? Only the former warrants a new rule. The latter warrants placement changes, not content creation.

**Violation signal:** your proposed rule text reads like it's already in the library, just with different wording. If you have to rephrase to avoid sounding identical to an existing entry, you're creating a duplicate.

**Corrective:** instead of adding a new rule, either:
- Cross-reference the existing rule (add a one-line `**See also**: ...` pointer) if it's in a different skill.
- Move the existing rule to a more visible position in its own skill (see "priority-based placement" below) if it was being missed.
- Consolidate: if the same rule lives in two places with different wording, merge into one and redirect the other.

## A principle about rule placement (priority beats discoverability)

**Pitfall:** writing a rule and then hiding it behind a reference that the agent has to actively choose to follow.

The most common failure pattern is: rule written in a `references/*.md` file → SKILL.md has a "See: references/foo.md" line → agent reads SKILL.md first screen only, never scrolls to the reference line, misses the rule entirely. This exact failure happened when `references/diagnostic-methodology.md` (5 high-priority rules) was cited on line 19 of a 1762-line SKILL.md — the reference was present but invisible to a reader who hadn't been told to load it separately.

**Principle: first-screen is the new first-priority.** A rule that must not be missed goes directly in the SKILL.md body, in a section visible within the first 50 lines. The reference file then becomes supplementary (examples, expanded cases) rather than primary.

**Correct procedure when a rule exists only in a reference file:**

1. **Extract the core rule** (one sentence per rule) into the parent SKILL.md.
2. **Rewrite the reference line** from "See: ref.md — these are the 5 rules" to "Full expanded examples in: ref.md".
3. Verify the rule is now visible in skill_view(first_screen) without needing to load the reference.

**Counterpoint — when to keep a rule only in a reference file:** if the rule is a complex verification procedure (10+ step checklist, full diagnostic script, protocol with example transcripts) that would bloat SKILL.md past 70KB. The decision is asymmetric: short, hard rules (≤3 lines each) always live in SKILL.md; long verification procedures can stay in references/ (but the SKILL.md should still have a one-line reminder of what the procedure exists for).

## A note about skill size

A SKILL.md over ~60KB (~1000 lines) starts to hide critical content. The `hermes-troubleshooting` skill was 101KB/1762 lines, and its reference to `diagnostic-methodology.md` was on line 19 — but the file was so long that screen-level skimming stopped before reaching potential follow-up content, and the reference line itself was only one line in a long list of symptom headings.

**Mitigations:**
- Hard, short rules → front-load into first 50 lines (see priority-based placement above).
- Long verification checklists → references/ directory, with a prominent one-line pointer in SKILL.md.
- When a skill regularly exceeds 60KB, consider splitting into sub-skills (e.g., `hermes-troubleshooting-telegram`, `hermes-troubleshooting-providers`) and having the umbrella skill load all sub-skills. This is a restructuring decision, not a format preference — only do it when the navigation burden is confirmed (user or agent missing content that was in the skill).

## How to patch a skill
- Use `skill_manage action='patch'` with `old_string` and `new_string` that reflect the correction.
- Include a **pitfall** section that warns future agents about the trap.
- Before writing, **show a preview of the insertion point** (surrounding ±10 lines) unless trivial.
- After writing, **verify integrity**: `ls -la` (file exists), `wc -c` (size reasonable), then read back the written section to confirm no truncation or format corruption.
- If the skill did not exist, create it with `action='create'` and add it to the appropriate category.

## Example: Updating this very skill
During the current session the user asked to “Review the conversation above and update the skill library.”  
The appropriate response is to **create a new class‑level skill** named `skill_library_maintenance` and document the signal‑driven update process. This skill should also contain a reference file (`references/conversation_update_guide.md`) that captures the exact steps taken in this session.

---

### Adding a reference file
A file can be added under the skill’s directory using `skill_manage action='write_file'` with `file_path` set to a path beginning with `references/`, `templates/`, or `scripts/`. Example:

```
skill_manage action='write_file' name='skill_library_maintenance' file_path='references/conversation_update_guide.md' file_content='<markdown content>'
```

The reference file should be concise, storing only the actionable guide (e.g., the Signal checklist, Patch Flowchart, and any session‑specific notes). It is linked from the skill’s `SKILL.md` so future agents can discover it easily.

---

**End of Skill Documentation**

## 参考文件
- `references/conversation_update_guide.md` — 会话审查与 skill 更新流程
- `references/skill-evaluation-methodology.md` — Skill 触发率与输出质量评估方法（含测试集设计、指标计算、修补闭环）
- `references/distillation-methodology.md` — Skill 蒸馏方法（将 ~800 行过胖 skill 压缩到 ~100 行的操作步骤，含合并/归档/生命周期标签）
- `references/design-patterns-mattpocock.md` — Matt Pocock Skill 设计模式
- `references/pruning-philosophy.md` — 技能精简哲学：少即是多，不用=不存在（2026-07-15 用户确立）