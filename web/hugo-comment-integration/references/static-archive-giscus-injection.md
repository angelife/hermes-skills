# Giscus injection into static HTML archives

## Problem
A Hugo site has a `static/old-site/` directory with 100+ hand-crafted or Vimwiki-generated static HTML pages. These files have no template engine — they're literal `.html` that Hugo copies verbatim to `public/`.

To add Giscus comments to every page, you cannot use Hugo partials. You must inject the Giscus HTML/JS into each file via a script.

## Injection pattern

The pages share a consistent ending:
```html
<script src="jquery-1.4.2.min.js" type="text/javascript"></script>
<script src="vimwiki.js" type="text/javascript"></script>


</body>
</html>
```

Insert Giscus block before `</body>`:

```python
GISCUS_HTML = '''  <style>
    #giscus { margin: 2em auto; max-width: 760px; padding: 0 1em; font-family: -apple-system,...; }
    #giscus iframe { background: #fff; border-radius: 4px; }
  </style>
  <hr>
  <div id="giscus"></div>
  <script src="https://giscus.app/client.js"
    data-repo="angelife/angelife.github.com"
    data-repo-id="<repo_id>"
    data-category="General"
    data-category-id="<category_id>"
    data-mapping="pathname"
    data-strict="0"
    data-theme="light"   # ← never preferred_color_scheme for light-only archives
    data-lang="zh-CN"
    crossorigin="anonymous"
    async>
  </script>'''

new_content = content.replace('</body>', GISCUS_HTML + '\n</body>', 1)
```

## Theme matching pitfall
- The archive has NO dark mode (fixed white background)
- `data-theme="preferred_color_scheme"` renders dark comments on light page when OS is dark → mismatch
- Fix: always force `data-theme="light"` for light-only static archives
- Add `#giscus iframe { background: #fff }` to prevent iframe transparency

## Return-link banner
Inject a banner after `<body>` tag via `re.sub(r'(<body[^>]*>)', r'\1\n' + BANNER_HTML, content, count=1)`.

The banner should link back to the main site and include a search link pointing to `/search/?q=`.
