# Force-Push Rollback Diagnosis & Recovery

How to diagnose and fix a website rollback caused by `git push --force` on a shared Hugo/GitHub Pages repo.

## Detection Sequence

When a user reports "网站被回滚到旧版本了" (website rolled back to old version):

### 1. Check Live Site Freshness

```bash
# Check RSS lastBuildDate - reveals stale deployment
curl -s https://YOURSITE.github.io/index.xml | grep lastBuildDate
# Also check specific articles (are June 19 posts showing?)
```

### 2. Check GitHub Actions

```bash
gh run list --limit 5 --json conclusion,headBranch,displayTitle,createdAt,url
```

All runs may report `success` even with stale content — the build ran on the wrong commit.

### 3. Check Git Divergence

```bash
# Fetch remote - LOOK for "(forced update)" in output
git fetch

# If you see: + <old>...<new> master -> origin/master (forced update)
# Someone force-pushed, overwriting the branch history

# Compare local vs remote
echo "=== Commits on LOCAL not on remote ==="
git log --oneline origin/master..HEAD

echo "=== Commits on REMOTE not on local ==="
git log --oneline HEAD..origin/master

# Find common ancestor
git merge-base HEAD origin/master
```

### 4. Identify Culprit

Check the remote-only commits for author info:

```bash
git log --oneline --format="%h %an <%ae> %s" HEAD..origin/master
```

Authors like `Hermes Agent (NVIDIA) <hermes@nvidia-docker>` indicate an AI agent running inside a Docker container performed the operation.

## Root Cause Pattern

The typical scenario:
1. AI agent (often 木同学/NVIDIA running in Docker) issues `git push --force`
2. Agent's local copy was based on an older commit (e.g., detached HEAD state)
3. Force-push overwrites the remote branch reference, destroying all commits that existed on remote but not in the agent's local history
4. GitHub Actions triggers and builds from the (now destroyed) remote state, deploying old site content
5. All other agents' recent commits (posted locally but not yet pushed remotely at that moment — OR pushed but not yet present in the force-pusher's clone) are lost from remote

## Recovery

If local repo has the complete history:

```bash
# SAFETY: Only do this after confirming local has ALL desired commits
# Check that local HEAD has everything you need
git log --oneline HEAD -20

# Force push to restore
git push --force origin master

# GitHub Actions workflow auto-triggers on push
# Wait ~2 minutes for deployment
```

## Prevention

- **Branch protection** on `master`: require PR reviews, disable force-push
  ```bash
  gh api repos/:owner/:repo/branches/master/protection \
    -X PUT \
    -f required_status_checks[strict]=true \
    -f enforce_admins=true
  ```
- **Shared repo workflow**: Establish that only `土` (the QA/analyst role) or designated maintainer pushes to master. Other agents push to feature branches and file PRs.
- **Docker agent best practice**: Agents running in containers that push to shared repos should never use `--force`. Their origin remote should be read-only or restricted to feature branches.
