# Session Reference: 2026-07-06 — Restoring angelife.github.com and Local Preview Recovery

## Context
- Repo: `/Users/macos/angelife.github.com`
- Remote: `https://github.com/angelife/angelife.github.com.git`
- Default local preview: `hugo server --buildDrafts -p 1313` from `hugo-site/`
- User expectation: "本地预览" = actual Hugo dev server, not a static file server

## Recovery Sequence Used
1. If the root repo has no `.git` or `hugo-site/` is missing:
   - `git init`
   - `git remote add origin https://github.com/angelife/angelife.github.com.git`
   - `git fetch origin`
   - `git reset --hard origin/master`
   - `git clean -fd`
2. After restore, verify:
   - `ls -ld hugo-site`
   - `find hugo-site -maxdepth 2 -type f \( -name 'hugo.toml' -o -name 'hugo.yaml' -o -name 'hugo.yml' \)`
3. If the user asks for local preview:
   - Check for any existing `hugo server` processes first
   - If one is already running, don't start another; just verify it
   - Otherwise start: `hugo server --buildDrafts -p 1313 --bind 127.0.0.1` from `hugo-site/`
   - Verify readiness with `curl` against `/`, `/search/`, and an article path like `/series/yi-notes/`

## Pitfall Notes
- Using `python3 -m http.server` on the repo root is NOT equivalent; it bypasses Hugo templating and can make taxonomy/article pages appear empty.
- `git checkout HEAD --` on a repo without `.git` will fail with `fatal: not a git repository`; recover from origin first.
- `git checkout HEAD -- categories/ tags/ series/ posts/ images/` can restore empty directory skeletons from git if those directories are present but have no tracked files; that does not restore rendered Hugo content.
