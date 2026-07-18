# Key Mapping Pitfalls

## Session: 2026-07-04 Hermes provider healthcheck + key.txt integration

### What went wrong
- Treated `key.txt` as a bag of secrets to be appended with guessed variable names (`KEY_TXT_NEW_*`).
- This violates the single-source-of-truth model and makes later mapping impossible without another guessing round.
- It also wastes turn budget, because `.env` later had to be restored from backup.

### Lesson
- **No invented env vars.** Only write real, semantically named env vars.
- **No silent reassignment.** Unless the user explicitly authorizes a full variable refresh, do not overwrite existing keys.
- **Require authoritative mapping first.** The only safe input is a table like:
  - `OPENCODE_ZEN_API_KEY=... provider=opencode-zen line=6`
  - `NVIDIA_API_KEY=... provider=nvidia-nim line=18`
  - `AGNES_API_KEY=... provider=agnes line=31`
- **If mapping is missing, stop and ask once**, then execute exactly once.

### Desired behavior
1. Inspect `key.txt` content.
2. If user did not provide mapping, ask for provider->line/value mapping in a single compact prompt.
3. Apply only the explicitly confirmed mappings.
4. Re-run provider healthcheck with real variables, not guesses.
