#!/usr/bin/env python3
"""
Crawl a WeChat public account article and extract structured data + clean markdown.

Usage:
    python crawl_wechat.py <url> [--download-images] [--save-html] [--save-markdown] [--output-dir DIR]

Outputs JSON to stdout with: title, author, publish_time, account_desc, markdown, html, url
"""
import argparse
import asyncio
import hashlib
import json
import os
import re
import sys
import aiohttp

from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, BrowserConfig
from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator
from crawl4ai.extraction_strategy import JsonCssExtractionStrategy

WECHAT_SCHEMA = {
    "name": "wechat_article",
    "baseSelector": "#js_article",
    "fields": [
        {"name": "title",        "selector": "#activity-name, h1.rich_media_title", "type": "text"},
        {"name": "author",       "selector": "#js_name",                             "type": "text"},
        {"name": "publish_time", "selector": "#publish_time",                        "type": "text"},
        {"name": "content_html", "selector": "#js_content",                          "type": "html"},
        {"name": "account_desc", "selector": "#js_profile_desc",                     "type": "text"},
    ],
}

WECHAT_USER_AGENT = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) "
    "Mobile/15E148 MicroMessenger/8.0.43"
)

def _extract_image_urls(text: str) -> list[str]:
    """Extract all WeChat CDN image URLs from HTML or markdown text."""
    pattern = r'https?://mmbiz\.(?:qpic|qlogo)\.cn/[^\s"\'<>\)]+'
    urls = list(dict.fromkeys(re.findall(pattern, text)))  # deduplicate, preserve order
    return urls


def _clean_markdown(md: str) -> str:
    """Clean raw markdown: remove data-URI placeholder images and excessive blank lines.

    WeChat articles contain 1x1 SVG placeholder images as data URIs. These appear
    in two forms in the raw markdown:
    1. Complete:  ![alt](data:image/svg+xml,...)
    2. Broken across lines — the regex doesn't capture the closing ), leaving
       orphan lines like:  '%20fill='%23FFFFFF'...%3C/svg%3E)
    """
    # Remove complete markdown images with data: URIs
    md = re.sub(r'!\[[^\]]*\]\(data:[^\)]+\)', '', md)
    # Remove orphan URL-encoded SVG tail lines (from broken data-URI images)
    md = re.sub(r"^['\"]?%[0-9A-Fa-f]{2}.*%3C/svg%3E\)?['\"]?\s*$", '', md, flags=re.MULTILINE)
    # Remove lines that are just leftover encoded SVG fragments
    md = re.sub(r"^.*%3Csvg%20.*%3C/svg%3E.*$", '', md, flags=re.MULTILINE)
    # Remove javascript:void links
    md = re.sub(r'\[([^\]]*)\]\(javascript:void\\\(0\\\);\)', r'\1', md)
    # Collapse 3+ consecutive blank lines into 2
    md = re.sub(r'\n{3,}', '\n\n', md)
    return md.strip()


async def download_images(urls: list[str], images_dir: str) -> dict[str, str]:
    """Download images from WeChat CDN with proper Referer header.

    Returns a mapping of original_url -> local_path.
    """
    os.makedirs(images_dir, exist_ok=True)
    url_to_local: dict[str, str] = {}

    headers = {
        "User-Agent": WECHAT_USER_AGENT,
        "Referer": "https://mp.weixin.qq.com/",
    }

    # Limit concurrency to avoid hammering the CDN and getting rate-limited
    semaphore = asyncio.Semaphore(8)

    async def _limited(url):
        async with semaphore:
            return await _download_one(session, url, images_dir)

    async with aiohttp.ClientSession(headers=headers) as session:
        tasks = [_limited(url) for url in urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)

    for url, result in zip(urls, results):
        if isinstance(result, str):
            url_to_local[url] = result
        else:
            print(f"Warning: failed to download {url}: {result}", file=sys.stderr)

    return url_to_local


async def _download_one(session: aiohttp.ClientSession, url: str, images_dir: str) -> str:
    """Download a single image and return the local file path."""
    async with session.get(url) as resp:
        resp.raise_for_status()
        content = await resp.read()

        # Determine file extension from Content-Type
        content_type = resp.headers.get("Content-Type", "")
        ext_map = {
            "image/jpeg": ".jpg",
            "image/png": ".png",
            "image/gif": ".gif",
            "image/webp": ".webp",
            "image/svg+xml": ".svg",
        }
        ext = ext_map.get(content_type.split(";")[0].strip(), ".jpg")

        # Use hash of URL as filename to avoid duplicates
        name = hashlib.md5(url.encode()).hexdigest()[:12] + ext
        local_path = os.path.join(images_dir, name)

        with open(local_path, "wb") as f:
            f.write(content)

        return local_path


def replace_urls(text: str, url_map: dict[str, str]) -> str:
    """Replace all remote URLs in text with local paths."""
    for remote_url, local_path in url_map.items():
        text = text.replace(remote_url, local_path)
    return text


async def crawl_wechat_article(url: str, images_dir: str | None = None) -> dict:
    """Crawl a WeChat article.

    Args:
        url: WeChat article URL.
        images_dir: If provided, download all images to this directory and
                    replace remote URLs with local paths in HTML and markdown.
                    If None, images are left as remote URLs.
    """
    browser_config = BrowserConfig(
        user_agent=WECHAT_USER_AGENT,
        headers={
            "Referer": "https://mp.weixin.qq.com/",
            "Accept-Language": "zh-CN,zh;q=0.9",
        },
    )

    # WeChat uses data-src for lazy-loaded images. This JS copies data-src -> src
    # so that the markdown generator can pick up the real image URLs.
    js_fix_lazy_images = """
    document.querySelectorAll('img[data-src]').forEach(img => {
        if (!img.src || img.src.startsWith('data:')) {
            img.src = img.getAttribute('data-src');
        }
    });
    """

    config = CrawlerRunConfig(
        wait_for="css:#js_content",
        js_code=js_fix_lazy_images,
        extraction_strategy=JsonCssExtractionStrategy(WECHAT_SCHEMA),
        # Use raw markdown (no PruningContentFilter) to preserve inline images.
        # We clean up placeholder data-URIs ourselves in _clean_markdown().
        markdown_generator=DefaultMarkdownGenerator(
            options={"ignore_links": False},
        ),
        word_count_threshold=10,
        remove_overlay_elements=True,
    )

    async with AsyncWebCrawler(config=browser_config) as crawler:
        result = await crawler.arun(url, config=config)

    meta = json.loads(result.extracted_content or "[]")
    article = meta[0] if meta else {}

    raw_html = article.get("content_html", "")
    raw_md = _clean_markdown(result.markdown.raw_markdown) if result.markdown else ""

    # Download images and replace URLs if images_dir is specified
    if images_dir:
        all_urls = _extract_image_urls(raw_html) + _extract_image_urls(raw_md)
        all_urls = list(dict.fromkeys(all_urls))  # deduplicate
        if all_urls:
            print(f"Downloading {len(all_urls)} images...", file=sys.stderr)
            url_map = await download_images(all_urls, images_dir)
            raw_html = replace_urls(raw_html, url_map)
            raw_md = replace_urls(raw_md, url_map)
            print(f"Downloaded {len(url_map)}/{len(all_urls)} images to {images_dir}", file=sys.stderr)

    return {
        "title":        article.get("title", "").strip(),
        "author":       article.get("author", "").strip(),
        "publish_time": article.get("publish_time", "").strip(),
        "account_desc": article.get("account_desc", "").strip(),
        "markdown":     raw_md,
        "html":         raw_html,
        "url":          result.url,
    }


def main():
    parser = argparse.ArgumentParser(description="Crawl a WeChat article")
    parser.add_argument("url", help="WeChat article URL (mp.weixin.qq.com/s/...)")
    parser.add_argument("--save-html", action="store_true", help="Save HTML to file")
    parser.add_argument("--save-markdown", action="store_true", help="Save markdown to file")
    parser.add_argument("--download-images", action="store_true",
                        help="Download images locally to bypass hotlink protection")
    parser.add_argument("--output-dir", default=".", help="Directory for saved files")
    args = parser.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)
    images_dir = os.path.join(args.output_dir, "images") if args.download_images else None
    article = asyncio.run(crawl_wechat_article(args.url, images_dir=images_dir))

    # Always print JSON summary to stdout
    summary = {k: v for k, v in article.items() if k not in ("html", "markdown")}
    summary["markdown_length"] = len(article["markdown"])
    summary["html_length"] = len(article["html"])
    print(json.dumps(summary, ensure_ascii=False, indent=2))

    if args.save_html and article["html"]:
        slug = re.sub(r'[^\w]+', '_', article["title"] or "wechat_article")[:60]
        path = os.path.join(args.output_dir, f"{slug}.html")
        with open(path, "w", encoding="utf-8") as f:
            f.write(article["html"])
        print(f"\nHTML saved to: {path}", file=sys.stderr)

    if args.save_markdown and article["markdown"]:
        slug = re.sub(r'[^\w]+', '_', article["title"] or "wechat_article")[:60]
        path = os.path.join(args.output_dir, f"{slug}.md")
        with open(path, "w", encoding="utf-8") as f:
            f.write(article["markdown"])
        print(f"\nMarkdown saved to: {path}", file=sys.stderr)

    # Print readable preview
    print(f"\n{'='*60}")
    print(f"Title:   {article['title']}")
    print(f"Author:  {article['author']}")
    print(f"Time:    {article['publish_time']}")
    print(f"Account: {article['account_desc']}")
    print(f"{'='*60}")
    print(f"Content preview (first 500 chars):\n")
    print(article["markdown"][:500])


if __name__ == "__main__":
    main()
