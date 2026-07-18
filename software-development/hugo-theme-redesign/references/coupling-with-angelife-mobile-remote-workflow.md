# Coupling with angelife-mobile-remote-workflow

When redesigning the angelife project (and similar Hugo/Git projects), this skill provides the design templates and CSS methodology. The project-specific workflow, role boundaries, git rules, and release script are in the **`angelife-mobile-remote-workflow`** skill.

## Skills Working Together

```
┌──────────────────────────────┐
│ angelife-mobile-remote-      │  ← whose hands, whose authority
│   workflow                   │
└──────────────┬───────────────┘
               │ guides the
               ▼
┌──────────────────────────────┐
│ hugo-theme-redesign          │  ← how to design the templates/CSS
└──────┬───────────────────────┘
       │ produces files for
       ▼
┌──────────────────────────────┐
│ tools/angelife-release       │  ← the only authorized deploy path
└──────────────────────────────┘
```

## Project-Specific Anchors (angelife)

When `hugo-theme-redesign` is invoked on angelife:

1. **Five-element (五行) navigation MUST be preserved in the top nav** at all times. After any redesign the user expects `{文章, 金·判断, 木·蝉识, 水·易理, 火·AI, 土·正见, ...}` accessibility from the top bar (or a clearly discoverable "栏目" entry that exposes all five). Removing the five-element top-nav is a hard regression — the user pasted a P1 problem list specifically about this.

2. **`mainSections: ["posts"]` is already in `hugo.toml`** — Hugo's auto-list renders ONLY when `layouts/index.html` is NOT overridden. If you override `index.html`, you must render the post list yourself, e.g.:
   ```go-template
   {{ range (.Paginator 15).Pages }}
     <article class="post-entry">…</article>
   {{ end }}
   ```

3. **Series (栏目) under `content/series/` are accessed via URL `/series/<slug>/`** — PaperMod taxonomy terms land here. The `[[menu.main]]` config in `hugo.toml` binds menu entries to those URLs.

4. **Existing `_index.md` per-series** (e.g. `content/series/information-judgment/_index.md`) — these act as section index pages. They render through `layouts/_default/list.html` unless overridden.

5. **Cover image bugs are a CLASSIC recurring issue** on this project. Before claiming "all covers work", grep the content tree:
   ```bash
   grep -r "^cover:" content/posts --include="*.md" | wc -l
   grep -r "^  image:" content/posts --include="*.md" | wc -l
   grep -r "^  relative: true" content/posts --include="*.md" | wc -l
   ```
   The first count = total cover declarations, second = map-style with image sub-key, third = relative-path covers. Real fix is `{{ partial "cover.html" . }}` — keep this skill's `cover-param-map-handling.md` reference handy.

6. **`git submodule update --init --recursive` is required** after a fresh clone. PaperMod is a submodule. Without it: `partial "head.html" not found`.

7. **Reserve `---Restore PaperMod partials---` section** in your mental checklist anytime `baseof.html` was rewritten:
   - `breadcrumbs`, `post_meta`, `cover`, `anchored_headings`, `post_nav_links`, `share_icons`, `comments`, `post_canonical`
   - Each requires the matching partial file to exist in `themes/PaperMod/layouts/partials/` (confirmed via `git submodule`).

## Recipe — Restoring a Custom-Baseof PaperMod Override

If a previous session replaced `baseof.html` with a Kindle-style minimal template, and you want to restore PaperMod behavior while keeping the custom CSS:

```bash
# 1. Restore theme-style baseof
cp themes/PaperMod/layouts/_default/baseof.html layouts/_default/baseof.html

# 2. Override ONLY the partials you want different
# (header.html, footer.html, extend_head.html, extend_footer.html)

# 3. Custom CSS lives in /css/angelife-brand.css
# Load it via layouts/partials/extend_head.html:
#   <link rel="stylesheet" href="/css/angelife-brand.css">
```

This is the safer reverse path — restore the framework first, then customize the parts you actually want to change.

## When to NOT Couple

When the user explicitly wants a fully custom baseof (e.g. "design Hugo site from scratch", "make a single-page app style site"), don't force PaperMod coupling. Use `hugo-theme-redesign` standalone with whatever baseof pattern fits.
