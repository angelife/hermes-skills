# Cross-Site Search Unification (Static Content + Hugo)

## Problem

Hugo generates `index.json` from content pages (posts, series) only. Static HTML files under `hugo-site/static/` are copied verbatim into the build output but never indexed. If your site has a legacy static archive alongside Hugo-managed content, the search at `/search/` won't find it.

## Solution Architecture

```
Hugo build → public/index.json (161 entries)
                ↓
post-build script → public/index.json (353 entries — 161 Hugo + 192 static)
                ↓
search.js reads extended index → unified results
```

## Components

### 1. Post-build index extender

Script at `.scripts/extend-search-index.py`:

- Scans `public/old-site/**/*.html`
- Extracts `<title>` and first ~200 chars of body text
- Appends entries with `categories: "旧站存档"`, `tags: "旧站,存档"`
- Writes merged `index.json`

**Critical CI pitfall**: Do NOT hardcode paths like `~/angelife.github.com/hugo-site/public`. GitHub Actions `$HOME` differs from local dev. Use `os.getcwd()` relative to repo root, or accept a `sys.argv[1]` path override.

### 2. URL param support in search.js

Old-site search box links to `/?q=keyword`. `search.js` must parse `?q=` on load:

```js
var qs = new URLSearchParams(window.location.search);
var qval = qs.get('q');
if (qval) { input.value = qval; doSearch(qval); }
```

This makes every old-site page a search entry point.

### 3. Giscus comment injection for static HTML

Static HTML pages need comments injected before `</body>`. Script pattern:

```python
GISCUS = '''<div id="giscus"></div>
<script src="https://giscus.app/client.js"
  data-repo="owner/repo"
  data-repo-id="..."
  data-category="General"
  data-category-id="..."
  data-mapping="pathname"
  data-theme="light"
  ...
  async></script>'''
content = content.replace('</body>', GISCUS + '\n</body>', 1)
```

**Theme**: Use `data-theme="light"` for pages that don't support dark mode. `preferred_color_scheme` causes mismatch (dark comments on light page).

## Navigation

Add a return-link banner to static archive pages so users can navigate back to the main site. Inject after `<body>`:

```python
BANNER = '''<div style="background:#fff8e1;border-bottom:1px solid #ffe082;
  padding:8px 16px;text-align:center;font:14px/1.5 sans-serif">
  <a href="https://angelife.github.io/" style="color:#b8860b;font-weight:600">
   ← 返回主站</a></div>'''
content = re.sub(r'(<body[^>]*>)', r'\1\n' + BANNER, content, count=1)
```

## Verification

After build + extend:

```python
import json
d = json.load(open('hugo-site/public/index.json'))
old = [e for e in d if e.get('categories') == '旧站存档']
print(f'Hugo: {len(d)-len(old)}, Static: {len(old)}, Total: {len(d)}')
```

Expected: static entries count matches file count under `public/old-site/` (minus blog/_site build artifacts).

## Kindle Partial Generation (pre-build mode)

`extend-search-index.py` also generates `layouts/partials/kindle-old-site-list.html` before Hugo builds:

```python
STATIC_OLD = os.path.join(os.getcwd(), "hugo-site", "static", "old-site")
for html_path in sorted(glob.glob(os.path.join(STATIC_OLD, "*.html"), recursive=False)):
    base = os.path.basename(html_path)
    if base in ("_layouts", "_site", "_posts") or base.startswith("google"):
        continue
    # extract <title>, build url = "/old-site/" + base
    # sort by mtime, limit to 80 entries
```

The partial is pure HTML (no Hugo template syntax), included via `{{ partial "kindle-old-site-list.html" . }}` in `layouts/kindle/list.html`.

## Reader Redirect Dual-Sync

`reader-redirect.js` must exist in TWO locations:
1. `hugo-site/static/js/reader-redirect.js` — for Hugo build output
2. `js/reader-redirect.js` — for root-level static HTML pages

Redirect logic:
- `/posts/:slug/` → `/kindle/posts/:slug/` (Hugo posts)
- `/` / `/index.html` → `/kindle/` (homepage)
- `/old-site/∗` → add `?kindle=1` param (static pages render inline)
- `?normal=1` or `?desktop=1` → force desktop view
- Already on `/kindle/` → no-op

## CI Path Pitfall

The extend script must use `os.getcwd()` NOT `~/angelife.github.com/hugo-site/public`:
```python
PUBLIC = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.getcwd(), "hugo-site", "public")
```
GitHub Actions `$HOME` ≠ local dev path. Hardcoded `~` paths silently fail on CI.

## Sources

Implemented on angelife.github.com, 2026-07-09. 192 old-site entries unified into search. Giscus on 186 static pages. CI path bug fixed in `b0b39e04`. Kindle partial and reader redirect dual-sync added in `9d1fb58e`.
