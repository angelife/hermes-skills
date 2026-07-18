# Hugo Archives Layout Gotcha

## Problem
When a page (`_index.md` or standalone `.md`) has `layout: "archives"` in its frontmatter:
- Hugo assigns `.Kind = "page"` (not `"section"`)
- `.Pages` is empty (it returns the page's children, not all content)
- Calling `.Paginate` on a page-type page **panics**: `pagination not supported for this page: kind: "page"`

## Root Cause
The `layout:` frontmatter field tells Hugo to look for a template named `archives.html` in `layouts/_default/`. If it doesn't exist, Hugo falls back to `_default/list.html`. But because `.Kind` is `"page"` (not `"section"`), the pagination helper `.Paginate` doesn't work.

## Fix
Create `layouts/_default/archives.html`:

```html
{{ define "main" }}
{{ partial "header.html" . }}
<div class="page">
  <h1>{{ .Title }}</h1>
  {{- $pages := where site.RegularPages "Section" "!=" "posts" }}
  {{- $pages = where $pages "Params.draft" "!=" true }}
  {{- $pages = sort $pages "Date" "desc" }}
  <ul class="post-archive">
    {{- range $pages }}
    <li class="post-item">
      <time class="post-date">{{ .Date.Format "2006-01-02" }}</time>
      <a class="post-title" href="{{ .Permalink }}">{{ .Title | emojify }}</a>
    </li>
    {{- end }}
  </ul>
</div>
{{ partial "footer.html" . }}
{{ end }}
```

Key points:
- Use `site.RegularPages` (not `.Pages`) to get all content
- Do NOT call `.Paginate` on a page-type page — iterate directly
- Exclude `"posts"` if archives should show only non-post content (adjust per need)
- Sort by `"Date" "desc"` for reverse chronological order

## General Rule
Any time you use a custom `layout:` value in frontmatter (e.g., `archives`, `changelog`, `series`), **you must create a corresponding template** in `layouts/_default/`. Hugo will NOT fall back gracefully — it uses whatever template name you specify, and if it doesn't exist, it falls back to `_default/list.html` which may not work for page-type content.
