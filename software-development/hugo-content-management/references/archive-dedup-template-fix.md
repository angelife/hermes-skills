# archives.html 模板级去重修复模板

## 问题

多 section 站点的归档页同时渲染 `posts/` 与 `series/<name>/` 时，同一主体文章可能两份都进入 `.RegularPages`。

如果模板按 `ContentBaseName` 去重，而重复文章的 posts/series 文件名不同（例如中文 slug vs 拼音 slug），去重会失效，用户看到 title+date 完全相同的重复条目。

## 修复模板

将归档页去重键从文件名改为 title+date：

```html
{{- $pool := where site.RegularPages "Section" "in" (slice "posts" "series") }}
{{- $pool = where $pool "Params.draft" "!=" true }}
{{- $pool = where $pool "Date.Year" "!=" 1 }}
{{- $sortedPool := sort $pool "Section" "asc" }}
{{- $seen := slice }}
{{- $deduped := slice }}
{{- range $sortedPool }}
  {{- $key := printf "%s|%s" .Title (.Date.Format "2006-01-02 15:04") }}
  {{- if not (in $seen $key) }}
    {{- $seen = $seen | append $key }}
    {{- $deduped = $deduped | append . }}
  {{- end }}
{{- end }}
{{- $deduped = sort $deduped "Date" "desc" }}
{{- range $deduped }}
  ...
{{- end }}
```

## 前置条件

- `posts/` 与 `series/` 下对应文章的 `title` 与 `date` frontmatter 保持一致
- 如 title/date 有漂移，需要先统一 frontmatter，再做模板级去重

## 配套校验

重建后用以下脚本验证 `public/archives/index.html`：

```python
import re
from collections import Counter
from pathlib import Path
html = Path('public/archives/index.html').read_text(encoding='utf-8')
items = re.findall(r'<a [^>]*post-title[^>]*>([^<]+)</a>\s*<time [^>]*post-date[^>]*>([^<]+)</time>', html)
c = Counter(items)
assert len([k for k,v in c.items() if v>1]) == 0
```

## 来源

本修复来自 2026-07-05 angelife.github.com 归档页重复问题，根因确认：
- 删除 series 副本后线上仍重复 → 模板去重键失效
- 将去重键从 ContentBaseName 改为 title|date 后本地构建 dup_groups=0
