---
name: hugo-comment-integration
description: Add, theme-match, and verify comment systems on Hugo sites. Governs Giscus/Valine/Waline/Twikoo integration, partial injection across layouts, and GitHub Pages deploy verification.
---

# Hugo 评论系统集成

## Trigger
- 在 Hugo 站点增加/切换评论组件（Giscus / Valine / Waline / Twikoo）
- 评论区颜色/主题与站点不一致
- 某类文章页（series / posts）渲染后评论区缺失
- 推送后线上页面未出现评论组件

## Canonical steps
1. 识别所有实际渲染用的 layout：`posts/single.html`、`_default/single.html`、主题自带 layout
2. 统一挂载评论 partial，不要只修一个 layout
3. 在 `comments.html` 里做系统级切换；配置写在 `hugo.toml`
4. 主题对齐：先锁定站点色板，再把评论组件 theme 绑到站点值
5. `hugo` 构建，grep 实际输出 HTML 的 script tag 和数据属性
6. git commit + push，然后线上页面探测验证

## Theme matching pitfall
- 若站点已锁定亮色背景，Giscus 绝不能设 `preferred_color_scheme`
- 适当值：`light`、`dark`，或自定义 CSS 变量映射
- 不要用主题自动适配；静态站点下它会与站点色板冲突
- 若站点强制亮色，直接在 `comments.html` 把 `data-theme` 钉死为 `light`

## Layout coverage pitfall
- `posts` 类型走 `posts/single.html`
- `series` 或其他非 posts 类型通常退到 `_default/single.html`
- 二者都要挂 `partial "comments.html"`，否则只修一个会漏页

## Custom layout pages (not posts/series)

When the page uses a **custom layout** (`layouts/_default/architecture-v2.html` etc.) instead of the standard `_default/single.html`:

1. Comments must be injected **directly in the custom layout**, not via `partial "comments.html"`
2. The Giscus script tag goes at the bottom of the `<div class="page-content">` section, before `{{ partial "footer.html" . }}`
3. Wrap in a styled card: `<div class="arch-card"><h3>评论</h3><div id="giscus-comments">...</div></div>`
4. Use `data-theme="light"` (not `preferred_color_scheme`) for static custom pages — the theme toggle on the page may not sync correctly with Giscus' auto-detection
5. Verify after build: `grep "giscus.app" public/<path>/index.html`

## Verification
- 本地：`hugo --gc --minify`
- 标记检查：grep `giscus.app/client.js`、`data-theme=light`、`post-comments`
- 线上：访问实际文章页源码，确认评论 script 存在
- 若线上缺失：先确认 push 的分支与 Pages workflow 分支一致

## Content-level diagnosis over title/slug checks
- 归档页“重复”投诉若只按标题/time 查，会把不同 section 的条目误判成重复
- 真正重复只存在于正文内容完全一致的场景；用 body MD5 比对，不要只看 slug/title
- `posts/...` 与 `series/...` 常因迁移历史出现标题近似、URL 不同的条目；这是现象级重复，不是内容级重复

## Giscus open-comment constraint
- Giscus 要求评论者拥有 GitHub 账号；若要“任意访客可留言”，应切 Waline/Twikoo/Artalk 等自托管方案
- repoId/categoryId 都必须存在；否则组件不渲染

## Alternative: Static HTML file injection (for legacy/archived content)

When the target pages are NOT Hugo templates but static HTML files under `static/old-site/` (Vimwiki output, hand-crafted archives):

1. **Determine the closing pattern**: Check if pages end with a predictable `</body>` (after consistent script tags).
2. **Write a Python injection script**: Walk the directory recursively, inject Giscus block before `</body>` via `str.replace`, skip files already containing the injected block (idempotent).
3. **Match theme**: If the archive has a fixed light background, use `data-theme="light"` (never `preferred_color_scheme` — it mismatches on dark OS). Add inline `<style>` for `#giscus` container to inherit the page font stack and background.
4. **Run pre-build**: Since files are under `static/`, Hugo copies them verbatim to `public/`.

**Pitfalls:**
- Subdirectories (`blog/_site/`, `diary/`) require `recursive=True`; some may lack `</body>` (fragment templates) — detect and skip
- Color mismatch: archive with no dark mode + `preferred_color_scheme` = dark comments on light page; force `data-theme="light"`
- Giscus uses URL pathname mapping per page; verify comment section appears on live page after deploy
- Add a "返回主站" banner at the top of each page via the same injection pattern

## Post-build: Extending Hugo's search index with static page entries

A Hugo site with `static/old-site/` (archive of static HTML) won't include those pages in `/search/` because Hugo's `index.json` only covers content files.

**Fix:**
1. Write `scripts/extend-search-index.py` that:
   - Reads `public/index.json` (Hugo output)
   - Scans `public/old-site/` for `.html` files
   - Extracts `<title>` and plain-text summary from `<body>` (strip HTML tags)
   - Appends entry with `categories: "旧站存档"`, `permalink`, `tags: "旧站,存档"`, `title`, `summary`
   - Writes back to `public/index.json`
2. Add a CI step in `.github/workflows/hugo.yml` after the Hugo build:
   ```yaml
   - name: Extend search index with old-site entries
     run: python3 .scripts/extend-search-index.py
   ```
3. Front-end `search.js` needs no changes — it already fetches `/index.json`

**Cross-site search linking:** Add a search link on archive pages pointing to `/search/?q=` and update `search.js` to parse `?q=` on load via `URLSearchParams`, setting the input value and triggering search automatically.

### CI path pitfall (critical)

Scripts with hardcoded `~/angelife.github.com/...` paths fail on GitHub Actions — `~` resolves to `/home/runner/` but the repo checkout lives under `$GITHUB_WORKSPACE`. **Always use relative paths from CWD:**

```python
PUBLIC = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.getcwd(), "hugo-site", "public")
```

Works locally (repo root) and in CI (runner CWD = repo checkout root).

### Two-step CI pattern

When a static enhancement needs both a **partial** Hugo includes during build AND an **index extension** after build, split into pre-build + post-build:

```yaml
- name: Pre-build — generate partial from static/
  run: python3 .scripts/extend-search-index.py  # reads static/
- name: Build Hugo
  working-directory: hugo-site
  run: hugo --gc --minify
- name: Post-build — extend index.json
  run: python3 .scripts/extend-search-index.py  # reads public/
```

The script must be idempotent — detect whether `public/` exists and do only the applicable work each pass.

### Banner injection on static pages

When adding a "返回主站" navigation banner to archived static pages, inject after `<body>` via regex. Keep idempotent — skip files already containing a marker. Include search + Kindle links in the same banner for cross-functionality. Run on `static/` source directory pre-build so Hugo copies it along.

## Support files
- `templates/comments-partial.html` — 双系统切换模板
- `scripts/verify-comments-rendered.py` — 构建 + HTML 标记检查
- `scripts/extend-search-index.py` — 将旧站静态 HTML 条目合并入 Hugo `index.json`
- `references/archive-duplication-diagnosis.md` — 归档页重复投诉的验证顺序和用户感知型重复分类
- `references/static-archive-giscus-injection.md` — 静态 HTML 文件批量注入 Giscus 评论的做法和色板匹配细节
