# 归档页重复检测食谱

## 1. 基于 source markdown 的重复检测（推荐）

```python
#!/usr/bin/env python3
from pathlib import Path
from collections import Counter, defaultdict
from difflib import SequenceMatcher
import re

ROOT = Path('/Users/macos/angelife.github.com/hugo-site/content')

def body(path: Path) -> str:
    text = path.read_text(encoding='utf-8')
    text = re.sub(r'^---\n.*?\n---\n', '', text, flags=re.S)
    return re.sub(r'\s+', ' ', text).strip()

def meta(path: Path):
    text = path.read_text(encoding='utf-8')
    date = ''
    m = re.search(r'^date:\s*(.*)$', text, re.M)
    if m:
        date = m.group(1).strip().strip('"').strip("'")[:16]
    title = ''
    m = re.search(r'^title:\s*"(.*?)"', text, re.M)
    if m:
        title = m.group(1)
    return title, date

posts = {}
series = {}
for p in ROOT.rglob('*.md'):
    rel = p.relative_to(ROOT)
    if p.name == 'index.md':
        continue
    section = rel.parts[0]
    title, date = meta(p)
    entry = (section, str(rel), body(p))
    if section == 'posts':
        posts.setdefault((title, date), []).append(entry)
    elif 'information-judgment' in str(rel):
        series.setdefault((title, date), []).append(entry)

# Cross duplicates
for key in sorted(set(posts) | set(series)):
    pv = posts.get(key, [])
    sv = series.get(key, [])
    if len(pv) + len(sv) > 1:
        print(f'TITLE_DATE_DUP {key}:')
        for sec, rel, _ in pv + sv:
            print(f'  {sec}: {rel}')
    elif len(pv) > 1:
        print(f'POSTS_DUP {key}: {[r for _,r,_ in pv]}')
    elif len(sv) > 1:
        print(f'SERIES_DUP {key}: {[r for _,r,_ in sv]}')
```

## 2. 基于 minified HTML 的提取

如果扫描 source 不方便，用以下选择器解析线上/本地归档页：

```python
import requests, re
from collections import Counter

html = requests.get('https://angelife.github.io/archives/',
                    headers={'User-Agent':'Mozilla/5.0'}, timeout=30).text
# 匹配 minified HTML 也不容易漏
items = re.findall(
    r'<a [^>]*post-title[^>]*>([^<]+)</a>\s*<time [^>]*post-date[^>]*>([^<]+)</time>',
    html
)
c = Counter(items)
print('total', len(items), 'dup groups', sum(1 for v in c.values() if v > 1))
```

注意：
- `re.findall` 的 pattern 必须同时匹配 `<a class="post-title"` 和 `<time class="post-date">`
- minify 页面没有换行，`\s*` 而不是 `\n`

## 3. 在线校验 CDN/Pages 缓存

```python
import requests
# 已删除的 series 详情页应返回 404
url = 'https://angelife.github.io/series/information-judgment/2012-02-08-shixi-keerkaiguodeer-de-gudu-geti-gainian/'
r = requests.get(url, allow_redirects=False, timeout=25)
print(r.status_code, r.headers.get('location', ''))
# 预期 404；若 200 说明缓存未更新
```
