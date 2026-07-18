# Digital Garden Page Patterns (naosense / yangzhiping style)

## Overview

When a Hugo site is being converted to a "Digital Garden" or essay-first knowledge base, the key design principle is **minimal information density per page** — fewer elements, higher readability, no visual noise.

## Pattern 1: Hero-Only Homepage

Replace the article list homepage with a static entry page:

```html
<article class="home-simple">
  <div class="home-simple-inner">
    <h1 class="home-simple-title">Site Name</h1>
    <p class="home-simple-sub">Tagline broken into two lines.</p>
    <nav class="home-simple-nav">
      <a href="/series/entry-1/">Entry 1 label</a>
      <a href="/series/entry-2/">Entry 2 label</a>
      <!-- etc -->
    </nav>
    <footer class="home-simple-footer">
      <a href="/archives/">Archives</a> ·
      <a href="/search/">Search</a> ·
      <a href="/about/">About</a>
    </footer>
  </div>
</article>
```

**When to use:** When the homepage should act as a landing page, not a blog index. Content is discovered through series/sections or archives.

## Pattern 2: Timeline Archives

Archive page shows every post as a single line:

```html
<div class="archive-item">
  <a href="{{ .Permalink }}">{{ .Title | emojify }}</a>
  <time>{{ .Date.Format "2006-01-02" }}</time>
</div>
```

**CSS key traits:** flexbox row, title left, date right, dotted bottom border, date in monospace + gray.

**When to use:** When you have many posts and want chronological scanning without summaries.

## Pattern 3: Minimal List Pages

Series/category pages show title + date only:

```html
<div class="list-item">
  <a href="{{ .Permalink }}">{{ .Title | emojify }}</a>
  <span class="list-date">{{ .Date.Format "2006-01-02" }}</span>
</div>
```

**Not included:** cover images, summaries, reading time, author info.

**When to use:** When the list page is a discovery surface, not a content preview surface.

## Pattern 4: Single Page with Reduced Cover

Article pages keep covers but shrink them:

```html
{{ $cover := "" }}
{{ with .Params.cover }}
  {{ if reflect.IsMap . }}
    {{ $cover = .image | default "" }}
  {{ else }}
    {{ $cover = . }}
  {{ end }}
{{ end }}
{{ if $cover }}
<figure class="entry-cover">
  <img src="{{ $cover | relURL }}" alt="{{ .Title }}" />
</figure>
{{ end }}
```

**CSS:** `max-height: 280px; object-fit: cover; border-radius: 6px;`

## Color System for Digital Garden

```css
:root {
  --al-ink: #222;           /* main text */
  --al-secondary: #666;     /* date, meta */
  --al-bg: #FAFAF8;         /* warm gray-white */
  --al-border: #e8e6e1;     /* subtle lines */
  --al-link: #4a5568;       /* low-sat blue-gray */
  --al-quote-line: #4a5568; /* blockquote left line */
  --al-quote-bg: #f4f3f0;   /* blockquote background */
}
```

**Key principle:** No gradients, no bright accent colors, no rainbow theming. One accent color max.

## Typography

| Element | Font | Size | Line-height |
|---------|------|------|-------------|
| Body | Noto Serif SC, Georgia, serif | 20px | 1.9 |
| English fallback | Inter, Georgia | - | - |
| Code | JetBrains Mono | 0.85em | - |
| Content width | - | 820px | - |
| Paragraph spacing | - | - | margin-top 1.4em |

## References

- **naosense.github.io** — actual example of this style (Hexo polk theme)
- **yangzhiping.com** — Chinese knowledge site with similar aesthetic
- This pattern was applied to the **angelife** site on 2026-06-13.
