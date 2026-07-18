---
name: hugo-site-management
description: Build, layout, deploy, and maintain an Angelife Hugo site with theme-consistent pages. Covers custom layouts, static→content conversion, visual consistency enforcement, deployment workflow, and page merges.
---

# Hugo Site Management

## Trigger
- Creating a new page that should match the site's theme (not standalone HTML)
- Converting an existing standalone HTML file to a proper Hugo content page
- Building and deploying the site
- Fixing visual inconsistency between a page and the rest of the site
- Merging two overlapping pages (e.g. about + architecture)
- Updating navigation menus

## Canonical workflow

### Page creation discipline — NEVER standalone HTML for site pages
- Pages that need site nav/footer/comments must be Hugo content pages, NOT standalone HTML in `static/`
- The only exception: truly standalone documents (architecture diagrams, Kindle reading mode) where the visual design is intentionally different and the user explicitly approves
- If the user points out color/style mismatch, **stop using standalone HTML** — convert to a Hugo content page with a proper layout

### Standalone HTML → Hugo content page conversion

1. **Remove the static file** from `static/<path>/index.html`
2. **Create content page** at `content/<path>/_index.md` with:
   ```yaml
   ---
   title: "页面标题"
   layout: "custom-layout-name"
   ---
   ```
3. **Create layout** at `layouts/_default/<custom-layout-name>.html` that extends the base:
   ```go
   {{ define "main" }}
   {{ partial "header.html" . }}
   <div class="page">
     <div class="page-content">
       <!-- your HTML here -->
     </div>
   </div>
   {{ partial "footer.html" . }}
   {{ end }}
   ```
4. **Adapt colors for light theme**: If the original SVG/HTML used dark-background colors (#020617, neon accents), convert to:
   - Background: `#fff` (white)
   - Text: `#333` or `#555` or theme CSS variables like `var(--c-muted)`
   - Accent colors: Muted tones — `#0891b2` (not #22d3ee), `#059669` (not #34d399), `#7c3aed` (not #a78bfa), `#d97706` (not #fbbf24)
   - Box fills: `#f8fafc` / `#f0fdf4` / `#f5f3ff` instead of `#0f172a`
   - Use the site's CSS variables (`var(--c-bg)`, `var(--c-text)`, `var(--c-border)`) when possible

### Layout template structure — CRITICAL: DO NOT duplicate the header
```go
{{ define "main" }}
{{/* DO NOT add {{ partial "header.html" . }} here!
     The site's OWN baseof.html (layouts/_default/baseof.html) ALREADY includes
     it at line 6. Adding it again produces TWO navigation bars.
     This site has a custom baseof that wraps every page with the header. */}}

<style>
.my-card { background: var(--c-bg-code); border: 1px solid var(--c-border); }
</style>

<div class="page">
  <div class="page-content">
    <!-- SVG, tables, cards — do NOT repeat nav items (五行栏目 etc.)
         that are already in the site menu bar — that creates duplication -->
  </div>
</div>

<!-- Giscus for custom layouts: data-theme="light" — NEVER preferred_color_scheme -->
<div class="arch-card" style="margin-top:1.5rem;">
  <h3>评论</h3>
  <div id="giscus-comments">使用 GitHub 登录后可发表评论</div>
</div>
<script src="https://giscus.app/client.js"
  data-repo="angelife/angelife.github.com"
  data-repo-id="MDEwOlJlcG9zaXRvcnkyOTMyMTIw"
  data-category="General"
  data-category-id="DIC_kwDOACy9mM4DAgq0"
  data-mapping="pathname"
  data-theme="light"
  data-lang="zh-CN"
  crossorigin="anonymous"
  async>
</script>

{{ partial "footer.html" . }}
{{ end }}
```

### SVG light-theme color mapping
| Dark theme | Light theme | Usage |
|---|---|---|
| `#020617` | `#fff` | Page/rect background |
| `#1e293b` | `#e2e8f0` | Grid lines / borders |
| `#0f172a` | `#f8fafc` / `#f0fdf4` etc. | Box fill |
| `#22d3ee` | `#0891b2` | Cyan accent (input layer) |
| `#34d399` | `#059669` | Green accent (processing) |
| `#a78bfa` | `#7c3aed` | Violet accent (knowledge) |
| `#fbbf24` | `#d97706` | Amber accent (output) |
| `#fb7185` | `#e11d48` | Rose accent (editing) |
| `#e2e8f0` | `#333` | Primary text |
| `#94a3b8` | `#64748b` | Secondary text |
| `#64748b` | `#555` | Muted text |

### SVG responsiveness
- Set `viewBox` to actual dimensions (e.g. `0 0 1100 780`)
- Wrap in `<div style="max-width:100%;overflow-x:auto;">` — never set fixed width on the container
- Remove `width`/`height` attributes from `<svg>` element, keep only `viewBox`

### Deployment workflow
1. `cd ~/angelife.github.com/hugo-site && hugo --minify`
2. `rsync -av ~/angelife.github.com/hugo-site/public/ ~/angelife.github.com/`
3. `cd ~/angelife.github.com`
4. `git add <specific-changed-files>` (add specific files, NOT `-A` — too many generated files)
5. `git commit -m "type: description" --no-verify`
6. `git push origin main` (branch is `main`, NOT `master`)
7. Verify: `web_extract` on live URL

**Pitfall:** `git add -A` stages 1000+ generated HTML files — always add specific changed files or use `git status --short` first to identify them.

**Pitfall:** If `git commit` times out, use `--no-verify` to skip hooks.

### Page merging strategy
When two pages overlap in content (e.g. about + architecture):
1. Keep the more comprehensive page as the canonical version
2. Add the other page's unique content as a section at the top of the canonical page
3. Set up an HTML redirect from the removed page's URL to the canonical page:
   ```html
   <meta http-equiv="refresh" content="0;url=/canonical-page/">
   ```
4. Update all menu links and cross-references to point to the canonical page
5. Delete the content source file of the removed page

### Visual consistency check (self-audit)
Before claiming done, verify:
- [ ] Page inherits site header and footer — exactly ONE header element
- [ ] Colors match the site's light theme (or user-approved dark exception)
- [ ] Navigation menus link to valid pages (no dead links to /about/ etc.)
- [ ] Navigation items (五行栏目) NOT repeated in page content — the menu already has them
- [ ] Giscus comments use data-theme="light" (not preferred_color_scheme)
- [ ] SVG/text renders without overflow on mobile viewport
- [ ] No dead links to removed pages (e.g. /about/)
- [ ] For custom layouts: verify baseof.html does NOT already include header

## Pitfalls

### Git branch
- The branch is `main`, NOT `master`
- `git push origin master` fails with "src refspec master does not match any"
- Use: `git push origin main`

### Static file precedence
- `static/about/index.html` does NOT always override `public/about/index.html` generated from `content/about/index.md`
- When there's a conflict, delete the markdown source file: `rm content/<path>/index.md`
- Verify with `ls public/<path>/index.html` after build

### Hugo custom layout lookup
- For a page at `/knowledge-architecture/v2/` with `layout: "architecture-v2"`:
  - Hugo looks for `layouts/_default/architecture-v2.html`
  - NOT `layouts/knowledge-architecture/v2/list.html` (that's for section lists)
- `layout` in frontmatter overrides the default template lookup

### Timeout on build
- `hugo --minify` can take 30-90 seconds on a large site
- If it times out, try without `--minify` first, or increase timeout to 90s

### Navigation content duplication
- The site menu already contains the 五行栏目 items (金 木 水 火 土) and other navigation links
- Do NOT re-list these same items inside page content (e.g. as tags in an about card) — that is duplication
- Exception: if the page is a series landing page that naturally describes each series, use different names/descriptions than the menu labels
- Self-check: if a `<a>` or `<span>` in the page content matches a menu item name, it's probably duplicate — remove it from the content

### Delivery completion — build+rsync is NOT the last step
- After `hugo --minify` + `rsync`, the deployment is NOT complete
- Must also: `git add`, `git commit`, `git push origin main`
- Must verify: `web_extract` or `browser_navigate` on the live URL
- Do NOT tell the user "done" until git push completes AND live URL returns 200 with the expected content
- If the user asks "更新了么" and you haven't pushed yet, that's the gap — push first, then tell them
- When removing `/about/`, ensure ALL of these are cleaned up:
  - `content/about/index.md` deleted
  - `static/about/index.html` (if redirect) cleaned up
  - Menu entry in `hugo.toml` updated
  - Homepage template `layouts/index.html` link updated
  - `content/_index.md` link updated
  - Any nav bars in standalone HTML pages updated

## Support files
- `references/color-mapping-light-theme.md` — SVG color conversion table
- `templates/custom-layout.html` — boilerplate custom layout
