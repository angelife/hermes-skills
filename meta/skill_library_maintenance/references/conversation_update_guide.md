---
title: Conversation Update Guide
---
# Conversation Update Guide

This reference captures the exact steps taken to review the chat transcript and update the skill library accordingly.

## 1. Signal Detection
- **Style/Tone Corrections**: User explicitly asked to “Review the conversation above and update the skill library.”
- **Meta‑task Request**: Needed a reusable Procedure for library maintenance.

## 2. Update Flow Chosen
1. **Create a new class‑level skill** named `skill_library_maintenance`.
2. **Write comprehensive SKILL.md** documenting:
   - Signal categories.
   - Preferred update flow (update loaded skill → update umbrella → add support file → create new umbrella).
   - Patch instructions and pitfall warnings.
3. **Add a reference file** `references/conversation_update_guide.md` that logs this process.

## 3. Files Created
- **Skill**: `meta/skill_library_maintenance/SKILL.md`
- **Reference**: `meta/skill_library_maintenance/references/conversation_update_guide.md`

## 4. Future Usage
- Load the skill via `skill_view(name='skill_library_maintenance')`.
- Consult `references/conversation_update_guide.md` whenever a library update is needed.
- When a new signal appears, follow the flowchart in the SKILL.md to decide which update path to take.