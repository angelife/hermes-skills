---
name: crawl-wechat
description: >
  Crawl and extract WeChat public account (微信公众号) articles into structured data and clean markdown,
  using crawl4ai (Playwright Chromium) with WeChat in-app UA spoofing, dynamic wait, lazy-image fix,
  and local image download to bypass hotlink protection. Use when user provides mp.weixin.qq.com link
  and wants content extracted. NOTE: on cloud agents without login session, WeChat returns a risk-check
  wall (no js_content in HTML) — see "Cloud agent reality" below.
version: 1.0.0
author: 木同学 (QwenPaw cloud agent), adapted from gxcsoccer/wechat-article-crawler
tags: [wechat, weixin, 微信公众号, 文章提取, crawl4ai, 云端]
---

# Crawl WeChat Articles

This skill extracts content from WeChat public account articles using the `crawl4ai` library. WeChat articles require special handling because they check the User-Agent header, render content dynamically, and use lazy-loading for images.

## Cloud agent reality (木同学 2026-07-18 实测)

This skill works great on a **trusted browser environment** (local machine with WeChat login session,
or persistent browser profile). But on a **cloud agent without login session** (e.g. QwenPaw sandbox,
cloud IP), WeChat returns a risk-check wall:

- `curl` / Playwright / crawl4ai all get an "环境异常 / 去验证" page (~18KB), **no `js_content` in HTML**
- Server sends a different HTML set; the article body is never delivered
- This is a server-side risk-score block, not a JS-render issue — nothing client-side can fix it

**If you run this on a cloud agent and get empty `markdown_length: 0` + timeout on `#js_content`:**
you hit the wall. Fall back to:
1. A trusted local browser via CDP (control the user's logged-in Chrome), or
2. Ask the user to paste the article body / have a local agent (Hermes) fetch it.

See also `media/wechat-article` v1.4.0 for the full three-tier classification and why.

## When to use

- User provides a `mp.weixin.qq.com/s/...` URL and wants its content
- User asks to scrape/crawl/extract/read a WeChat (微信) article
- User wants to batch-process multiple WeChat article links
- User needs the article in markdown or structured format

## Setup (run once before first use)

Before running the script, ensure dependencies are installed:

```bash
pip install crawl4ai aiohttp && crawl4ai-setup
```

If `crawl4ai` is already importable and the browser backend is ready, skip this step. When the script fails with `ModuleNotFoundError` or browser-related errors, run the commands above to fix it.

## How it works

Run the bundled script to crawl a WeChat article:

```bash
python <skill-dir>/scripts/crawl_wechat.py <URL> [--download-images] [--save-html] [--save-markdown] [--output-dir DIR]
```

The script outputs a JSON summary to stdout and optionally saves the full HTML and/or markdown to files.

### Key technical details

1. **User-Agent spoofing**: The script sets `MicroMessenger/8.0.43` in the UA string so WeChat serves the full article instead of a "please open in WeChat" block.

2. **Dynamic wait**: Uses `wait_for="css:#js_content"` to ensure the article body has fully rendered before scraping.

3. **Lazy-image fix**: WeChat uses `data-src` for lazy-loaded images. The script injects JS to copy `data-src` → `src` so the markdown generator can pick up real image URLs.

4. **Structured extraction**: Uses `JsonCssExtractionStrategy` with a schema targeting WeChat's DOM structure (`#activity-name` for title, `#js_name` for author, `#publish_time` for date, `#js_content` for body).

5. **Clean markdown with images**: Uses `DefaultMarkdownGenerator` to produce readable markdown. SVG placeholder images and data-URI artifacts are cleaned out, preserving only real article images inline with the text.

6. **Image hotlink protection**: WeChat images on `mmbiz.qpic.cn` block requests with non-QQ referrers. Use `--download-images` to download all images locally with the correct Referer header, automatically replacing remote URLs with local paths in both HTML and markdown output.

## Extracted fields

| Field          | Description                        |
|----------------|------------------------------------|
| `title`        | Article title                      |
| `author`       | Public account name                |
| `publish_time` | Publication timestamp              |
| `account_desc` | Account description/bio            |
| `markdown`     | Clean markdown of article body     |
| `html`         | Raw HTML of article body           |
| `url`          | Final URL after any redirects      |

## Example usage

Single article with images downloaded locally:
```bash
python <skill-dir>/scripts/crawl_wechat.py "https://mp.weixin.qq.com/s/xxx" --download-images --save-markdown --output-dir ./output
```

For programmatic use in Python:
```python
from crawl_wechat import crawl_wechat_article
import asyncio

article = asyncio.run(crawl_wechat_article(
    "https://mp.weixin.qq.com/s/...",
    images_dir="./output/images",  # download images locally
))
print(article["title"])
print(article["markdown"])  # images reference local paths
```

## Limitations

- Requires a valid, non-expired WeChat article URL — cannot search or list articles from an account
- High-frequency crawling may trigger WeChat's anti-bot measures (CAPTCHAs, IP blocks)
- Some temporary share links expire after a period
