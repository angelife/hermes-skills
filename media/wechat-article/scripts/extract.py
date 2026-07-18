#!/usr/bin/env python3
"""
wechat-article: Extract WeChat public account article content.
Usage: python3 extract.py <url> [--json]

Outputs cleaned article text to stdout.
With --json: outputs {title, author, pub_date, content, url}
"""
import re, html, json, sys, os
from urllib.request import Request, urlopen
from urllib.parse import urlparse

def extract(url):
    req = Request(url, headers={
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    })
    with urlopen(req, timeout=30) as resp:
        raw = resp.read().decode('utf-8', errors='ignore')

    result = {'url': url, 'title': '', 'author': '', 'pub_date': '', 'content': ''}

    # Title
    m = re.search(r'var msg_title\s*=\s*["\']([^"\']+)["\']', raw)
    if m: result['title'] = m.group(1)
    m = re.search(r'<title>(.*?)</title>', raw)
    if not result['title'] and m: result['title'] = m.group(1)

    # Author / Account — multiple fallback patterns
    author_patterns = [
        r'var nickname\s*=\s*["\']([^"\']+)["\']',
        r'var user_name\s*=\s*["\']([^"\']+)["\']',
        r'var profile_nickname\s*=\s*["\']([^"\']+)["\']',
        r'<strong\s+class="rich_media_meta_nickname"[^>]*>([^<]+)',
        r'"nickname"\s*:\s*"([^"]+)"',
    ]
    for pat in author_patterns:
        m = re.search(pat, raw)
        if m:
            result['author'] = m.group(1)
            break
    m = re.search(r'var msg_source_url\s*=\s*["\']([^"\']+)["\']', raw)
    if m: result['source_url'] = m.group(1)

    # Publish date — multiple fallback patterns
    import datetime
    date_patterns = [
        (r'var create_time\s*=\s*(\d{10})', lambda m: datetime.datetime.fromtimestamp(int(m.group(1))).strftime('%Y-%m-%d %H:%M')),
        (r'var ct\s*=\s*["\'](\d{4}-\d{2}-\d{2})', lambda m: m.group(1)),
        (r'"create_time"\s*:\s*(\d{10})', lambda m: datetime.datetime.fromtimestamp(int(m.group(1))).strftime('%Y-%m-%d %H:%M')),
        (r'<em\s+id="publish_time"[^>]*>([^<]+)', lambda m: m.group(1)),
        (r'var create_time\s*=\s*"([^"]+)"', lambda m: m.group(1)),
    ]
    for pat, fmt in date_patterns:
        m = re.search(pat, raw)
        if m:
            result['pub_date'] = fmt(m)
            break

    # Content from js_content
    m = re.search(r'id="js_content"[^>]*>(.*?)</div>\s*<script', raw, re.DOTALL)
    if m:
        text = html.unescape(m.group(1))
        text = re.sub(r'<[^>]+>', '', text)
        text = re.sub(r'\s+', ' ', text).strip()
        result['content'] = text
    else:
        # Check if captcha — NOTE: only check wx_verify, NOT 'ticket'!
        # The string 'ticket' appears frequently in legitimate page JS, causing false positives.
        if 'wx_verify' in raw:
            # Double-check: if page is >1MB, there's probably hidden js_content anyway
            if len(raw) > 1_000_000:
                result['error'] = '疑似验证码页面但页面体积较大，尝试直接查找 js_content 可能成功'
            else:
                result['error'] = '微信验证码拦截，需人工扫码或使用浏览器工具'
        else:
            result['error'] = '无法定位文章内容（js_content 未找到，且无验证码标记）'
    return result


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: python3 extract.py <url> [--json]', file=sys.stderr)
        sys.exit(1)
    url = sys.argv[1]
    if not url.startswith('http'):
        url = 'https://mp.weixin.qq.com/s/' + url
    result = extract(url)
    if '--json' in sys.argv:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        if result.get('error'):
            print(f"❌ {result['error']}")
        else:
            print(f"📰 {result['title']}")
            if result.get('author'): print(f"✍️ {result['author']}")
            if result.get('pub_date'): print(f"📅 {result['pub_date']}")
            print()
            print(result['content'])
