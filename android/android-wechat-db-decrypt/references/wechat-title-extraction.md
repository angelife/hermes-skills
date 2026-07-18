# WeChat Article Title Batch Extraction

从 EnMicroMsg.db 解密后，提取公众号文章（type=49）链接，批量获取标题和公众号名。

## 场景

解密微信数据库后，从 message 表取出 type=49 的链接，需要给每条链接配上标题和公众号名以便阅读。微信反爬机制会拦截 curl 请求（"环境异常"），需要用真实浏览器渲染。

## 前置条件

- Playwright 已安装（含 Chromium）— 在 openbb-env 中：`/Users/macos/openbb-env/bin/python`
- 加密 DB 已解密，或能通过 sqlcipher 直查
- **网速要求**：52 条链接约需 3-5 分钟（每条 3-6 秒）

## 工作流

### 1. 提取 URL 列表

```bash
# 从加密库直查（sqlcipher）
/tmp/sqlcipher/sqlite3 /tmp/EnMicroMsg.db <<'EOF' | grep -o 'https://mp\.weixin\.qq\.com/s/[A-Za-z0-9_-]*' | sort -u > /tmp/urls.txt
PRAGMA key = '0273023';
PRAGMA cipher_compatibility = 1;
SELECT content FROM message WHERE isSend=1 AND talker='<目标群聊ID>' AND type=49 AND content LIKE '%mp.weixin.qq.com/s/%';
EOF

# 检查数量
wc -l /tmp/urls.txt
```

注意：公众号文章链接有两种格式：
- 短链：`mp.weixin.qq.com/s/<短ID>` — 可直接用 Playwright 加载
- 长链（含 `__biz=`, `mid=`, `idx=`, `sn=` 参数）— 部分也兼容

### 2. 用 Playwright 批量拉标题

```python
from playwright.sync_api import sync_playwright

urls = open('/tmp/urls.txt').read().strip().split('\n')

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    # 模拟安卓微信浏览器 UA — 这是绕过微信反爬的关键
    context = browser.new_context(
        user_agent="Mozilla/5.0 (Linux; Android 14; MI 8) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.6422.165 Mobile Safari/537.36 MicroMessenger/8.0.52",
        locale="zh-CN",
    )
    
    for i, url in enumerate(urls):
        page = context.new_page()
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=20000)
            # 取标题（优先 h1）
            title = page.eval_on_selector("h1", "el => el?.textContent?.trim() || ''") or ""
            # 取公众号名
            account = ""
            for sel in [".rich_media_meta_nickname", "#js_name"]:
                el = page.query_selector(sel)
                if el:
                    account = el.text_content().strip()
                    break
            if not account:
                # 从链接里找
                for link in page.query_selector_all("a"):
                    text = link.text_content().strip()
                    href = link.get_attribute("href") or ""
                    if text and len(text) < 30 and "mp.weixin.qq.com" in href:
                        account = text
                        break
        except Exception as e:
            title = "(标题获取失败)"
            account = ""
        finally:
            page.close()
        
        results.append({"url": url, "title": title, "account": account})
    
    browser.close()
```

### 3. 关键参数

- **User-Agent**: 模拟安卓微信浏览器，绕过部分反爬。核心是 `MicroMessenger/8.0.52`。
- **`wait_until`**: `domcontentloaded` 即可，不需等全部图片加载。用 `load` 会等所有图片，慢 5-10 倍。
- **超时**: 20s 足够，失败直接跳过（标记为失败即可）。
- **并发**: 不要并发加载——同一 IP 短时间内大量请求会触发微信滑块验证码。顺序处理，每页关闭后再开下一页。

### 4. 已删除文章的识别

如果返回的页面顶层 heading 显示 "此内容因违规无法查看"，说明文章已被微信删除。标记为 `❌ 已删除`。

### 5. 运行环境

这个 Mac 的 Playwright 装在 openbb-env 里：

```bash
/Users/macos/openbb-env/bin/python3 -c "from playwright.sync_api import sync_playwright; print('OK')"
```

playwright browsers 路径：`~/Library/Caches/ms-playwright/chromium-1228/`

### 6. 已知陷阱

- **反爬 CAPTCHA**: 同上 IP 大量请求触发滑块验证码。如果浏览器加载了验证码页面，`eval_on_selector("h1")` 会报找不到元素。控制频率（无并发）。
- **macOS 版 Playwright**: 不需要额外安装浏览器（已在 `~/Library/Caches/ms-playwright/` 中有 Chromium 1228）。
- **标题截断**: 部分文章的 h1 标题可能截断为 `...`，但不影响使用。
- **公众号名缺失**: 不同微信文章模板的 HTML 结构不同，`.rich_media_meta_nickname` 和 `#js_name` 是常见选择器。都不行时标记为空白。
- **反爬检测**: 浏览器环境提示 "Running WITHOUT residential proxies"。如果大量失败（超过 20%），可能是 IP 被临时标记。
- **重拉机制**: 如果一批中有个别失败，可以直接单独重试失败的那些，不需要全量重跑。

## 7. 组织为 Obsidian 笔记

提取标题后，推荐按以下格式生成 Obsidian 笔记：

```markdown
# 微信链接收藏 — Mi8（金同学）

> 主群聊中分享过的公众号文章
> 数据截至 <日期> · 共 N 篇

| # | 标题 | 公众号 |
|---|------|--------|
| 1 | [标题](url) | 公众号名 |
| 2 | [标题](url) | 公众号名 |
...
```

**关键原则**：
- 按时间倒序排列（最新在前）
- 标题可点击（Markdown 链接语法）
- 已删除文章标记 `❌ 已删除`
- 非 weixin 链接（技术博客、proxy 订阅等）单独归类为「其他链接」
- 链接在微信客户端内可直接打开；从浏览器打开可能报"环境异常"（微信反爬），需注明
