# WeChat Article Extraction

WeChat Official Account articles (`mp.weixin.qq.com/s/...`) are behind anti-scraping protection.

## Extraction Method

### Step 1: Try web_extract

```python
web_extract(urls=["https://mp.weixin.qq.com/s/..."])
```

Fails if WeChat returns a captcha page (滑块验证).

### Step 2: Fallback to curl with browser User-Agent

```bash
curl -s -L -A "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36" \
  "https://mp.weixin.qq.com/s/<ARTICLE_ID>" -o /tmp/wechat_article.html
```

### Step 3: Extract `js_content` div

```python
import re, html

with open('/tmp/wechat_article.html', 'r', encoding='utf-8', errors='ignore') as f:
    content = f.read()

match = re.search(r'id="js_content"[^>]*>(.*?)</div>\s*<script', content, re.DOTALL)
if match:
    raw = match.group(1)
    text = html.unescape(raw)
    text = re.sub(r'<[^>]+>', '', text)  # strip HTML tags
    text = re.sub(r'\s+', ' ', text).strip()
    print(text)
```

## Notes

- WeChat may rate-limit: "Refreshing too often" message with repeated requests
- The `js_content` div is server-rendered for initial page load — accessible via raw HTML
- Some articles block regardless of User-Agent
- If captcha appears, interactive browser (computer_use / browser tool) is needed
