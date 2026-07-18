# Force Push Forensics & Recovery

## Scenario
An agent reports "the website was rolled back to an old version". You suspect a force push from a Docker container or another agent.

## Step-by-Step Diagnosis

### 1. Check Git Fetch for Forced Update Signal
```bash
cd /repo
git fetch
```
Look for: `+ oldhash...newhash master -> origin/master (forced update)`
The `+` prefix and `(forced update)` suffix confirm a force push happened.

### 2. Compare Local vs Remote History
```bash
# What the remote currently has
git log --oneline origin/master

# What local has
git log --oneline HEAD

# Find common ancestor
git merge-base HEAD origin/master

# Commits local has that remote lost
git log --oneline origin/master..HEAD | wc -l
git log --oneline origin/master..HEAD

# Commits remote has that local lost (if any)
git log --oneline HEAD..origin/master | wc -l
git log --oneline HEAD..origin/master
```

### 3. Determine Recovery Strategy
- If `origin/master..HEAD` has many commits → force push local to restore
- If both branches diverged → cherry-pick or rebase to reconcile
- If local has nothing useful → just pull remote

### 4. Recovery (Only from Mac Host, Never from Docker Container)
```bash
cd /Users/macos/angelife.github.com
git push --force origin master
```
Then verify:
- `gh run list --limit 2` — workflow should trigger automatically
- Check `https://angelife.github.io/index.xml` for latest build date
- Check RSS for lost articles

## Key Indicators

| Signal | Meaning |
|--------|---------|
| `fetch` shows `+` and `(forced update)` | Force push happened |
| `origin/master..HEAD` has commits | Local is ahead — can restore |
| `HEAD..origin/master` has commits | Remote has stuff not in local |
| No common ancestor (`merge-base` returns 0) | Repos have diverged completely |
| GitHub Actions latest run shows "deploy success" but site is old | Force push deleted the correct commits before deploy |

## Stale Clone Detection (Critical Investigation Step)

**When a force push is suspected, the container may have MULTIPLE git repos.** The bind-mounted workspace is one; a separate, older clone the agent created independently is another — and that old clone is often the force-push source.

### 1. Find All Git Repos in the Container

```bash
docker exec <container-name> find /opt/data -name ".git" -maxdepth 4 -type d 2>/dev/null
```

Typical output when there's a stale clone:
```
/workspace/angelife.github.com/.git         # bind-mount (live, correct)
/opt/data/angelife-clone/.git               # old clone (stale, dangerous)
```

### 2. Identify Which Repo Is the Culprit

Check each separate clone for its remote state:

```bash
docker exec <container-name> sh -c 'cd /opt/data/angelife-clone && \
  echo "=== Old clone ===" && \
  git log --oneline -3 && \
  echo "Remote:" && \
  git remote -v && \
  echo "Last push target:" && \
  git log --oneline origin/master -1 2>/dev/null || echo "no remote tracking"'
```

Compare its last commit against the live workspace and the remote to confirm it was the force-push source.

### 3. Check `.hermes_history` for What the Agent Was Doing

```bash
# See recent agent actions in the container
docker exec <container-name> cat /opt/data/.hermes_history 2>/dev/null | tail -50
```

This reveals what the agent's last commands were — often showing it tried `git push` in a stale clone, failed on SSH, then escalated to `--force`.

### 4. Account for Dual-Repo State

| Repo | State | Purpose |
|------|-------|---------|
| `/workspace/angelife.github.com/` | Live sync with Mac host | Correct, latest code; bind-mounted; container writes content here |
| `/opt/data/angelife-clone/` (or similar) | Stale, possibly old reflog | Dangerous; may have 20+ days of missing commits; **this is the force-push source** |

**Forensic connection**: The old clone has fewer commits than the live workspace. The agent found the old clone first (or preferred it because it had more history from *its* perspective), then ran `git push --force` from it, which set the remote back to that old state.

### 5. Recovery After Culprit Identification

```bash
# From Mac host ONLY (never from container)
cd /Users/macos/angelife.github.com  # the CORRECT local repo
git push --force origin master
```

Then verify:
- `gh run list --limit 2` — workflow should trigger automatically
- Check `https://angelife.github.io/index.xml` for latest build date
- Check RSS for lost articles

### 6. Prevention After Recovery

Create a `PUBLISHING.md` rule file at the repo root that explicitly states:
- **Container agents MUST NOT execute git push** (especially `--force`)
- Container agents write `.md` files ONLY to the bind-mounted workspace
- 土 handles all git operations (commit, tag, push) from Mac host
- The old clone may be retained as a **cold backup** with read-only access

Also create a helper script `tools/publish-mu.sh` that 土 can run to build + commit + push in one step.

## Common Root Causes
1. **Container agent git push from stale clone** — container has no SSH keys, creates a separate clone, uses `--force` as workaround, overwriting remote with stale local state
2. **Dual-repo confusion** — the agent accidentally operates on the old clone (with outdated history) instead of the bind-mounted workspace
3. **Accidental `git push --force`** — agent intended `git push` but used `-f`
4. **Rebase conflict resolution** — agent force-pushed after rebase, destroying other commits

## Prevention
- **Never do git push from Docker containers** — no SSH keys, no git config
- **Never `git clone` inside the container** — use the bind-mount only
- **Detect and document all clones on first investigation** — `find /opt/data -name ".git"`
- Container agents write content via bind mount: `/workspace/angelife.github.com/hugo-site/content/posts/`
- Put a `PUBLISHING.md` at the repo root with explicit container-publishing rules
- 土 handles all git operations from the Mac host
