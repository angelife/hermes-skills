---
name: hugo-theme-redesign
description: "Redesign Hugo sites (PaperMod, polk-x, or other) for cleaner, content-first style. Covers template overrides, CSS rewrites, navigation simplification, theme switching, and build verification. Use when asked to change a Hugo site's look/feel, simplify navigation, modernize layout, or move toward a reference design."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [hugo, theme, redesign, papermod, polk-x, css, template, web-design]
    related_skills: [plan, subagent-driven-development, systematic-debugging, angelife-mobile-remote-workflow]
---

# Hugo Theme Redesign

## Overview

Redesign a Hugo site's visual style, layout, and navigation. Works with PaperMod, polk-x, and other Hugo themes. Covers template overrides, CSS rewrites, navigation simplification, and build verification. Use when asked to change a Hugo site's look/feel, simplify navigation, move toward a reference design, or switch themes.

**Reference style example:** 阳志平 website (内容优先, 长文阅读友好, 知识库气质).

## When to Use

- User wants to change a Hugo site's look/feel
- User references a design target site ("make it look like X")
- User says the site is "too busy", "too decorative", "lacks knowledge site feel"
- Navigation needs simplification
- Article reading experience needs improvement

## Pre-Flight Checklist

1. **Read prior session history and current repo state BEFORE changing anything**
   - Search session history for this repo/site first; do not re-derive workflow from scratch.
   - Inspect existing recovery procedures / CI workflow before destructive ops.
   - If the working tree is missing `hugo-site/`, `.git/`, or the normal source layout, STOP and restore history before guessing.

2. **Ensure Hugo theme source is available**
   - PaperMod is often a git submodule: `git submodule update --init --recursive`
   - Verify `themes/PaperMod/layouts/_default/baseof.html` exists before overriding anything
   - Without the theme source, your overrides may break on missing partials

3. **Read the full current CSS and templates**
   - Use `read_file` with pagination if CSS > 1000 lines
   - Identify all CSS classes used across templates
   - Don't assume class names — the theme may reference them in partials

4. **Back up existing files**
   - `cp css/<name>.css css/<name>.css.bak`
   - Don't overwrite without backup — you may need to roll back

5. **Verify Hugo binary availability and version**
   - `hugo version` — check it's v0.146.0+ (PaperMod minimum)
   - Extended build needed for SCSS/PostCSS processing
   - Some projects use a vendored hugo binary (e.g. `/opt/data/hugo`); check first

6. **Check for git repo integrity**
   - `git status` — ensure clean working tree
   - `git log --oneline -1` — verify HEAD is on expected branch
   - If repo appears empty (no commits, empty refs), recover from origin before proceeding

## Step-by-Step Workflow

### Step 1: Understand the Reference Design

Read the target design site. Note:
- Navigation structure (how many items, where they are)
- Homepage layout (list vs single-page vs hero banner)
- Typography (font families, sizes, line-heights)
- Content density (cards vs lists, spacing)
- Visual weight (shadows, borders, colors)

**Do NOT copy pixel-for-pixel.** Learn the design principles and apply them.

### Step 2: Plan the Changes

Create a plan listing:
- CSS files to rewrite (what to remove, what to add)
- Templates to override (which partials)
- Config to update (hugo.toml menu, params)
- Build verification steps

### Step 3: Rewrite CSS First

Rewrite the custom CSS file. Key principles:
- Start from the existing PaperMod CSS variables for consistency
- Remove decorative elements first (hero banners, cards, shadows, animations)
- Then add reading-friendly styles (larger line-height, proper font chain)
- Keep it under ~10KB for manageability
- Use CSS variables for theming, not hardcoded values

**CSS targets:**
- Body/base fonts and colors
- Navigation bar (simple, right-aligned)
- Article list entries (title + summary + date)
- Single article page (content width, typography)
- Footer (minimal)
- Mobile responsive rules

### Step 4: Override Templates

Know which template handles each page type BEFORE writing overrides:

1. **`layouts/index.html`** — Homepage. `list.html` does NOT handle home — it only handles sections (`content/*/_index.md`). If you override `list.html` with a五行 nav `.IsHome` branch, it will NEVER fire for the homepage. Polk-x has its own `index.html` that renders `.Pages` only (no `_index.md` Markdown content). To add五行 nav to home: create `layouts/index.html` and render `{{ .Content }}` from `_index.md` Markdown.
2. **`layouts/_default/list.html`** — Section pages (series, categories, tags). This is where `.IsHome` is FALSE. Use polk-x's `.RelPermalink` pattern (never `.Permalink` — `.Permalink` returns absolute URLs with `baseURL`, breaking local dev previews).
3. **`layouts/partials/header.html`** — Simplified navigation
   - Remove theme toggle, language switch, logo icons
   - Keep: logo + menu items
   - Menu items come from `hugo.toml` `[[menu.main]]`

2. **`layouts/partials/footer.html`** — Minimal footer
   - Keep: copyright line
   - Remove: "Powered by Hugo & PaperMod"
   - Keep: scroll-to-top if desired

3. **`layouts/index.html`** — Homepage
   - From decorative single-page → article list
   - Show: title, summary (2 lines), date, series/category badges
   - Pagination: 15 posts per page

4. **`layouts/_default/list.html`** — List pages
   - Unified: category pages, series pages, tag pages
   - Same list layout as homepage

5. **`layouts/_default/single.html`** — Article pages
   - Content width: ~720px max
   - Font chain: Songti SC first, then system sans-serif
   - Line-height: 1.8-1.9
   - Code blocks: gray background, rounded corners, horizontal scroll
   - Blockquotes: left border line, no background
   - Cover images: max-height 480px, centered, rounded
- **`layouts/_default/archives.html`** — Custom archive layout (optional)
  - If you want a naosense-style timeline (title + date per line), create this template
  - Use a simple list: `- [title](url) YYYY-MM-DD` — no summary, no cover
  - **CRITICAL:** If the page uses `layout: "archives"` in frontmatter, `.Kind` is `"page"` not `"section"`. `.Paginate` will PANIC. Use `site.RegularPages` and iterate directly (no pagination). See `references/hugo-archives-layout-gotcha.md`.
7. **`layouts/_default/list.html`** — List pages with different modes:
   - **Card mode (default PaperMod):** cover + title + summary + date — good for blog aggregation
   - **Minimal list mode:** title + date per line — matches naosense/yangzhiping style
   - **Compact list mode:** title + date + one-line summary — balanced information density

### Step 5: Update Hugo Config

Simplify `hugo.toml` menu:
- Remove redundant menu items
- Use `weight` consistently for ordering
- Keep only essential navigation

### Step 6: Build and Verify

```bash
cd hugo-site && hugo --gc --minify
```

Check:
- Build succeeds with no errors
- Homepage shows article list
- Article pages render correctly
- Navigation works
- Pagination works on list pages

**Common build errors:**
- `.Params.cover` is a map (frontmatter with alt/caption) not a string URL → handle with `{{ if reflect.IsMap .Params.cover }}`
- `plainify` returns `template.HTML` type, NOT `.Page` → `.Truncated` does not exist on `template.HTML`
- Missing partials in overrides → check theme source
- CSS classes referenced in templates but removed from CSS → add them back
- Empty menu causes PaperMod header to render empty `<ul id="menu">` and a hamburger button → hide with CSS `#menu { display: none !important; }` and `.nav-toggle { display: none !important; }`

## Pitfalls

- **Don't modify theme source files.** Always override in `layouts/` (your project's layouts directory takes precedence).
- **Don't `git add .` in the site repo.** Use precise `git add` as per angelife rules.
- **CSS class names must match templates.** After rewriting CSS, cross-check every class used in templates.
- **`cover` frontmatter may be a map.** Some articles use `cover: {image: "...", alt: "...", caption: "..."}`. Handle both string and map types — see `references/cover-param-map-handling.md`.
- **Archive/series pages need their own templates** if you want different layouts (e.g., timeline archive).
- **PaperMod's `baseof.html` defines the `<html>` wrapper.** If your overrides reference partials not in baseof's chain, they'll fail.
- **Don't remove the theme toggle JS entirely.** PaperMod's footer includes theme toggle scripts. If you remove the toggle button but keep the JS, the page works but wastes bytes. Either remove both or keep both.
- **`.Pages.GroupByDate` does NOT work on plain `_index.md` archive pages.** It only works for taxonomy/term pages where `.Pages` is populated. For custom archive pages created via `_index.md`, use `site.RegularPages` as the source: `{{ $pages := where site.RegularPages "Type" "posts" }}` then `.Pages.GroupByDate`.
- **`.Summary | plainify` returns `template.HTML`, NOT `.Page`.** Do NOT try `{{ .Summary | plainify }}.Truncated` or `if .Truncated` — that field does not exist on `template.HTML`. Use `truncate N` directly on the plainify output. If you need the truncation indicator, just append "..." unconditionally.
- **PaperMod header renders hamburger button even with empty menu.** If you remove all `[[menu.main]]` entries, the `<ul id="menu">` is empty and PaperMod may still render a mobile hamburger toggle. Add CSS: `#menu { display: none !important; } .nav-toggle { display: none !important; }`.
- **CRITICAL — "Make X the only version" is ambiguous.** When user says "把 [kindle/paper/mobile] 版本做成唯一版本" or "use X as the only version", DO NOT bulk-replace `baseof.html`/`header.html`/`comments.html`/`search.html`. Two interpretations exist:
  1. **Make X the default output** (keep dual-output, just change defaults)
  2. **Replace everything with X's rendering pipeline** (delete the other version's templates)
  Always ask which one before touching `baseof.html`. A bad interpretation can wipe out navigation, search, comments, breadcrumbs, and cover system in a single edit, and the user only notices 2-3 rounds later when they ask about a missing menu or 404 cover images.
- **CRITICAL — Read `baseof.html` BEFORE any custom index/single override.** If `baseof.html` has been customized to a minimal Kindle-style template (no PaperMod header/footer), then adding custom `index.html`/`single.html` will silently MISS PaperMod navigation, breadcrumbs, post_meta, comments, anchored headings, and post_nav_links. Either restore PaperMod baseof OR explicitly add all those partials to your custom templates. For the angelife project the preferred pattern is in `references/coupling-with-angelife-mobile-remote-workflow.md`.
- **PaperMod `single.html` must call `{{ partial "cover.html" . }}`** for cover images. Don't try to render covers with `<figure><img src="{{ .Params.cover | relURL }}"></figure>` — it produces 404s on page-bundle relative-path covers like `cover.png`. PaperMod's `cover.html` partial does `.Resources.ByType "image"` lookup of the page bundle. See `references/cover-param-map-handling.md` for the full pattern.
- **CRITICAL — Switching Hugo themes: delete old theme's `layouts/_default/` overrides.** When switching from one theme to another (e.g. PaperMod → polk-x), any `layouts/_default/baseof.html` or `layouts/partials/*.html` from the old theme MUST be deleted first. Otherwise the old theme's `baseof.html` will still be found in the project's `layouts/` directory and override the new theme's rendering, causing double header/footer, missing CSS, and broken layouts. Always `rm layouts/_default/baseof.html` after theme switch.
- **Custom `layout:` frontmatter creates page-type pages.** When you set `layout: "archives"` (or any custom name) in frontmatter, Hugo assigns `.Kind = "page"` instead of `"section"`. This means: (1) `.Pages` is empty — it only returns children, (2) `.Paginate` will PANIC with `pagination not supported for this page`. Always create a matching template and use `site.RegularPages` directly instead of `.Paginate`. See `references/hugo-archives-layout-gotcha.md` for the full pattern.

- **Archives dedup failures must be diagnosed at the field level, not just observed as a symptom.** Before declaring that dedup logic "failed" or "doesn't work", verify the exact values of the chosen key fields. For example, if dedup uses `.File.ContentBaseName`, print the actual `.ContentBaseName` values for the suspected duplicate pages in rendered output. Without this verification, you cannot distinguish between "logic is wrong" and "key fields are incompatible from the start". The most common trap: two duplicate-looking pages have different base names because one lives under a leaf-bundle directory and the other under a taxonomy file with a different filename/slug — they will never collide on a filename-based key.

- **Distinguish source duplication from template/render duplication before choosing a fix.** This determines the entire repair strategy:
  - Source duplication: the same article content exists as two separate markdown files in different sections. Fix: delete or redirect the duplicate source file, or prevent one from rendering a page.
  - Template/render duplication: one source file appears twice in rendered output because the template iterates both `site.RegularPages` and taxonomy terms without filtering. Fix: adjust template `Range` logic or `.Kind` filters.
  Applying the wrong fix causes data loss or incomplete coverage.

- **Prefer preventing duplicate page generation over post-render filtering.** If a content file's only purpose is taxonomy assignment (e.g., a markdown file in `content/series/<term>/` exists solely to attach an article to a series), use frontmatter build controls instead of relying on archives/list templates to filter it out afterward:
  ```yaml
  _build:
    render: never
    list: always
  ```
  This removes the duplicate page from the URL space at the source. It also keeps taxonomy aggregation working because `list: always` still includes the page in term listings. Only fall back to template-side dedup if the site intentionally needs both pages but wants archives to show one entry.

- **Before removing taxonomy-term URLs, check for external references.** Some `/series/<term>/<slug>/` URLs may have been shared externally or indexed by search engines. Before switching any URL from "rendered" to "never", audit whether inbound links exist. If they do, add a redirect rather than returning 404. Treat this as a migration check, not an optional cleanup.

- ** Verify rendered output, not just build success.** After archives or dedup changes, the only valid proof is inspecting the rendered page content (`public/archives/index.html` or `curl http://localhost:1313/archives/`). A `hugo` exit code of 0 is necessary but not sufficient — the page can still contain duplicate entries.
- ** Don’t stop verifying at `/archives/` alone when the user reports duplicates.** In Hugo, duplicate-looking entries can come from separate content-source files with different section paths (`content/posts/...` and `content/series/<term>/...md`) that share the same date, title substring, or near-identical body; rendered archive views merge them. If the rendered archive still shows repeated title/date rows, grep and diff the source files across `posts/` and the relevant `series/` directories instead of re-counting archive HTML.

- **Debug artifacts can silently become 1-byte empty files.** When creating temporary templates or content pages for debugging (e.g., `content/debug-cbn-test/_index.md`, `layouts/debug/single.html`), Hugo may generate the target output path but write zero rendered content into it. The file exists and `hugo` exits 0, but the artifact is useless. Always verify debug output with `ls -l <path>` and `wc -c <path>` immediately after build — a 1-byte file means the debug path was not actually exercised. When this happens, do not keep repeating the same template-injection pattern; switch to a proven debugging path instead.

- **LocalSend on macOS is primarily a GUI app; direct CLI/API automation is unreliable.** Homebrew installs `LocalSend.app` into `/Applications/`. The app listens on TCP 53317, but probes can still hit 403/empty responses, indicating auth/CSRF middleware. For this user's actual workflow — get a file from Mac to iPhone — the practical path remains: use the LocalSend GUI or OS-native sharing. Do not spend cycles trying to reverse-engineer an undocumented local API when the user core need is just "send this file."
- **`mainSections` filter is fragile — avoid it in `list.html`.** Filtering by `where site.RegularPages "Section" "in" site.Params.mainSections` silently drops articles when a section directory is empty, missing, or misnamed (e.g., `series/` vs `posts/`). After a theme switch or content reorg, the most common "missing articles" symptom is caused by this filter. Use `site.RegularPages` directly instead. See `references/polk-x-theme-switch.md` for details.
- **User verbal patterns that require immediate verification instead of reported completion:** When user says "没看到更改效果 你核查一下" or "够了/不要解释了", the retry pattern must be: (1) immediately verify the specific change in rendered output, not just build success, (2) provide one-line confirmation of the actual state found, (3) do not ask user to refresh or recheck themselves. Reporting "done" without verification is itself a bug. See `references/local-preview-verification.md` for verification patterns.
- **TOML config overrides YAML when both exist.** Hugo picks `.toml` over `.yaml` when both are in the same directory. If menus, params, or other settings were added to `hugo.yaml` but the site uses `hugo.toml` with the same keys, the TOML values silently win. Always check which config file Hugo is actually loading. Use `hugo --config hugo.toml` explicitly, or `grep` the config key in all `.toml` files. See `references/hugo-config-priority.md`.
- **`layouts/index.html` vs `layouts/_default/list.html` separation is a common trap.** `.IsHome` is only true for `content/_index.md` (the homepage), which renders via `layouts/index.html` (polk-x's own), NOT via `_default/list.html`. If you put五行 nav logic in `list.html` inside an `.IsHome` branch, it will NEVER render for the homepage. To add五行 nav to home: override `layouts/index.html` AND render `.Content` to include `_index.md` Markdown body. Conversely, section pages (like `series/information-judgment/_index.md`) ARE handled by `list.html` with `.Kind = "section"`.
- **Use `.RelPermalink` not `.Permalink` in overrides.** `.Permalink` always resolves to the full absolute URL (e.g., `https://angelife.github.io/posts/foo/`), which breaks local dev previews running at `http://localhost:1313/`. Polk-x's own templates use `.RelPermalink` which returns `/posts/foo/` — correct for both local and production.
- **Polk-x's `index.html` does NOT render `_index.md` Markdown content.** It only renders `.Pages` (article list). If your homepage has content like五行 navigation links in `_index.md`, you must explicitly render `{{ .Content }}` in your custom `layouts/index.html`, otherwise all Markdown content disappears.
- **CRITICAL — Multi-persona distillation ("蒸馏X") must be analytical, not ventriloquism.** When user asks to "蒸馏 [person]" and run a debate, capture their *analytical frame, idioms, core propositions, and how they would likely respond to others* — NOT first-person agitprop declarations. Hard rule: never write "I declare support / I oppose / the people stand with me" speeches for currently-powerful top leaders or historically-violent figures (current top leadership of CN/US/RU/IR, Mao, Pol Pot, Hitler, Stalin). Safe phrasing: "X's analytical frame would lead them to argue Y" or "X would likely respond to Z by saying A". Preserves educational value without the agent authoring propaganda declarations on behalf of dangerous or living-power figures. See `references/multi-persona-distillation-rules.md`.
- **Never claim a file is written without `ls` + `wc -c` proof.** When asked to write a new article (>1000 Chinese characters), the long stream is prone to mid-flight truncation by Hermes gateway. The model's natural failure mode is to *output the success message anyway* ("✅ 已发布") even though the `write_file` tool call was cut off before execution. This produces a 3-4 hour debugging loop where the user thinks files are landing but `ls` finds nothing. **Mandatory discipline:** (1) `[WRITE TASK] 路径/字数/段数/模型` announcement BEFORE writing; (2) after EVERY `write_file`/`append_file`, run `ls -la && wc -c` and read the actual output; (3) NEVER say "已发布/已写入/已完成" unless `ls` confirms the file; (4) on stream truncation, the ONLY honest response is "上次 stream 被截断，文件未写入，下面重新来过". See `references/large-content-write-protocol.md` for the full chunked-write protocol and recovery recipe.

- **Title shortening must preserve uniqueness.** If user asks for titles ≤10 chars, do NOT blindly slice the first 10 characters. That collapses distinct articles into identical short titles. Instead, use the article's existing slug/tag/sequence identifier as the tie-breaker. For series like 教会史续1..19, the short title must include the sequence tag, e.g., `轨迹1`/`轨迹2`/…/`轨迹18`, not just `轨迹` repeated 19 times. Rule of thumb: when shortening, prefer `head + sequence/tag` over `head only` if collision risk exists.
- **Polish-aware chunked writing for Chinese long-form content.** For a 17,000-character Markdown article on this project, the working pattern is: split into ≈1000-character segments, first segment via `write_file` (overwrite mode), subsequent segments via `append_file` (append mode), `wc -c` after each segment to confirm byte count grows monotonically, final `cat` to show full text. Avoid `minimax`/`minimax-m3` for files >800 chars when alternatives exist — it has the highest stream-truncation rate observed on this user's setup. Prefer `xopqwen36v35b` (Qwen 3.6 35B) for prose generation when fallback chain is stable.

- **MANDATORY: load this skill before any "publish to local site" or "publish to website" task.** When user says "把这些都写成文章发布到本地站点", "publish to angelife", "write a new article", "发布", "公开发布", or anything implying file creation or deployment in `hugo-site/content/`, you MUST `skill_view(name="hugo-theme-redesign")` first. Then read `references/large-content-write-protocol.md` and `references/angelife-publishing-workflow.md`. Then state `[WRITE TASK] 路径/字数/段数/模型`. Then write. Then follow the full publish workflow from `references/angelife-publishing-workflow.md`. **Do not skip the skill load.** The protocol exists; it just gets ignored when the skill isn't loaded. This was the root cause of the 2026-06-14 three-hour hallucination cascade (agent claimed "已发布" 5+ times with `ls` showing only 3 files) and the 2026-07-01 partial-push (only source markdown committed, missing rsync + tag steps — agent said "已发布" but the repo root had no generated files).

- **CRITICAL — Tse's "本地预览" means: run `hugo server --buildDrafts` on the Mac and open it in a browser.** When user says "本地预览" or "本地站点预览", his default expectation is: start a Hugo dev server (`hugo server --buildDrafts -p 1313`) that he can open in Safari at `http://localhost:1313/` and browse with navigation, categories, series pages, and individual article pages. Do NOT respond by showing file paths (`/Users/macos/...`), listing directory contents, or describing build output stats — those are NOT what he means by "预览". If you show file paths first, he will correct you: "本地预览 就是 本地网站预览的意思". **First action on hearing "预览" for Tse: kill any existing hugo server -> start `hugo server --buildDrafts` -> confirm it's responding via `curl` -> tell him the URL.** The `--buildDrafts` flag is essential because restored historical articles have `draft: true` frontmatter and won't appear without it. If the files are already on the Mac via bind mount (which they always are), do NOT re-copy them — just start the server.
- **Local-preview recovery rule for this repo:** If the site should be previewed from `hugo-site/`, verify that directory and `hugo.toml`/`hugo.yaml` exist before serving. If they're missing but a live dev server is already running on another port, treat the existing `hugo server` process as state to inspect first instead of immediately starting a second server or fallback to `python3 -m http.server`. Using plain `python3 -m http.server` on the repo root bypasses Hugo rendering and causes category/series/tag pages to look wrong or empty; that substitution is considered a regression here.

- **MANDATORY: ask "本地预览还是公开发布" before writing any article that mixes political/cult/religion/sensitive themes.** User has explicitly stated "反正我自己看" / "我要放在本地站点里看" / "发布到本地网站上去" — this means LOCAL `hugo server` preview on the user's machine, NOT `git commit` and NOT `git push`. The default publishing target when user says "本地" is: write to disk → user runs `hugo server` locally to read → no git, no push, no remote deployment. Even when content is politically sensitive (邪教, 反政府, 政治矛盾), if the user said "仅本地", do not push to GitHub Pages even after writing it. **HOWEVER, "本地" does NOT grant permission to relax content quality.** The user is literately capable — content written for self-reading must still be coherent, factually careful, and free of obvious hallucinated quotes. Private ≠ sloppy. See `references/private-content-vs-published-content.md`.

- **Infer audience-safety rules from explicit framing, not from topic alone.** When user says "不要顾虑写 反正我自己看" + "本地站点" (combined), the local-only framing rewrites the audience-safety calculus: political/religious content that would be inappropriate to publish under the user's identity is acceptable for local self-reading. Do NOT trigger over-cautious "红线" warnings on politically adjacent content when the user has confirmed (a) the deliverable target is local and (b) the audience is themselves. The earlier mistake pattern in this skill was treating "本地" as a synonym for "low-stakes" and skipping all careful writing — the corrected pattern is: keep writing quality high, drop the political-risk over-coaching.

- **Q: When user says "发布到本地网站上去" or "发布到 angelife/github 通过 github pages" — which is it?** When in doubt, RETAIN the default that 本地 = hugo server on the user's machine, NOT github.io. Reasons: (1) github.io requires `git push origin main` which the user has explicit veto over ("暂停 git 操作", "禁止执行任何 git 操作"); (2) the user has historically run preview before push; (3) "angelife.github.com" as a directory on disk is the live working tree, and writing into it does not equal pushing. If user wants push, they will say "git push" or "上线" or "deploy" — those words are unambiguous. Default to NO PUSH on any ambiguity.

- **`append_file` is not in the agent's tool set.** The Hermes agent has `write_file` (overwrite only) and `terminal` (single command, no heredoc). User-supplied protocol steps that say `cat >> file << EOF` cannot be executed as-written — they fail or simulate success without execution. When the user's protocol contradicts the actual tool surface, flag it BEFORE Step 1, propose an A/B alternative, and only proceed after user picks an adapted path (e.g., "write_file whole-file in one go" instead of chunked append). The earlier mistake was silently falling back to write_file while the protocol logs claimed append_file had run — this is a SUBTLE form of the "声明假成功" anti-pattern.

- **Heredoc-style multi-segment shell appends may produce silent no-ops on this user's terminal backend.** When `printf '...' >> file` or `cat >> file << EOF` is the prescribed step and the terminal returns no error BUT `wc -c` does not grow, the most likely cause is shell escaping/quoting failure or the terminal tool sanitizing input. Re-verify with `wc -c` AND `tail` after each append. If size doesn't grow, do not pretend success — switch to single write_file with full content, and note in chat that the protocol was deviated from for tool-platform reasons. Audit: 2026-06-14 session lost ~90 minutes to silent no-op appends.

- **When switching to "B 我推荐" mode (single write_file overwrite of full content), still get the chunked-write discipline.** The "let me write the whole file at once" path violates the spirit of the chunked-write protocol but is acceptable IF: (1) the whole content is ≤3000 Chinese characters (fits in one tool response without stream truncation risk on most backends), (2) the user has explicitly chosen this path (i.e., you proposed it and they typed "B"), (3) you announce `[WRITE TASK]` with path/字数/模型 before the write, (4) you run `wc -c` immediately after to confirm byte count, and (5) you do NOT claim "已发布" — you claim "已落盘" or "一次性写入完成" only after `wc -c` verification.

- **"Stream 截断后" 强制行为: 不要继续假装成功.** When a turn ends mid-stream without you receiving a `write_file` tool result, the next turn's FIRST sentence MUST admit the file may not be on disk. Run `ls <target_dir>` and `wc -c <target_file>` before saying anything about content. Never say "上一篇已经写好了" or "as I wrote earlier" without `ls` proof. The user loses 30-60 minutes per hallucinated "as I wrote earlier" because they trust the agent and don't immediately re-check.
- **Polk-x `dateFormat` config is decorative — dates are hardcoded in templates.** Setting `params.dateFormat` in `hugo.yaml` has NO effect on polk-x. You must patch BOTH the theme templates AND any project-level override templates in `layouts/`. The project's own `layouts/` directory takes precedence over the theme, so unless both are patched, the change won't appear. At minimum search all `layouts/` and `themes/polk-x/layouts/` for `.Date.Format "2006-01-02"` — likely candidates include `index.html`, `_default/list.html`, `_default/single.html`, `_default/archives.html`, `posts/single.html`, `columns/list.html`, and `kindle/list.html`. See `references/polk-x-date-format-handling.md` for the exact fix and the complete file list.
- **"真的好了" is a verification trigger, not a vague query.** If the user asks "好了？", "真的好了？", "刷新也没有啊", or any similar sentence, immediately re-verify the specific change in rendered output rather than re-explaining what was changed. Build success is necessary but not sufficient; inspect the actual HTML from `public/` first. Do not answer "好了" unless the rendered artifact contains the expected marker.
- ** Archives dedup mismatch: when URL-level checks show no duplicates but user insists duplicates exist, stop re-running identical checks.** Either sample article bodies and hash-compare them, or ask the user to name one specific title/URL pair. Continuing to claim "没有重复" after the user has said "没解决" turns their frustration into feedback that you are not actually searching for the right thing.
- ** Forcing Giscus theme to `light` works for color consistency.** Do not rely on `preferred_color_scheme` when your brand CSS locks `:root`/container backgrounds to `#FAFAF7`; explicitly render `data-theme="light"` in the iframe loader.
- ** Coverage gap for comments partials.** Adding `partial "comments.html"` to only one single-page template causes silently missing comments on pages rendered by other templates. After adding comments, grep `layouts/` for every `single.html` and ensure ALL article-type templates include the partial. The angelife site has both `layouts/posts/single.html` and `layouts/_default/single.html`, and `series/*` uses the latter.
- **After config/template changes, self-verify with `curl` before reporting "done".** Do not ask the user to "refresh and check" or "按 ⌘R 刷新查看". If the change isn't visible, their reaction is "没看到更改效果 你核查一下" — they expect you to have already verified the rendered output. Always:
  1. Rebuild or confirm the dev server auto-rebuild: `hugo --gc --buildDrafts`
  2. Verify the specific change in rendered HTML: `curl -s http://localhost:1313/posts/ | grep -o '<time[^>]*>.*</time>' | head -5`
  3. Only then tell the user the change is live
  The verification must prove the specific change is visible in rendered output, not just that the build succeeded with 0 errors.
- **CSS override strategy for themes with their own `style.css`.** If the target theme loads its own `static/css/style.css` (like polk-x does via `<link href="/css/style.css">` in `head.html`), your project's `static/css/style.css` will be the SAME file loaded by the theme. Use `!important` on critical properties (font-family, font-size, line-height) that must override the theme's defaults. Without `!important`, the theme's own rules may have higher specificity and silently win. Example: `html, body, .container { font-family: "Noto Serif SC", serif !important; font-size: 17px !important; }`

- **Cover generation via free API fallback (Pollinations.ai).** When paid image generation APIs (Agnes, FAL, KEYLESS, etc.) return 401, exceed budget, or are unavailable, Pollinations.ai provides free cover image generation via simple HTTP GET — no API key, no registration required. URL format: `https://image.pollinations.ai/prompt/{prompt}?width=1200&height=630&nologo=true`. Produces 1200×630 JPEG covers (25-97 KB) suitable for Hugo `cover:` frontmatter. See `references/pollinations-ai-cover-generation.md` for batch workflow, prompt templates by article category, and verification steps.

- **CRITICAL — Site domain is `angelife.github.io`, NOT `.com`.** The GitHub repo is named `angelife.github.com` but GitHub Pages publishes to `angelife.github.io`. Hugo's `baseURL` is also set to `.io`. When providing a URL for a published article, linking to it, or referencing the site, ALWAYS use `https://angelife.github.io/...`. Using `.com` is the most common repeated error pattern — the user is visibly frustrated by it. When in doubt about domain, check `hugo.toml`'s `baseURL` field.

- **YAML frontmatter `---` delimiter conflict with article body.** When a Markdown article body uses `---` (three dashes) as a section separator or horizontal rule, Hugo's YAML parser consumes it as the frontmatter closing delimiter, then fails on the text after it with `ERROR ... YAML: line N: did not find expected key`. **Fix:** Ensure the frontmatter has a proper closing `---` before any `---` in the body. Alternatives: use `***` or `___` as markdown section separators instead of `---`; or place the closing `---` on a blank line immediately after the last frontmatter key-value pair. **Detection:** If Hugo build fails with a YAML error pointing to a line number inside the article body, the most likely cause is a `---` in the body consumed as frontmatter terminator. Run `head -25 <article>.md` and verify the frontmatter has an explicit closing `---` line before any body `---`. This can also silently corrupt frontmatter without build errors if the body `---` is followed by lines that happen to parse as valid YAML — doing `head -25` to check is always safer than assuming.

## Known Bugs & Edge Cases

### Cover parameter may be a map, not a string URL

Some articles define `cover` in frontmatter as:
```yaml
cover:
  image: /images/cover.png
  alt: "Cover text"
  caption: "Caption"
```

Instead of a plain string:
```yaml
cover: /images/cover.png
```

**Handle both types in templates:**
```html
{{ $cover := .Params.cover }}
{{ if reflect.IsMap $cover }}
  {{ $cover = $cover.image }}
{{ end }}
{{ if $cover }}
  <img src="{{ $cover | absURL }}" alt="{{ with (index $.Params.cover "alt") }}{{ . }}{{ end }}">
{{ end }}
```

### Don't remove too much visual hierarchy

**Pitfall:** Going from "decorative" directly to "pure minimal" in one shot strips too much — the site loses its identity and looks like a generic template. This is the most common failure mode.

**Balance principle:** Blend reference styles rather than copying one. A good formula:
- Reference style 40% + Original identity 30% + Theme base 30% = unique but recognizable

**Key identity elements to preserve:**
- Thematic structure (e.g., 五行 categories) — use as navigation badges
- Site voice and tagline
- Any unique section structure that users recognize
- Cover images and any existing branding assets

**After stripping elements, ask:**
- Can a user identify what this site is about within 3 seconds?
- Is the site's thematic structure visible on the homepage?
- Would a returning reader feel at home?

### Cover image gap: files on disk but articles don't reference them

After restoring historical articles from git history or Blogger migration, `static/images/posts/` may have `cover.png` files for every article, but the restored articles' frontmatter has NO `cover:` field. This means images are deployed but invisible — Hugo's cover template never activates. **Always run the detection script from `references/cover-image-gap-detection.md` after any article-restoration operation** to check whether cover files and article frontmatter are in sync. The mismatch is silent: no build warning, no 404, just an empty visual.

### Pagination may need custom layout

PaperMod's default list pagination uses a simple numbered style. For knowledge sites with long archives, consider a "load more" or year-grouped archive layout instead. Create a custom `layouts/_default/archives.html` if the default pagination doesn't fit.

## Reference: File Modification Order

```
1. css/angelife-brand.css    (visual foundation)
2. layouts/partials/header.html  (navigation)
3. layouts/partials/footer.html  (footer)
4. layouts/index.html           (homepage)
5. layouts/_default/list.html   (list pages)
6. layouts/_default/single.html (article pages)
7. hugo.toml                    (config/menu)
8. Build test
```

CSS must be written first so template overrides can reference the new class names.

## Giscus / Comments Integration Workflow

Use when the user asks to add comments, discussion threads, or "动态功能" to a Hugo site — especially when the previous comment backend becomes unavailable.

- **LeanCloud/Valine is deprecated.** As of 2026-07-05, LeanCloud sunset public Valine hosting. Do not install or configure Valine on a new site. If the user asks for "评论" and you find Valine config, immediately propose Giscus or self-hosted alternatives. Reference: https://docs.leancloud.cn/sdk/announcements/sunset-announcement
- **Preferred path for github.io sites: Giscus.** It uses GitHub Discussions as backend, requires no separate server, and fits Hermes-authored public sites.
- **Provider-ready pattern.** A provider counts as ready only when ALL required IDs are filled. For Giscus: `repoId` AND `categoryId` must both be non-empty. If either is missing, fall through to the next provider instead of rendering an empty widget.
- **Branch priority.** Giscus first, then any fallback. Do not let global `enabled = true` alone activate a provider with empty credentials — users frequently copy snippets with partial IDs.
- **Coverage pitfall.** If you add a comments partial to one single-page template (e.g. `layouts/posts/single.html`), remember that other content types may use different templates like `layouts/_default/single.html`. Always grep for all `single.html` files across `layouts/` and confirm every article-type template includes the comments partial. Missing one layout causes some pages to silently have no comments.
- **Template injection.** Add comments partial to article layouts, not home/list pages. Verify by inspecting rendered HTML for the provider's script node (`giscus.app/client.js`, `id="vcomments"`, etc.).
- **Verification pattern.** After enabling, do a temp-render check on 1 actual article page per layout type before claiming success. Build success alone is insufficient — inspect rendered output from the specific URL the user opened.
- **Push discipline.** After config + template changes, commit ONLY those files. Do not bulk-add the repo; honor the Angelife repo hygiene rule. Then push so GitHub Pages can redeploy.

See `references/giscus-integration-workflow.md` for the exact giscus parameter mapping, fallback template logic, and the temp-enable verification recipe used in the angelife.github.com deployment on 2026-07-05.

## Support Files

- `references/cover-param-map-handling.md` — How to handle cover frontmatter that may be a map, not a string URL
- `references/cover-image-gap-detection.md` — Detect and reconnect orphaned cover.png files on disk when restored articles have no `cover:` frontmatter (files exist but are invisible)
- `references/digital-garden-patterns.md` — Templates and CSS patterns for Digital Garden / naosense style (hero homepage, timeline archives, minimal lists, reduced covers, garden color system)
- `references/local-preview-verification.md` — Hugo server setup, verification patterns, and common preview issues
- `references/angelife-publishing-workflow.md` — Complete production publish workflow for angelife.github.com: build → rsync → git commit generated files → tag (from CODEX_HANDOFF.md)
- `references/git-refs-wiped-recovery.md` — How to recover a repo where refs were wiped but pack files survive
- `references/empty-taxonomy-mainSections-and-baseof-coupling.md` — Two distinct root causes for "list page renders empty"; diagnostic decision tree
- `references/coupling-with-angelife-mobile-remote-workflow.md` — Angelife remote workflow coupling notes
- `references/polk-x-theme-switch.md` — Complete migration guide from PaperMod to polk-x for minimal archive/digital garden style
- `references/hugo-archives-layout-gotcha.md` — Why `layout: "archives"` + `.Paginate` panics; how to fix with `site.RegularPages`
- `references/naosense-archive-pattern.md` — HTML structure and CSS for naosense-style minimal archives: `section.archive > h1.article-title + ul.post-archive > li.post-item` with title first and date floated right
- `references/hugo-config-priority.md` — TOML overrides YAML when both exist in the same directory
- `references/hugo-search-page.md` — Standalone full-HTML template pattern for search pages to avoid header duplication and empty menus
- `references/pollinations-ai-cover-generation.md` — Free cover image generation via Pollinations.ai HTTP GET API (no key needed, paid-API fallback). Includes batch workflow, prompt templates by article category, rate-limiting notes, and YAML delimiter conflict warning.
- `references/session-2026-06-14-publish-cascade.md` — Full failure-mode recap with tool-platform realities (`append_file` not in tool set, heredoc-silent-fail policy)
- `references/session-2026-06-14-24-voices-publish-cascade.md` — End-to-end session recap of the 5-article 24-voices cult-debate write publish cascade including recovery recipe
- **references/title-shortening-protocol.md** — Safe shortening rules for Hugofrontmatter titles: keep uniqueness, use slug/sequence tie-breakers, avoid blind truncation collisions.
- **references/angelife-repo-hygiene.md** — Deduplication and cleanup rules for `angelife.github.com`: preserve `old-site/`, treat `hugo-site/` as source of truth, remove duplicate generated top-level dirs, and avoid polluting commits with `.DS_Store`/environment noise.
- **references/hugo-series-posts-deduplication.md** — Diagnosis and safe-removal recipe for duplicate articles stored under both `content/posts/...` and `content/series/<term>/...md`; includes verification script for rendered archive `public/archives/index.html`.
