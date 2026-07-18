# Switching to polk-x for Minimal Archive Style

## When to Use
- Target is a "digital garden" / naosense-style minimal archive (date + title list, no cards, no summaries)
- PaperMod's default card layout or even custom overrides aren't minimal enough
- User explicitly references `naosense.github.io` as the visual target

## Why polk-x
- Ships with a minimal `list.html` that renders dates + titles as clean list items
- Has built-in CSS variables system
- `head.html` loads `/css/style.css` as an override file — perfect for project-specific CSS
- No blog cards, no hero banners, no decorative elements

## Migration Steps

1. **Add polk-x as submodule:**
   ```bash
   git submodule add https://github.com/leviathan0992/hugo-theme-polk-x.git themes/polk-x
   ```

2. **Update `hugo.yaml` theme:**
   ```yaml
   theme: polk-x
   mainSections: ["columns", "posts", "series"]
   ```

3. **Delete old theme's layout overrides:**
   ```bash
   rm -f layouts/_default/baseof.html
   rm -f layouts/partials/header.html
   rm -f layouts/partials/footer.html
   ```
   **CRITICAL:** This is mandatory. Old `baseof.html` overrides the new theme's rendering pipeline.

4. **Override templates in `layouts/_default/`:**
   - `list.html` — `if .IsHome` branch for五行 navigation, else reuse polk-x's minimal list
   - `single.html` — handle cover frontmatter as both map and string
   - `index.html` — optional if list.html covers homepage

5. **Create `static/css/style.css` for overrides:**
   - Must use `!important` on font-family, font-size, line-height
   - Target: `html, body, .container` selectors for maximum specificity
   - Define五行 navigation styles here

## Common Issues
- **Cover map vs string:** polk-x may expect cover as string URL; handle map type in `single.html`
- **Missing partials:** polk-x has its own partial chain; don't reference PaperMod partials like `post_meta.html`, `header.html`
- **CSS not loading:** polk-x loads `static/css/style.css` from `head.html`; ensure file exists and path is correct
- **Article list filter too narrow:** DO NOT use `where .Site.RegularPages "Section" "in" site.Params.mainSections` in `list.html`. This is fragile when sections don't exist or are misnamed, and commonly causes missing articles (e.g., series articles not appearing). Instead, use `site.RegularPages` directly, which always includes all content pages regardless of section naming or config drift. The filter is the most common cause of "list shows only some articles" after a theme switch.

## Pitfalls in Polk-x Specific Context
- **`site.RegularPages` vs filtered `.Pages`:** polk-x's default `list.html` uses `.Pages` which works per-section. But when your site has multiple content types (posts, series, columns) that all need to appear in the archives, use `site.RegularPages` to collect ALL content pages. Filtered section queries break silently when a section directory is empty or missing.
