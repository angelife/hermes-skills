#!/usr/bin/env python3
"""
Extend Hugo's index.json with entries from static archive pages (old-site/).
Run AFTER `hugo --gc --minify --cleanDestinationDir`.
"""
import os, glob, json, re

PUBLIC = os.path.expanduser("~/angelife.github.com/hugo-site/public")
ARCHIVE = os.path.join(PUBLIC, "old-site")          # adjust for your archive dir
INDEX_PATH = os.path.join(PUBLIC, "index.json")

# Read existing Hugo index
with open(INDEX_PATH, "r", encoding="utf-8") as f:
    index = json.load(f)

existing_urls = {e.get("permalink", "") for e in index}
added = 0

for html_path in sorted(glob.glob(os.path.join(ARCHIVE, "**", "*.html"), recursive=True)):
    with open(html_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Extract title from <title> tag
    m = re.search(r'<title>(.*?)</title>', content, re.DOTALL)
    title = m.group(1).strip() if m else os.path.basename(html_path)

    # Permalink: relative to Hugo public/
    rel_path = os.path.relpath(html_path, PUBLIC)
    permalink = f"https://angelife.github.io/{rel_path}"  # adjust domain

    if permalink in existing_urls:
        continue

    # Plain-text summary from <body>
    summary = ""
    body_m = re.search(r'<body[^>]*>(.*?)</body>', content, re.DOTALL)
    if body_m:
        text = re.sub(r'<[^>]+>', '', body_m.group(1))
        text = re.sub(r'\s+', ' ', text).strip()
        summary = text[:200] if text else ""

    index.append({
        "categories": "旧站存档",
        "content": "",
        "description": summary[:160] or "存档文章",
        "permalink": permalink,
        "summary": summary,
        "tags": "旧站,存档",
        "title": title
    })
    existing_urls.add(permalink)
    added += 1

with open(INDEX_PATH, "w", encoding="utf-8") as f:
    json.dump(index, f, ensure_ascii=False)

print(f"Extended search index: {added} archive entries added (total {len(index)})")
