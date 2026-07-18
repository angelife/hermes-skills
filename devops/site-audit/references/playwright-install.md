# Playwright 安装记录

## 问题背景

Python Playwright 包通过 PyPI 源下载超时（41.4MB 包在中国网络环境下）。

## 解决方案

### 使用阿里云镜像安装 Python 包

```bash
cd ~/angelife.github.com/site_audit
uv pip install playwright -i https://mirrors.aliyun.com/pypi/simple/
```

安装结果：
- `playwright==1.61.0`
- `greenlet==3.5.3`
- `pyee==13.0.1`
- `typing-extensions==4.16.0`

### 安装 Chromium 浏览器二进制

Playwright 的 npm 版已在用户目录安装 Chromium：
```
~/Library/Caches/ms-playwright/chromium-1228/
~/Library/Caches/ms-playwright/chromium_headless_shell-1228/
```

Python Playwright 需要单独安装浏览器：
```bash
cd site_audit/.venv/bin/playwright install chromium
```

或使用 npm 版的缓存路径链接。

## 验证

```python
from playwright.sync_api import sync_playwright
p = sync_playwright().start()
b = p.chromium.launch(headless=True)
page = b.new_page()
page.goto('https://example.com')
print(page.title())  # "Example Domain"
```

## 替代方案（不推荐）

Node.js Playwright via subprocess — 曾尝试但增加了进程通信复杂度，最终弃用。
