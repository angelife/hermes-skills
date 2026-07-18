# Polk-x Date Format: Template-hardcoded, Config is Decorative

## The Trap

The `dateFormat` parameter in `hugo.yaml` (under `params:`):

```yaml
params:
  dateFormat: "2006-01-02 15:04"
```

**Does NOT control polk-x's date display.** The polk-x theme ignores this config value entirely. It's a PaperMod convention that polk-x inherited as a dead config key.

## Where Dates Are Actually Rendered

Polk-x hardcodes `.Date.Format "2006-01-02"` directly in templates. **BUT** the project's own `layouts/` directory overrides the theme — both must be patched.

### Theme templates

| File | Location | Effect |
|---|---|---|
| `themes/polk-x/layouts/index.html` | Line ~16 | Homepage article list |
| `themes/polk-x/layouts/_default/list.html` | Line ~17 | Section/category/tag pages |
| `themes/polk-x/layouts/posts/single.html` | Line ~20 | Article detail page (post-time span at bottom) |

### Project-level overrides (take precedence over theme)

| File | Occurrences | Context |
|---|---|---|
| `layouts/index.html` | 1 | Homepage (if present, overrides theme) |
| `layouts/_default/list.html` | 1 | Generic list pages |
| `layouts/_default/single.html` | 1 | Generic single pages |
| `layouts/_default/archives.html` | 1 | Archive page |
| `layouts/posts/single.html` | 1 | Article detail page |
| `layouts/columns/list.html` | 2 | Column section pages (both entries) |
| `layouts/kindle/list.html` | 1 | Kindle-format rendering |

### How to find all instances

```bash
grep -rn '.Date.Format "2006-01-02"' layouts/ themes/polk-x/layouts/
```

This shows all hardcoded format strings across both theme and project overrides.

## Common Failure Mode

**Patching only the theme templates and skipping project overrides.** This is the #1 cause of "made the change but user says it didn't show up." The user reports "没看到更改效果" (no visible change) because Hugo uses the project's `layouts/` before `themes/polk-x/layouts/`. Always grep both directories.

## Fix Pattern

Search and replace the hardcoded format string in ALL matching files:

```
old: .Date.Format "2006-01-02"
new: .Date.Format "2006-01-02 15:04"
```

Go's date format reference:
- `2006` = year
- `01` = month
- `02` = day
- `15` = hour (24h)
- `04` = minute
- `05` = second

## Verification

After patching all files, rebuild and check by viewing any article with a full ISO timestamp in frontmatter (e.g. `date: 2026-06-20T22:00:00+08:00`):

```bash
hugo --gc --buildDrafts  # confirm 0 errors
curl -s http://localhost:1313/posts/ | grep '<time'
```

Articles without time in frontmatter will show `00:00` — consider bulk-adding times to historical articles if needed.
