---
name: upgrade-decision
description: >-
  Structured framework for evaluating whether to upgrade a self-hosted system
  (Hermes Agent, OmniRoute, any tool with custom skills/config/plugins).
  Produces a clean pros/cons table + recommendation, not a wall of speculation.
version: 1.0
---

# Upgrade Decision — Structured Evaluation

## Trigger

User asks "要不要升级" / "升级利弊" / "升不升" / "should we upgrade X" for any system they run with custom modifications (skills, config, state layers, plugins).

## Principles

1. **Frame against what we actually have** — map every claimed improvement to our current version's state. Don't repeat vendor changelogs.
2. **Separate relevance** — table mapping: article claim → our current status → delta → importance to us (⭐ scale).
3. **Cost is real** — config migration, skill API compatibility, downtime window, unknown regressions from accumulated commits. These are NOT "minor concerns."
4. **Recommend a specific target** — "升到 X 止步" not "要不要升". Give a version number or commit range.

## Execution Steps

### 1. Establish baselines

```
<current_ver>  →  hermes --version
<target_ver>   →  hermes update --check  or  git log --oneline origin/main | head -1
<commit_count> →  "N commits behind"
```

### 2. Map article/claims to our state

For each claimed improvement from the article or changelog:

| Claim | Our Version Has It? | Delta | Importance (⭐⭐⭐) |
|-------|-------------------|-------|-------------------|
| feature X | ✅/❌/partial | what changes | why we care or don't |

### 3. Identify relevant stack dependencies

- Custom skills count and complexity (e.g. 50+ skills)
- Config format version (v27→v33 etc.)
- State layer / persistence (Working State, Hindsight, cron jobs)
- Running services (Telegram Gateway, etc.)

### 4. Produce structured output

Format:

```
## 升级利弊

### 利
1. bullet per claimed improvement that's actually relevant
2. ...

### 弊
1. config migration risk
2. skill compatibility
3. downtime window
4. unknown regression from N accumulated commits

### 真实收益评估

| 收益点 | 对我们重要度 | 能否拿到 |
|--------|-----------|--------|
| feature X | ⭐⭐⭐ | ✅ 已在此版本 |

### 建议
[升到具体版本止步] 或 [不升] 或 [等有具体问题再升]
```

### 5. Let user decide

End with "去改吗？" or a summary they can copy to ChatGPT.

### (Optional) Step 6 — Source-level audit for code-backed risk assessment

When the upgrade is for a custom-deployed system (50+ skills, gateway, state persistence, custom providers), and the user wants concrete risk assessment beyond changelog claims:

**6a. Resolve version-to-tag mapping**

hermes --version may report "v0.18.0" while git tags use "v2026.7.1". Resolve before diffing:

```bash
git tag | sort -V
git describe --tags
```

**6b. Check the four critical diff zones**

| Zone | Command | What to look for |
|------|---------|-----------------|
| Config schema | `git diff <from>..<to> -- *config* *migrat*` | migration files, schema version bumps, new required fields, field renames |
| Skill / hook API | `git diff --stat <from>..<to> -- src/hermes_agent/skill/` | zero changes = strong evidence of no breaking API change |
| Session / state lifecycle | `git log --oneline <from>..<to> --grep="session\|memory\|state"` | /new behavior, memory extraction, state persistence changes |
| Telegram / provider | `git log --oneline <from>..<to> --grep="telegram\|provider\|fallback"` | connectivity changes, provider abstraction changes, fallback chain impact |

Also check `git diff --stat <from>..<to> -- config.yaml pyproject.toml locales/ gateway/config.py` for config file churn — these are the files that carry schema version migrations and new required fields.

**6c. Craft audit prompt for external AI**

Structure the prompt as:

1. Source-level data — the actual diff and commit data from step 6b, presented as a compact block
2. Explicit questions — config schema breaking? skill API change? known issues with similar deployments?
3. Required output format

The prompt should force the external AI to check code paths, not give general advice. See `references/upgrade-audit-prompt-template.md` for the canonical template.

### 7. Backup before touching

Order matters — backup in this sequence:

```bash
# 0. Freeze current state with a git tag (for exact reproducibility)
git tag <system>-prod-<current_ver>-before-upgrade
git describe --tags  # confirm

# 1. Config (most likely to be modified by migration)
cp ~/.hermes/config.yaml ~/.hermes/config.yaml.<current_ver>.bak
cp ~/.hermes/.env ~/.hermes/.env.<current_ver>.bak

# 2. State (persistent working state, session state)
cp -a ~/.hermes/state ~/hermes-state-backup-<current_ver>

# 3. Skills (no migration risk but valuable to snapshot)
cp -a ~/.hermes/skills ~/hermes-skills-backup-<current_ver>
```

For large .hermes directories (session DBs, caches), skip `tar czf ~/.hermes` — it times out. Backup by individual asset: config + state + skills as separate `cp -a` operations.

### 8. Upgrade Execution — from backup to operational target

When the user says "去改吧" after the decision phase, execute the upgrade. Do NOT conflate this with the assessment phase.

**8a. Resolve version→tag mapping if not done in Step 6a**

If the user's version string (e.g. "v0.18.0") doesn't match git tag format (e.g. "v2026.7.1"), check `pyproject.toml` or `VERSION` for the actual mapping:

```bash
grep "^version" pyproject.toml      # canonical version string
git tag | sort -V                   # release tags
git describe --tags                 # current position
```

Cross-reference the tagged release's version with `pyproject.toml` — e.g. `v2026.7.1` → `version = "0.18.0"`.

**8b. Stash local patches before switching**

Custom installations may have local edits (provider defaults, platform backoff strategies). Save them:

```bash
git stash push -m "description: patch1, patch2"
```

**8c. Checkout target and create stable branch**

```bash
git fetch --tags origin
git checkout <target_tag>
git checkout -b <system>-<target_ver>-stable
```

**8d. Re-apply local patches**

```bash
git stash pop
```

If conflicts occur:

1. Read the conflict region — understand what changed in the upstream version
2. Merge both changes (upstream's new variable/structure + your local behavior) instead of choosing one
3. Verify with `grep` that your intended values are present
4. Commit as a new patch commit on the stable branch

**8e. Verify the install is using the new code**

```bash
hermes --version
# Should show: v<target_ver> (tag) · upstream <sha> · local <sha> (+N carried commit)
```

**8f. Smoke-test (non-interactive tier)**

Run in order, stop on any failure:

1. **Version check** — `hermes --version` confirms target version
2. **Skill count** — `hermes skills list | grep -c "enabled"` — should be close to pre-upgrade count. Also check: no errors in the skill list output
3. **Config validity** — `hermes config show` — no parse errors, provider/env visible
4. **State file integrity** — read `~/.hermes/state/active/project.yaml` — file is readable, content intact
5. **Gateway status** — `hermes gateway status` — process alive (don't restart it yet)

For the Gateway, verify it's running but **don't restart** during the initial verification — the old process continues on the old code path until explicitly recycled.

**8g. Gateway restart (planned downtime)**

When the user approves, restart the gateway:

```bash
hermes gateway restart
```

Then verify: message in → reply out.

**8h. Rollback**

```bash
cd /path/to/hermes
git checkout <original_branch_or_tag>
rm -rf ~/.hermes/config.yaml ~/.hermes/.env
cp -a ~/hermes-backup-<current_ver>/config.yaml ~/.hermes/
cp -a ~/hermes-backup-<current_ver>/.env ~/.hermes/
# Restore state and skills from backups
hermes gateway restart
```

If the rollback is to exactly the previous tagged commit:

```bash
git checkout <system>-prod-<current_ver>-before-upgrade
hermes gateway restart
```

## Pitfalls

- Don't upgrade past the version that has the improvements we need. HEAD might be 700+ commits past the LTS-like point.
- Don't assume compatibility. Custom skills, config structures, state persistence — these are NOT automatically compatible across a major version gap.
- Don't present options without a recommendation. "升到 0.18.2 止步" is better than "你觉得升到哪个版本好？"
- For users who prefer to ask third-party AI ("我问 ChatGPT 看看"), provide a self-contained summary block they can copy-paste — formatted neutrally, no agent-specific framing.
- When mapping version numbers to git tags, first check `git tag | sort -V` — the user-visible version (e.g. v0.18.0) and the release tag (e.g. v2026.7.1) may be different strings. Running `hermes --version` first tells you what version string the user expects; then cross-reference it in the git tag list. If the tag list has date-based tags (v2026.7.1) but the version string is semver (0.18.0), also check `pyproject.toml` or `VERSION` for the canonical mapping: `grep "^version" pyproject.toml`.
- If skill/hook API directories show zero file changes in the diff, that is strong evidence of no breaking changes — mention it explicitly in the assessment rather than defaulting to "可能有风险". Config/skill/state/telegram are independent risk dimensions; they should each get their own verdict.
- The external AI will say it needs the source repo to give concrete answers — that's correct behaviour, not stalling. Provide the actual diff data so it has something to analyse; don't let it defer to "you'll need to check the codebase".
- After pinning to a specific version, `hermes --version` will show "N commits behind" — this is NOT a sign the upgrade failed. It's expected: you intentionally chose not to chase HEAD. Document this in the handoff so neither you nor the user reads it as a problem later.
- Backup order matters: config first (most likely modified by migration), then state, then skills. This is a three-layer safety net, not a single tarball of the whole .hermes directory.
- Local patches (provider defaults, platform backoff strategies, config overrides) MUST be stashed before switching branches. `git stash pop` will fail with merge conflicts if the target version changed the same files. When conflicts occur, merge both changes (upstream's new structure + your behavior) — don't pick one. Commit the result as a dedicated patch commit on the stable branch so future diffs show exactly what was customised.
- Don't `tar czf ~/.hermes` for backup — the directory contains session DBs and caches that make it slow (30s+ timeout). Use targeted `cp -a` for the three asset types: config files, state directory, skills directory. Each is small enough to copy instantly.

## See also

- `hermes-troubleshooting` — for upgrade fallout diagnosis
- `telegram-gateway` — downtime window planning
- `hermes-provider-config` — post-upgrade provider verification