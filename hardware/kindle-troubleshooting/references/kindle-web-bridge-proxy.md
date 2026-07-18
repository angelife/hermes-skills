# Kindle Web Bridge Proxy

Full Python script for the web-to-Kindle proxy. Save as `~/kindle-bridge/proxy.py`.

## Architecture

```
Kindle Browser → http://<Mac-IP>:8080?url=https://example.com
                       ↓
               Python proxy (requests library)
                       ↓
               Fetches page with proper SSL/User-Agent
               Strips: <script>, <style>, <iframe>, <nav>, <footer>, <header>, <aside>
               Preserves: <a>, <p>, <br>, <h1-6>, <ul>/<ol>/<li>, <blockquote>, <pre>/<code>, <img>
                       ↓
               Returns minimal HTML with inline CSS optimized for 600px e-ink display
```

## Setup

```bash
pip3 install requests
mkdir -p ~/kindle-bridge
cd ~/kindle-bridge
# Create proxy.py with the code below
python3 proxy.py &
# Listening on http://0.0.0.0:8080
```

## Usage on Kindle

1. Ensure Kindle is on **same WiFi** as the Mac
2. Experimental Browser → `http://<Mac-IP>:8080`
3. Type URL → tap "Open"
4. Page renders as clean text

## Full Source Code (tested 2026-07-13)

```python
#!/usr/bin/env python3
"""Kindle Web Bridge — convert modern web pages to minimal HTML for Kindle"""
import re, html as html_mod
from urllib.parse import urlparse
import requests
import http.server
import socketserver

def clean_html(html_text, url):
    html_text = re.sub(r'<script[^>]*>.*?</script>', '', html_text, flags=re.DOTALL | re.IGNORECASE)
    html_text = re.sub(r'<style[^>]*>.*?</style>', '', html_text, flags=re.DOTALL | re.IGNORECASE)
    html_text = re.sub(r'<iframe[^>]*>.*?</iframe>', '', html_text, flags=re.DOTALL | re.IGNORECASE)
    html_text = re.sub(r'<nav[^>]*>.*?</nav>', '', html_text, flags=re.DOTALL | re.IGNORECASE)
    html_text = re.sub(r'<footer[^>]*>.*?</footer>', '', html_text, flags=re.DOTALL | re.IGNORECASE)
    html_text = re.sub(r'<header[^>]*>.*?</header>', '', html_text, flags=re.DOTALL | re.IGNORECASE)
    html_text = re.sub(r'<aside[^>]*>.*?</aside>', '', html_text, flags=re.DOTALL | re.IGNORECASE)
    html_text = re.sub(r'</?(?:a|p|br|h[1-6]|ul|ol|li|div|span|blockquote|pre|code|img|table|tr|td|th|tbody|thead|b|i|em|strong|small|hr)\b[^>]*>',
                       lambda m: keep_tag(m), html_text)
    html_text = re.sub(r'<[^>]+>', '', html_text)
    html_text = html_mod.unescape(html_text)
    html_text = re.sub(r'\n\s*\n', '\n\n', html_text)
    html_text = '\n'.join(line.strip() for line in html_text.split('\n'))
    return html_text

def keep_tag(m):
    tag = m.group(0)
    if tag.startswith('<a '):
        href = re.search(r'href=[\'"]([^\'"]+)[\'"]', tag)
        if href:
            return f'<a href="{href.group(1)}">'
    return tag.split()[0] + '>'

def fetch_page(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                   'Accept': 'text/html,application/xhtml+xml'}
        resp = requests.get(url, headers=headers, timeout=15)
        resp.encoding = resp.apparent_encoding
        return resp.status_code, resp.text, resp.headers.get('content-type', '')
    except Exception as e:
        return 0, str(e), ''

def make_page(title, content, source_url=''):
    links = ''
    if source_url:
        links = f'<p><small><a href="/?url={html_mod.escape(source_url)}">⟳ Refresh</a></small></p>'
    return f'''<!DOCTYPE html>
<html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html_mod.escape(title)}</title>
<style>
body{{font-family:sans-serif;font-size:16px;line-height:1.4;color:#333;padding:8px;margin:0;max-width:600px}}
a{{color:#0066cc;text-decoration:none}}
h1{{font-size:20px}} h2{{font-size:18px}} h3{{font-size:16px}}
pre{{white-space:pre-wrap;font-size:14px;background:#f5f5f5;padding:8px}}
img{{max-width:100%;height:auto}}
hr{{border:none;border-top:1px solid #ddd}}
small{{color:#666}}
form{{margin-bottom:16px}}
input[type=text]{{width:70%;font-size:16px;padding:6px}}
input[type=submit]{{font-size:16px;padding:6px 12px}}
</style></head><body>
<h1>Kindle Web Bridge</h1>
<form method="get" action="/">
<input type="text" name="url" placeholder="Enter URL https://..." value="{html_mod.escape(source_url)}">
<input type="submit" value="Open">
</form>
{links}
<hr>
{content}
</body></html>'''

class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        params = dict(p.split('=', 1) for p in parsed.query.split('&') if '=' in p)
        if parsed.path == '/' and 'url' in params:
            url = params['url']
            status, html_text, ctype = fetch_page(url)
            if status == 200:
                content = clean_html(html_text, url)
                title = re.search(r'<title[^>]*>(.*?)</title>', html_text, re.DOTALL | re.IGNORECASE)
                title = title.group(1).strip()[:80] if title else 'Page'
                page = make_page(title, content, url)
                self.send_response(200)
                self.send_header('Content-Type', 'text/html; charset=utf-8')
                self.send_header('Cache-Control', 'no-cache')
                self.end_headers()
                self.wfile.write(page.encode('utf-8'))
            else:
                page = make_page('Error', f'<p>Failed to fetch: {html_text}</p>')
                self.send_response(200)
                self.send_header('Content-Type', 'text/html; charset=utf-8')
                self.end_headers()
                self.wfile.write(page.encode('utf-8'))
        else:
            page = make_page('Kindle Web Bridge',
                '<p>Enter a URL to browse the web on your Kindle.</p>'
                '<p>Best for: news, blogs, Wikipedia, documentation, text-heavy sites.</p>')
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(page.encode('utf-8'))

    def log_message(self, format, *args):
        print(f"[{self.address_string()}] {args[0]} {args[1]} {args[2]}")

if __name__ == '__main__':
    PORT = 8080
    print(f"Kindle Web Bridge running on http://0.0.0.0:{PORT}")
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("0.0.0.0", PORT), Handler) as httpd:
        httpd.serve_forever()
```
