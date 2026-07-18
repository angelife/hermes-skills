---
name: github-workflow
description: "Full GitHub lifecycle from Hermes — auth setup, repository management, issues, PR workflows, code review, and content archaeology. One umbrella for all `gh` CLI operations."
version: 2.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [github, git, PR, code-review, issues, auth, workflow, gh-cli]
    related_skills: [git-content-archaeology]
---

# GitHub Workflow – Complete Lifecycle

Covers the full GitHub operation lifecycle from Hermes: authentication → repository management → issues → pull requests → code review → content recovery.

All operations use the `gh` CLI. Authentication must be configured first (see §1).

---

## Quick Reference

| Operation | Tool | See Section |
|-----------|------|-------------|
| Auth setup | `gh auth login` / SSH keys | §1 Auth |
| Create repo | `gh repo create` | §2 Repos |
| Clone/fork | `gh repo clone` / `gh repo fork` | §2 Repos |
| Manage issues | `gh issue create/list/view/close` | §3 Issues |
| Branch + PR | `gh pr create` / `gh workflow run` | §4 PR Workflow |
| Review PR | `gh pr diff` / `gh pr review` | §5 Code Review |
| Find deleted files | `git log --diff-filter=D` | §6 Archaeology |
| Publish quick ref | `gh gist create` | references/gist-publishing.md |

---

## §1 — Authentication

**Reference**: `references/github-auth.md`

### Prerequisites

```bash
# Install gh if missing
brew install gh  # macOS
sudo apt install gh  # Linux

# Login
gh auth login

# Verify
gh auth status
```

### HTTPS vs SSH

| Method | Setup | Works Anywhere? |
|--------|-------|-----------------|
| HTTPS + token | `gh auth login` with token | Yes (no SSH port concerns) |
| SSH key | `ssh-keygen -t ed25519` → upload to GitHub | No (blocked on some corporate networks) |

### Token scopes needed

- `repo` (full control of private repos)
- `workflow` (to trigger Actions)
- `read:org` (org-level access)
- `admin:public_key` / `write:public_key` (SSH key management)

---

## §2 — Repository Management

**Reference**: `references/github-repo-management.md`

### Clone

```bash
gh repo clone owner/repo
gh repo clone owner/repo -- --depth 1    # shallow clone (CI/cache)
```

### Create

```bash
gh repo create my-project --public --clone
gh repo create my-project --private --template owner/template-repo
gh repo create my-project --internal --push --remote upstream --source .
```

### Fork

```bash
gh repo fork owner/repo --clone
gh repo fork owner/repo --clone=false   # fork without cloning
```

### Releases

```bash
gh release create v1.0.0 --title "v1.0.0" --notes "Release notes"
gh release upload v1.0.0 build.zip
gh release list --limit 5
```

### Secrets & Variables

```bash
gh secret set MY_SECRET --body "$(cat key.txt)"
gh variable set MY_VAR --body "value"
```

### Actions

```bash
gh workflow run build.yml --ref main
gh run list --limit 5 --workflow=build.yml
gh run watch <run-id>
```

### Force Push / Rollback

See `references/force-push-rollback-diagnosis.md` for recovery scripts.

---

## §3 — Issues

**Reference**: `references/github-issues.md`

### Create

```bash
gh issue create --title "Bug: login fails on Safari" \
  --label "bug" \
  --assignee "@me" \
  --project "Q3 Sprint" \
  --body "$(cat /tmp/issue-body.md)"
```

Create from template:
```bash
gh issue create --label "bug" --body-file ~/.hermes/skills/github-workflow/templates/bug-report.md
gh issue create --label "enhancement" --body-file ~/.hermes/skills/github-workflow/templates/feature-request.md
```

### List & Search

```bash
gh issue list --label "bug" --state open --limit 20
gh issue list --assignee "@me" --state open
gh issue list --search "crash in:title,body"
```

### View & Close

```bash
gh issue view 123
gh issue close 123 --comment "Fixed in #456"
gh issue reopen 123
```

### Triage

```bash
gh issue label 123 "needs-triage"
gh issue edit 123 --add-label "priority/high" --remove-label "needs-triage"
gh issue comment 123 --body "Can you provide reproduction steps?"
```

---

## §4 — Pull Request Workflow

**Reference**: `references/github-pr-workflow.md`

### Branch + Commit

```bash
git checkout -b feat/my-feature
git add . && git commit -m "feat: implement my feature"
```

Uses Conventional Commits prefixes: `feat:`, `fix:`, `refactor:`, `docs:`, `test:`, `chore:`, `perf:`, `style:`, `build:`, `ci:`, `revert:`.

### Create PR

```bash
gh pr create --title "feat: implement my feature" \
  --body "$(cat ~/.hermes/skills/github-workflow/templates/pr-body-feature.md)" \
  --base main \
  --label "needs-review"
```

### CI Integration

```bash
gh workflow run ci.yml --ref feat/my-feature
gh run watch $(gh run list --workflow=ci.yml --branch feat/my-feature --json databaseId --jq '.[0].databaseId')
```

CI troubleshooting: `references/ci-troubleshooting.md`

### Merge

```bash
gh pr merge 123 --rebase --delete-branch  # rebase + merge
gh pr merge 123 --squash                   # squash merge
gh pr merge 123 --merge                    # merge commit
```

### Template Files

- `templates/pr-body-bugfix.md`
- `templates/pr-body-feature.md`

---

## §5 — Code Review

**Reference**: `references/github-code-review.md`

### Fetch PR Diffs

```bash
gh pr diff 123                          # Full diff
gh pr diff 123 --name-only              # Changed files only
gh pr view 123 --json title,body,additions,deletions,files,reviews,comments
```

### Review Commands

```bash
gh pr review 123 --approve --body "LGTM!"
gh pr review 123 --comment --body "Minor nit: trailing whitespace on line 42."
gh pr review 123 --request-changes --body "This approach doesn't handle edge case X."
```

### Checklist-Based Review Template

```
## Review Checklist
- [ ] Code compiles/lints clean
- [ ] Tests added for new functionality
- [ ] Error handling is appropriate
- [ ] No hardcoded secrets/URLs/ports
- [ ] Edge cases handled (null, empty, timeouts)
- [ ] Documentation updated
- [ ] No breaking changes to public API
```

### Inline Comments via REST API

```bash
# Comment on a specific line
curl -s -X POST \
  -H "Authorization: token $GH_TOKEN" \
  -H "Accept: application/vnd.github.v3+json" \
  https://api.github.com/repos/owner/repo/pulls/123/comments \
  -d '{"body":"This should use `.get()` with a default.","commit_id":"<sha>","path":"src/main.py","line":42}'
```

### Output Template

See `references/review-output-template.md` for structured review formatting.

---

## §6 — Git Content Archaeology

**Reference**: `references/git-content-archaeology.md`

### Find Deleted Files

```bash
# Files deleted in commits
git log --diff-filter=D --name-only --pretty=format:"%h %s" -- "*$PATTERN*"

# Find when a specific file was deleted
git log --all --full-history --diff-filter=D -- "*filename*"

# List all deleted files across entire history
git log --diff-filter=D --name-only --pretty=format:'' | sort -u

# Deleted files in the last N commits
git log --diff-filter=D --name-only --pretty=format:"%h" -n 20 | grep -v '^$'
```

### Restore a Deleted File

```bash
# From a specific commit
git restore --source <commit-hash> -- path/to/deleted-file

# From the commit that deleted it (the parent still has it)
git checkout <deleting-commit>^ -- path/to/deleted-file
```

### Handle Chinese/Exotic Filenames

```bash
# Find non-ASCII filenames
git ls-files | grep -P '[^\x00-\x7F]'
# OR if the file was deleted
git log --diff-filter=D --name-only -n 10 | grep -P '[^\x00-\x7F]'

# Restore with --literal-pathspecs (avoid glob interpretation)
git restore --source <hash> --pathspec-from-file=<(echo "中文字幕-带版权的示例.md")
```

### Restore an Entire Deleted Directory

```bash
git restore --source <hash> -- path/to/directory/
git checkout <hash>^ -- path/to/directory/
```

---

## §7 — Codebase Inspection

**Reference**: `references/codebase-inspection.md`

Quick language/code metrics using `pygount`:

```bash
pip install pygount

# Full language breakdown (exclude deps)
pygount --format=summary --folders-to-skip=".git,node_modules,venv,__pycache__,dist,build" .
```

### Common Flags

| Need | Command |
|------|---------|
| Summary table | `pygount --format=summary .` |
| Single language | `pygount --suffix=py --format=summary .` |
| JSON output | `pygount --format=json .` |
| Detailed output | `pygount .` (per-file) |

### Pitfalls

1. **Always exclude `.git`, `node_modules`, `venv`** — without `--folders-to-skip`, pygount crawls everything and may take minutes.
2. **Markdown shows 0 code lines** — pygount classifies Markdown content as comments, not code.
3. **Large monorepos** — use `--suffix` to target specific languages instead of scanning everything.

## Common Pitfalls

1. **`gh auth status` fails on CI machines** — use `GH_TOKEN` environment variable instead of interactive login
2. **SSH key passphrase** — `gh auth login` uses token auth by default; SSH needs keychain set up
3. **PR close vs. merge** — closing without merging deletes the branch; merging keeps history
4. **Workflow ref** — always pass `--ref <branch>` when triggering workflows; default behavior may surprise
5. **Large diffs** — `gh pr diff` paginates but may time out; use `--name-only` first
6. **Deleted file in submodule** — recover from the submodule's own repo, not the parent
7. **Space/emoji in filename** — always use `--pathspec-from-file` for problematic names
8. **`gh repo create` with `--push`** — only works if the directory is already a git repo
