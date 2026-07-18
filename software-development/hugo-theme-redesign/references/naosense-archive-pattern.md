# Naosense Archive Pattern

Source: https://naosense.github.io/

## HTML Structure

### Homepage
```html
<div class="home">
  <div class="info">
    <a href="/" class="logo">Site Name</a>
    <div class="subtitle">Tagline</div>
    <div class="sns">
      <a href="/archives">Blog</a>
      <a href="https://github.com/user">GitHub</a>
      <a href="https://steam...">Steam</a>
    </div>
  </div>
</div>
```

### Archive/List Page
```html
<section class="archive">
  <h1 class="article-title">Posts</h1>
  <ul class="post-archive">
    <li class="post-item">
      <a class="post-title" href="/post-slug/">Post Title</a>
      <time class="post-date">2026-01-15</time>
    </li>
  </ul>
</section>
```

Key: **title before date** in each `li`, date is `float: right`.

## CSS Pattern

```css
/* Homepage centering */
.home {
  display: table;
  width: 100%;
  height: 100%;
}
.home .info {
  display: table-cell;
  vertical-align: middle;
  text-align: center;
}
.home .info .logo {
  font-size: 2em;
  font-weight: bold;
}
.home .info .subtitle {
  font-size: 1em;
  color: #808080;
}
.home .info .sns {
  margin: 1em auto;
}
.home .info .sns a {
  width: 55px;
  color: #999;
  display: inline-block;
}
.home .info .sns a:hover {
  color: #000;
}

/* Archive list */
.archive .post-archive .post-item {
  margin: 6px 0;
  line-height: 1.5;
}
.archive .post-archive .post-item .post-date {
  float: right;
  font-size: 80%;
  color: #808080;
}
.archive .post-archive .post-item .post-title:hover {
  border-bottom: 1px solid;
}
```

## Design Principles

1. **Vertical center on homepage** — `display: table` + `table-cell` + `vertical-align: middle`
2. **Pure list, no cards** — just title + date per line
3. **Title first, date right-aligned** — opposite of PaperMod default
4. **Sparse spacing** — 6px margin between items, not 10px+
5. **System fonts** — `-apple-system, Segoe UI, Helvetica, Arial, sans-serif`
6. **Gray aux colors** — `#999` for links, `#808080` for dates/subtitles
7. **Minimal menu** — just text links, no icons, no decorations

## Hugo Menu Integration

Add navigation as `hugo.yaml` menu entries:
```yaml
menu:
  main:
    - name: "金"
      url: "/series/information-judgment/"
      weight: 1
    - name: "木"
      url: "/series/chan-shi-lu/"
      weight: 2
    # ... etc
```

The header partial renders these from `.Site.Menus.main`.
