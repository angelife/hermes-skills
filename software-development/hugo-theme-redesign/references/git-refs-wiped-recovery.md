# Hugo Project: Git Refs Wiped Recovery

## The Problem

A Hugo site repo can end up with **no commits and empty refs** even though:
- The working directory (hugo-site/, content/, css/, etc.) is fully intact
- Git pack files exist in `.git/objects/pack/`
- The remote (origin) has all commits and tags

Symptoms: `git status` says "No commits yet", `git log` is empty, `git branch` shows nothing.

## How It Happens

This typically occurs when:
- Someone accidentally runs `git init` in a directory that already has a `.git/` with pack objects but no refs
- Docker volume mounts or CI steps reset refs without recreating branches
- `git --bare` or other destructive operations overwrite the refs directory

## Recovery Procedure

### Step 1: Check pack files still exist
```bash
ls .git/objects/pack/
# Should see .pack and .idx files
```

### Step 2: Fetch from remote
```bash
git fetch origin master
```

### Step 3: Recreate local branch from remote
```bash
git branch -f master origin/master
git checkout master
```

### Step 4: Verify
```bash
git log --oneline -5
git status
# Should show clean working tree
```

## If Fetch Fails (SSH auth issues)

- Ensure SSH agent has the key: `eval $(ssh-agent) && ssh-add ~/.ssh/id_ed25519`
- Or use HTTPS remote temporarily
- The pack files on disk contain all objects; `git fsck` should show no dangling objects

## Prevention

- Always use `git branch --set-upstream-to=origin/master master` on fresh clones
- In Docker/container environments, map the repo as a volume, not re-initialized
- Before any destructive git operation, verify with `git fsck`
