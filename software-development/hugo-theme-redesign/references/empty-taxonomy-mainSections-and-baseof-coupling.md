# Empty Taxonomy/Lists: mainSections and baseof Coupling

## Symptom

A Hugo taxonomy or section page renders an empty article list. The HTML is short (often under 2 KB), the title is correct, but `<article class="post-entry">` count is 0 even though `hugo list all` shows the posts exist.

Two distinct root causes produce the same surface symptom. Both were observed in production on the angelife project.

---

## Cause 1: mainSections missing the section type (silent filter)

PaperMod's `_default/list.html` and `_default/archives.html` filter pages with:

```go
{{- $pages := where site.RegularPages "Type" "in" site.Params.mainSections }}
```

If a section's `Type` is not in `mainSections`, all its pages are filtered out before pagination begins. The page renders with the H1 from the section's `_index.md`, but with zero entries. Build succeeds silently — no error, no warn.

### Correct placement in hugo.toml

`mainSections` is a TOP-LEVEL array. It is **not** under `[params]` and **not** under `[outputs]`.

✅ Correct:
```toml
theme = "PaperMod"
copyright = "© ..."

mainSections = ["columns", "posts", "series"]

enableRobotsTXT = true
```

❌ Wrong (silently ignored, sometimes even logged as WARN):
```toml
[outputs]
  home = ["HTML", "RSS", "JSON"]
  mainSections = ["columns", "posts", "series"]   # wrong — TOML nests under outputs

[params]
  mainSections = ["columns", "posts", "series"]   # wrong — params is unrelated to mainSections

[mainSections]
  main = ["columns", "posts", "series"]            # wrong — that's a table assignment, type mismatch
```

### Diagnostic: did I write mainSections in the right place?

```bash
cd hugo-site && hugo --gc --minify
```

If you see `WARN  Unknown kind "mainsections" in outputs configuration.`, the line is nested under `[outputs]`. Move it to the top level.

If you see **no warning** but the list is still empty AND `hugo list all` confirms the posts exist with the expected `Type`, suspect Cause 2.

### Duplicate history trap

If earlier project changelogs mention a `mainSections` fix that was later reverted (e.g. covered by a series→columns replacement), double-check the current `mainSections` matches the **current** section types your `content/` directory actually uses. A fix from commit N may be correct for commit N's directory layout, but your working tree may have different section names.

---

## Cause 2: Custom baseof.html with wrong root context

If `layouts/_default/baseof.html` has been replaced (e.g. by a previous "Kindle-only" redesign) and includes a non-PaperMod stylesheet (`<link rel="stylesheet" href="/css/kindle.css">`) plus a minimal `<body>` that just `{{ block "main" . }}{{ end }}`, then **all** pages that override `_default/list.html` with a custom template will render through that custom template, even though PaperMod's own `list.html` exists in the theme.

Symptoms: HTML title correct (e.g. "信息判断 | 安知生 angelife"), but the body has only header chrome + a paragraph of description text, no `<article class="post-entry">` tags. Total file size ~1-2 KB. Stylesheet link visible in `<head>` points to `/css/kindle.css` or similar non-PaperMod file.

The cascade: custom baseof loads the wrong CSS, custom list.html is a thin wrapper around `{{ .Content }}` (no pagination loop), no `layouts/_default/term.html` exists, so taxonomy pages fallback to the broken list.html → empty result.

### Fix

Restore PaperMod's `baseof.html` and `list.html` from the theme source. They are scaffold files and safe to copy fresh:

```python
import shutil
shutil.copy2("themes/PaperMod/layouts/_default/baseof.html",
             "layouts/_default/baseof.html")
shutil.copy2("themes/PaperMod/layouts/_default/list.html",
             "layouts/_default/list.html")
```

After rebuilding, expect the page size to jump from ~1 KB to ~14 KB and `<article class="post-entry">` count to match the post count for that section.

---

## Verifying the fix actually rendered

Don't grep for class names you invented. PaperMod uses specific class names:

| Element | PaperMod class |
|---------|----------------|
| Article entry | `<article class="post-entry">` (or `first-entry` for index 0 on home) |
| Entry H2 | `<h2 class="entry-hint-parent">` (NOT `entry-title`) |
| Entry footer | `<footer class="entry-footer">` |
| Cover | rendered via `{{ partial "cover.html" . }}` |

Quick verification script:
```python
import re
with open("public/series/information-judgment/index.html") as f:
    c = f.read()

articles = re.findall(r'<article[^>]*class="([^"]+)"', c)
print(f"article tags: {len(articles)}")
# If 0 → Cause 2 still active
# If matches expected → Cause 1 fixed

# Also check stylesheet link
m = re.search(r'stylesheet[^>]*href="([^"]+)"', c)
if m:
    print("stylesheet:", m.group(1))
# Should be /assets/css/stylesheet.<hash>.css (PaperMod default)
# Not /css/kindle.css (Kindle-only override)
```

---

## Related pattern: GroupByDate on a top-level _index.md

If you create `content/archives/_index.md` and try to group posts by year:

```go
{{ range .Pages.GroupByDate "2006" }}
```

This produces zero output. `.Pages` on a top-level `_index.md` does not contain posts — it contains child sections.

For custom archive pages, iterate from `site.RegularPages`:

```go
{{ range (where site.RegularPages "Type" "posts").GroupByDate "2006" }}
  <div class="archives-year">
    <h2>{{ .Key }}</h2>
    {{ range .Pages }}<article class="post-entry">...</article>{{ end }}
  </div>
{{ end }}
```

If the symptom persists past this explanation, suspect `Type` mismatch.

---

## Decision tree when "list page is empty"

```
Empty list page on /series/X/
│
├─ hugo build -> WARN about mainSections?
│  └─ YES: move mainSections to top-level hugo.toml
│
├─ hugo build -> no output about mainSections, list still empty
│  │
│  ├─ Inspect generated HTML:
│  │  ├─ < 2 KB, no <article> tags
│  │  │   └─ check stylesheet link. If non-PaperMod (e.g. kindle.css):
│  │  │      suspect Cause 2 → restore baseof.html from theme
│  │  │
│  │  └─ normal size (~12-15 KB), BUT <article> count is 0
│  │      └─ post.Type not in mainSections → Cause 1
│  │
│  └─ hugo list all | grep Type
│     └─ See if expected Type matches mainSections entries
```

Don't try fixes blind. The two causes need opposite fixes (Cause 1: redo config; Cause 2: restore template). Misdiagnosing wastes cycles on the wrong file.
