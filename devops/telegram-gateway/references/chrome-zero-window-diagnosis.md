# macOS Chrome 0-Window Diagnosis (cross-platform reference)

## Symptom
Chrome process runs but no window appears. Clicking Dock icon has no effect.
`osascript -e 'tell application "Google Chrome" to count windows'` returns 0.

## Root Causes

### 1. Crashpad directory corruption
`~/Library/Application Support/Google/Chrome/Crashpad/` gets corrupted, blocking startup.
**Fix:** `rm -rf ~/Library/Application\ Support/Google/Chrome/Crashpad`

### 2. Local State file corruption
`~/Library/Application Support/Google/Chrome/Local State` becomes corrupt.
**Fix:** Delete the file. Chrome recreates it with fresh defaults. Bookmarks/passwords/history in `Default/` are unaffected.

### 3. LaunchServices stale registration
Previous headless or `--no-startup-window` instances leave stale registrations.
**Fix:** Reset LaunchServices and re-register Chrome:
```bash
lsregister -kill -r -domain local -domain system -domain user
lsregister -f /Applications/Google\ Chrome.app
```

## Diagnostic Method (Binary Isolation)
1. Move entire `~/Library/Application Support/Google/Chrome/` aside
2. Launch Chrome — if fresh profile works, issue is in user profile
3. Restore only `Default/` directory — if still works, issue is in a top-level file
4. Binary-search top-level files/Local State to find the specific file

## Key Log
`log show --predicate 'process == "Google Chrome"'` shows **`Unable to find className=(null)`** when window creation fails.
