# Batch Title Extraction from WeChat Articles via Playwright

## Use Case

You have 50+ WeChat article URLs (`mp.weixin.qq.com/s/...`) and need to extract their titles and account names. Curl is blocked by WeChat's anti-crawler. The browser tool is too slow for 50+ pages.

## Solution: Playwright Chromium

### Prerequisites

```bash
# Playwright installed
python3 -c "from playwright.sync_api import sync_playwright; print('OK')"

# Chromium browser available
ls ~/Library/Caches/ms-playwright/chromium-*
```

### Script

```python
#!/usr/bin/env python3
"""Batch-extract WeChat article titles using Playwright Chromium"""

import json
from pathlib import Path
from playwright.sync_api import sync_playwright

URLS = ["https://mp.weixin.qq.com/s/...", "..."]  # your URLs

results = []
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    context = browser.new_context(
        user_agent=(
            "Mozilla/5.0 (Linux; Android 14; MI 8) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/125.0.6422.165 Mobile Safari/537.36 "
            "MicroMessenger/8.0.52"
        ),
        locale="zh-CN",
    )

    for i, url in enumerate(URLS):
        try:
            page = context.new_page()
            page.goto(url, wait_until="domcontentloaded", timeout=20000)

            title = page.eval_on_selector(
                "h1", "el => el?.textContent?.trim() || ''"
            ) or ""

            account = ""
            for sel in [".rich_media_meta_nickname", "#js_name"]:
                el = page.query_selector(sel)
                if el:
                    account = el.text_content().strip()
                    break

            results.append({"url": url, "title": title, "account": account})
            page.close()
        except Exception as e:
            results.append({"url": url, "error": str(e)})

    browser.close()

Path("/tmp/wechat_titles.json").write_text(
    json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8"
)
```

### Key Techniques

1. **Mobile WeChat User-Agent** — Essential to avoid CAPTCHA. Desktop UA triggers anti-crawler.
2. **`domcontentloaded`** — Don't wait for full load (can hang on WeChat analytics). DOM is enough for title.
3. **Account name** — In `#js_name` or `.rich_media_meta_nickname`. Not all pages have it.
4. **Deleted articles** — Return "此内容因违规无法查看" (`<h2>`, no `<h1>`). Handle with fallback.

### Rate Limiting

~5-10s per page. For 50+ pages, expect 5-10 minutes total. This is WeChat-imposed.
