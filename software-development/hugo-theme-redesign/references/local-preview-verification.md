# Local Preview and Verification for Hugo Theme Redesign

## User Semantics — What "本地预览" Actually Means

When 土同学 tells Tse "本地预览已完成" or when Tse himself says "先本地预览", he means: **he wants to browse the actual rendered website in Safari at `http://localhost:1313/`** — with working navigation, category/series pages, individual article pages, and proper theming. He does NOT mean: reading .md source files, scanning directory listings, looking at build output stats, or hearing about file paths. The deliverable is a live Hugo dev server, not a report.

**This is the default, single-step expectation.** Do not first show file paths, explain bind mounts, or describe build output — Tse does not consider those "预览". Go straight to `hugo server --buildDrafts`.

## After Making Changes: Build + Local Preview

### Build Test

```bash
cd hugo-site && hugo --gc --minify
```

Expected output includes page count. If build succeeds with 0 errors, proceed to preview.

### Local Server

```bash
cd hugo-site && hugo server --bind 0.0.0.0 --port 1313 --disableLiveReload --noHTTPCache
```

**Note:** Hugo server runs in the background — output may not appear immediately due to buffering.

### Verify Server is Ready

```bash
# Quick readiness check
curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:1313/
# Returns 200 when ready
```

### Inspect Generated HTML

```bash
# Get page structure without opening browser
curl -s http://127.0.0.1:1313/ | grep -o '<title>.*</title>'
curl -s http://127.0.0.1:1313/ | grep -oP '<h2[^>]*>.*?</h2>' | head -20
```

### Verify Key Elements Exist

```bash
# Check if navigation items rendered
curl -s http://127.0.0.1:1313/ | grep -c 'article.*post-entry'

# Check if new CSS classes are present
curl -s http://127.0.0.1:1313/ | grep -o 'home-phase-nav' | head -1

# Check article count on homepage
curl -s http://127.0.0.1:1313/ | grep -c 'post-list'
```

## Common Local Preview Issues

### Port already in use
```bash
lsof -i :1313 | grep LISTEN
kill <PID>
```

### Hugo not found
Check if the project uses a vendored Hugo binary:
```bash
find . -name hugo -type f 2>/dev/null | head -5
# Common locations: ./hugo, /opt/data/hugo, /usr/local/bin/hugo
```

### Theme source missing
If `themes/PaperMod/` is empty:
```bash
git submodule update --init --recursive
```

### Build errors on cover parameter
If you see "unable to cast maps.Params to string" on `.Params.cover`:
- Some articles define cover as a map: `cover: {image: "...", alt: "...", caption: "..."}`
- Handle with `{{ if reflect.IsMap .Params.cover }}` — see `cover-param-map-handling.md`

## Docker-Container Hugo Preview (no port mapping)

When Hugo runs inside a Docker container without `-p` port publishing, you cannot reach `hugo server` from the host browser. Two workarounds:

### A) Build to bind mount + Python HTTP server (preferred)

If the container has a bind mount back to the host (e.g., `/Users/macos/angelife.github.com` ↔ `/workspace/angelife.github.com`):

```bash
# Step 1 — Build inside container, output to bind-mount directory
docker exec <container> /path/to/hugo --gc --minify \
  --buildDrafts \
  -s /workspace/angelife.github.com/hugo-site \
  -d /workspace/angelife.github.com/hugo-preview

# Step 2 — Serve on the host (Mac) via Python
cd /Users/macos/angelife.github.com/hugo-preview
python3 -m http.server 1314

# Step 3 — Open http://localhost:1314 in browser
```

Clean up after preview: `rm -rf /Users/macos/angelife.github.com/hugo-preview`

### B) Background hugo server + container-local curl

For quick inline verification without serving to browser:

```bash
# Start server in background
docker exec -d <container> /path/to/hugo server \
  -s /workspace/angelife.github.com/hugo-site \
  --bind 0.0.0.0 -p 1313

# Verify
docker exec <container> curl -s -o /dev/null -w "%{http_code}" http://localhost:1313/

# Check page titles
docker exec <container> sh -c 'curl -s http://localhost:1313/ | grep -o "<title>.*</title>"'
```

## Content Quality Review Pattern (for "预览几篇" requests)

When the user asks "预览几篇" after a batch restore/import of historical articles, follow this review protocol:

### Step 1 — Classify by Category

Map the restored articles across the 五行 categories. Check:
- 金·判断: typically the largest count (~42 articles in angelife)
- 木·蝉识: second largest (~21 articles, often church history series)
- 土·正见: smaller (~10 articles, anti-cult, Confucian framework)
- 火·AI: mostly modern articles, few historical
- 水·易理: may have zero historical articles

### Step 2 — Pick 4-5 Representative Articles

Selection criteria:
- **One from each major category** that has restored content
- **Varied content types**: long-form series (教会史), standalone essay (白岩松), investigative analysis (反邪教), introspective (心理学)
- **Mix of good and marginal quality**: some articles render cleanly, some may have Blogger migration artifacts — show both
- **Verify series continuity**: for multi-part series (e.g., 教会史 20 parts), check that all parts rendered and the series page lists them

### Step 3 — Build with Drafts

Use `--buildDrafts` so draft articles appear in the output. Page count increases significantly (e.g., 461→604 for angelife).

```bash
hugo --gc --minify --buildDrafts -s hugo-site -d /tmp/hugo-preview
```

### Step 4 — Inspect Actual Rendered HTML

Do NOT just count files — read the rendered HTML for at least 2-3 articles to check category labels, dates, and content rendering:

```python
import re
with open('/path/to/preview/posts/<slug>/index.html') as f:
    html = f.read()
# Extract rendered metadata
re.search(r'<div class=post-category>([^<]+)</div>', html)
re.search(r'<span class=post-time[^>]*>([^<]+)</span>', html)
# Extract body content
re.search(r'<div class=post-content>(.*?)</div>', html, re.DOTALL)
```

### Step 5 — Check for Formatting Artifacts

Blogger-exported articles may have rendering issues:

| Artifact | Looks like | Severity |
|----------|-----------|----------|
| Table bar chars | `<p>| \| 标题 \|</p>` | Medium — visible `|` in rendered page |
| Raw HTML entities | `&mldr;` instead of `…` | Low — browsers render correctly |
| Missing images | Broken external Blogger links | Medium — image is gone, alt text shows |
| Raw markdown tables | `<p>| col1 \| col2 \|</p>\n<p>|--- \|---\|</p>` | High — entire table structure visible |

**Report artifacts honestly**: "约 80% 渲染干净，20% 有 Blogger 表格/格式残留" is better than pretending all articles render perfectly.

### Step 6 — Present Results

Format each article preview as:

```
**① 标题**
分类：金·判断 | 日期：2011-10-21
字数：5,817字 | 质量：✅ 干净
开头摘：*实际渲染的文本开头*
备注：来源/特点/问题
```

Include a summary table at the end:

| 指标 | 状况 |
|------|------|
| 文章完整性 | 70篇全部恢复，frontmatter完整 |
| 渲染质量 | 约80%干净，20%有格式残留 |
| 图片依赖 | 全部为外部链接，部分失效 |
| 系列完整性 | 教会史(20篇)、反邪教(7篇) 完整 |

### Step 7 — Clean Up

After preview is done, clean up the temp build directory:

```bash
rm -rf /Users/macos/angelife.github.com/hugo-preview
```

Also kill any Python HTTP servers left running from serving previews.

## Previewing Draft Articles (`--buildDrafts`)

Articles with `draft: true` in frontmatter are excluded from regular `hugo --gc --minify` builds. To preview them:

```bash
# Server mode — includes draft content
hugo server -D       # short flag for --buildDrafts

# Build mode — includes draft content
hugo --gc --minify --buildDrafts

# Verify draft content appears in output
ls <output-dir>/posts/ | wc -l
# Page count should increase from previous build (e.g., 461 → 604)
# Check a specific draft article's page exists
ls <output-dir>/posts/<article-slug>/index.html
```

**Caveat:** `--buildDrafts` also includes unpublished content (`publishDate` in future). For previewing ONLY drafts, combine with `--buildFuture=false` if needed.

## Verifying Draft Content in Preview

After building with `--buildDrafts`:

```bash
# Check total page count increased (draft pages added)
grep 'Pages' build-output.log

# Verify draft articles appear in series/category pages
ls <output-dir>/series/information-judgment/ | grep -c 'index.html'
# Should contain both old and new articles

# Verify a specific draft article renders correctly
head -5 <output-dir>/posts/<article-slug>/index.html | grep '<title>'

# Check homepage does NOT link to drafts (if previewing without --buildDrafts)
grep -c 'href=".*<article-slug>.*"' <output-dir>/index.html
# Returns 0 when drafts excluded, >0 when included
```
