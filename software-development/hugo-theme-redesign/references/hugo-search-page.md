# Hugo Search Page — Custom Layout Pattern

## Problem

When you add a custom `content/search.md` with `layout: "search"`, Hugo matches it against `layouts/search/search.html` (exact layout match). But if you use `{{ define "main" }}` blocks with `{{ partial "header.html" . }}` inside, it may:

1. **Render two headers** — if both `baseof.html` chain and the partial add a header
2. **Have empty menu** — if the config's `menu.main` is defined in a `.toml` file that's being ignored (because a `.yaml` with no menu exists)
3. **Be invisible** — if CSS has no styles for `.search-page` and the page lacks header/footer scaffolding

## Solution: Standalone Full-HTML Template

Don't use `{{ define "main" }}` with partials for search. Write a complete HTML document directly:

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta http-equiv="X-UA-Compatible" content="IE=Edge,chrome=1">
  {{- $separator := printf " %s " (.Site.Params.separator | default "-") -}}
  {{- $title := .Site.Title -}}
  {{- if and .IsHome (.Site.Params.subtitle) -}}
    {{- $title = printf "%s%s%s" $title $separator .Site.Params.subtitle -}}
  {{- end -}}
  {{- if and (not .IsHome) .Title -}}
    {{- $title = printf "%s%s%s" .Title $separator .Site.Title -}}
  {{- end -}}
  <title>{{ $title }}</title>
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <!-- include theme's theme-switching script, keywords meta, etc. -->
  <link rel="stylesheet" href="/css/style.css?v={{ now.Unix }}">
</head>
<body id="top">
  <div class="container">
    {{ partial "header.html" . }}
    <section class="search-page">
      <h1 class="article-title">{{ .Title }}</h1>
      <div class="search-box">
        <input id="search-input" type="text" placeholder="搜索..." />
        <div id="results"></div>
      </div>
    </section>
    <script src="/js/search.js"></script>
    {{ partial "footer.html" . }}
  </div>
  <script src="/js/main.js" defer></script>
</body>
</html>
```

## Client-Side Search Implementation

Hugo can output an `index.json` via the JSON output format. Use a small JS file for client-side fuzzy search:

```js
// static/js/search.js
document.addEventListener('DOMContentLoaded', function() {
  var input = document.getElementById('search-input');
  var results = document.getElementById('results');
  if (!input || !results) return;

  var indexUrl = '/index.json';
  var entries = [];

  fetch(indexUrl).then(function(r) { return r.json(); }).then(function(data) {
    (data.pages || data).forEach(function(p) {
      entries.push({
        title: p.title,
        summary: p.summary || '',
        url: p.permalink || p.url
      });
    });
  }).catch(function() {});

  function fuzzyMatch(text, query) {
    if (!query) return true;
    return (text || '').toLowerCase().indexOf(query.toLowerCase()) !== -1;
  }

  function displayResults(matches) {
    if (matches.length === 0) {
      results.innerHTML = '<p style="color:#888;text-align:center;margin-top:1em;">没有找到匹配的文章</p>';
      return;
    }
    var html = '<ul class="post-archive">';
    matches.forEach(function(m) {
      html += '<li class="post-item"><a class="post-title" href="' + m.url + '">' + m.title + '</a></li>';
    });
    html += '</ul>';
    results.innerHTML = html;
  }

  input.addEventListener('input', function() {
    var q = input.value.trim();
    if (q.length === 0) { results.innerHTML = ''; return; }
    var matches = entries.filter(function(e) {
      return fuzzyMatch(e.title, q) || fuzzyMatch(e.summary, q);
    }).slice(0, 30);
    displayResults(matches);
  });
});
```

## Required Hugo Config

Make sure the site outputs JSON (needed for search index):

```toml
[outputs]
  home = ["HTML", "RSS", "JSON"]
```

And `index.json` template should output pages with title, summary, and permalink.

## CSS

Add styles for `.search-page` to ensure visibility:

```css
.search-page { padding: 0 20px; margin-bottom: 2em; }
.search-page .search-box { margin: 1em 0; }
.search-page #search-input {
  width: 100%; max-width: 500px; padding: 0.6em 1em;
  font-size: 1em; border: 1px solid var(--c-border);
  border-radius: 4px; background: var(--c-bg); color: var(--c-text);
}
```
