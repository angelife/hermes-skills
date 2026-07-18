# Angelife repo hygiene

## Source of truth

- `hugo-site/` is the canonical source tree.
- `old-site/` is preserved as-is.
- Do not recreate deleted duplicate top-level dirs once they are removed.

## Dedup rules

- Preserve `old-site/` exactly.
- From every other duplicate tree, keep only the `hugo-site/` copy.
- After deletion, rebuild and verify:
  - `hugo --gc --minify -s hugo-site`
  - check key rendered paths still exist under `hugo-site/public/...`

## Commit discipline

- Commit only meaningful changes.
- Exclude noise:
  - `.DS_Store`
  - stray `docs/` scratch outputs that are not site content
  - duplicate top-level generated dirs already deleted from the worktree
- Prefer scoped commits:
  - title cleanup
  - repo dedup cleanup
  - published article updates
