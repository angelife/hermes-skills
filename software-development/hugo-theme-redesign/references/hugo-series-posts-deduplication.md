# Hugo `series/` vs `posts/` Duplicate Article Deduplication

## Symptom
`/archives/` lists the same article title+date multiple times. These entries often differ only by section path:
- `/posts/<slug>/...`
- `/series/<term>/<slug>.md`

## Pattern
During migrations (Blogger → Hugo) or taxonomy reorgs, the same article can be stored in two places:
1. A full page-bundle under `content/posts/<slug>/index.md`
2. A standalone markdown file under `content/series/<term>/<slug>.md`

Both files may share the same `date`, a similar `title`, and nearly identical body content. Because archive/list templates merge all regular pages, both URLs appear in archive views.

## Diagnosis
Do not rely on title count alone. Check source files and compare bodies:
```bash
find content/posts -name 'index.md' | wc -l
find content/series -name '*.md' | wc -l
```
Then compare suspected pairs by content similarity (SequenceMatcher, md5 of stripped body).

## Fix
Keep `content/posts/...` as canonical source. Remove duplicate `content/series/<term>/...md` files when the series copy is functionally identical.

If the series copy carries taxonomy metadata only, prefer Hugo frontmatter build controls instead of keeping a duplicate page:
```yaml
_build:
  render: never
  list: always
```

## Caution
Some `/series/<term>/...` URLs may have external refs or search engine indexing. Before removing any URL that currently returns 200, audit inbound links; if they exist, add a redirect rather than returning 404.

## Verification
After deduplication, inspect rendered archive HTML directly:
```bash
hugo --gc --minify
python3 - <<'PY'
from pathlib import Path
import re
from collections import Counter
p=Path('public/archives/index.html').read_text(encoding='utf-8')
items=re.findall(r'<a [^>]*post-title[^>]*>([^<]+)</a>\s*<time [^>]*post-date[^>]*>([^<]+)</time>', p)
c=Counter(items)
print('total', len(items), 'dup groups', sum(1 for v in c.values() if v>1))
PY
```
Build success alone is insufficient; the rendered archive must show zero duplicate title+date groups.
