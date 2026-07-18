---
name: git-content-archaeology
title: Git Content Archaeology — Recover Deleted Files from Git History
description: Find and restore deleted files (including Chinese/exotic-named) from git history. Covers git log forensic search, tree inspection with encoding-safe output, batch restore, and frontmatter cleanup after recovery.
---

# Git Content Archaeology

Find and restore files that were deleted from a git repo but still exist in the commit history.

## When to Use

- Files were deleted and you need them back
- A commit message says "remove checkout residue" or similar cleanup
- Old blog posts/content was cleaned up but you want to reconsider
- Chinese or Unicode file names are involved (git octal-encoding issue)

## Step 1: Find the Deletion Commit

```bash
# If you know the pattern
git log --all --diff-filter=D -- "path/to/pattern"

# If files were definitely in the repo at some point
git log --all --oneline -- "path/to/target"

# Show what a known commit actually touched
git show --stat <commit-hash>
```

## Step 2: Find the Last Good Commit

```bash
# Find commits that contain the files (listed by git log in step 1)
# The last commit BEFORE the deletion commit is the one to restore from

# Verify files exist at a candidate commit
git ls-tree -r --name-only -z <candidate-commit> | tr "\0" "\n" | grep "your/pattern"
```

**Critical**: Use `-z` (null separator) with `git ls-tree` when files have Chinese/Unicode names. Without it, the output wraps paths in quotes with octal escape sequences (like `"path/\345\233\276/index.md"`) which shell pipes and Python subprocess(text=True) cannot reliably parse.

## Step 3: Batch Restore

### Shell approach (encoding-safe for Chinese names):

```bash
git ls-tree -r --name-only -z <commit> | tr "\0" "\n" | while IFS= read -r file; do
  case "$file" in
    *your-pattern*)
      target="/path/to/$file"
      if [ ! -f "$target" ]; then
        mkdir -p "$(dirname "$target")"
        git show <commit>:"$file" > "$target" 2>/dev/null
      fi
      ;;
  esac
done
```

### Python approach (no shell pipe, raw bytes):

```python
import subprocess, os

def restore_files(commit, repo_dir, pattern_filter=None):
    r = subprocess.run(
        ["git", "ls-tree", "-r", "--name-only", "-z", commit],
        capture_output=True, cwd=repo_dir
    )
    paths = [p for p in r.stdout.decode().split("\0") if p.strip()]
    
    for path in paths:
        if pattern_filter and pattern_filter not in path:
            continue
        target = os.path.join(repo_dir, path)
        if os.path.exists(target):
            continue
        os.makedirs(os.path.dirname(target), exist_ok=True)
        
        r2 = subprocess.run(
            ["git", "show", f"{commit}:\"{path}\""],
            capture_output=True, cwd=repo_dir
        )
        if r2.stdout:
            with open(target, 'wb') as f:
                f.write(r2.stdout)
```

## Step 4: Post-Recovery Cleanup

Deleted files often have stale references (missing cover images, unpublished drafts).

```bash
# Remove cover blocks from Hugo frontmatter
sed -i "/^cover:$/,/^  alt:/{/^cover:$/d; /^  alt:/d}" posts/*/index.md

# Set draft: true to prevent auto-publishing
sed -i "s/draft: false/draft: true/" posts/*/index.md

# Verify no stale cover refs or remaining draft: false
grep -l "^cover:" posts/*/index.md
grep -c "draft: false" posts/*/index.md
```

## Pitfalls

1. **Chinese filenames + shell piping**: Without `-z` (null separator), filenames get octal-encoded with surrounding quotes. Pipe corruption is silent — inspect with `cat -v` and retry with `-z`.
2. **`git show` with encoded paths**: Quote the path: `git show <commit>:"path/中文/index.md"` — works with literal Unicode or octal-encoded forms.
3. **Python text=True corrupts**: Use `capture_output=True` (bytes) and decode manually; `text=True` mangles octal paths.
4. **Draft state**: Restored content at `draft: false` will deploy on next push if published accidentally. Check frontmatter before committing.
5. **Cover images**: If posts referenced local cover images that were also deleted, remove the cover blocks. The images are unlikely to be recoverable unless committed separately.

## Verification

```bash
# Count restored files
git diff --stat HEAD

# Build with Hugo
hugo --gc --minify -s hugo-site

# Check for remaining draft: false
grep -c "draft: false" posts/*/index.md
```
