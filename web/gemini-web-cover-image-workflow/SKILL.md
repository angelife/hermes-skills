---
name: gemini-web-cover-image-workflow
description: >
  通过 Gemini Web CDP 桥接为 Hugo 文章生成 AI 配图的全流程。
  包括：文章内容发送 → Gemini 配图建议 → 生成图像 → 从页面提取 → 保存到 static/ → 设置 cover frontmatter → 发布。
category: web
version: 1.0
---

# Gemini Web 配图生成全流程

用 Gemini Web 的免费多模态能力给 Hugo 文章生成配图，不花一分钱 API 费用。

## 触发条件

- 用户写完一篇 Hugo 文章，需要封面/配图
- 用户问"这个文章配什么图"
- 需要零成本的多模态 AI 图像生成

## 前置条件

1. Chrome CDP 已启动（端口 9222）
2. Gemini 已登录（`--user-data-dir` 保持登录态）
3. `hermes-gemini-web` skill 的脚本在 `~/.hermes/skills/hermes-gemini-web/scripts/`

## 工作流

### 1. 启动 Chrome CDP

```bash
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
  --remote-debugging-port=9222 \
  --user-data-dir=/Users/macos/.chrome-debug-profile \
  --proxy-server=http://127.0.0.1:10808 \
  --disable-quic \
  --no-first-run \
  --disable-features=ChromeWhatsNewUI \
  2>/tmp/chrome-cdp.log
```

**关键点：** `--user-data-dir` 必须指定，Chrome 禁止默认 Profile 开 CDP。如果 Profile 无 Gemini 登录态，先从主 Chrome Profile 复制 Cookies/Login Data。

### 2. 发文章内容让 Gemini 提方案

```bash
ARTICLE=$(cat content/posts/<slug>/index.md)
node index.js "我写了一篇博客文章，以下是全文。请为这篇文章推荐3种配图方案（描述画面内容、风格和构图）。\n\n---\n${ARTICLE:0:3000}"
```

Gemini 会返回 3 个方案。选一个最贴合文章的。

### 3. 让 Gemini 生成图片

用选定方案的描述作为 prompt 发给 Gemini：

```bash
node index.js "根据方案X（详细描述），请生成一张配图..."
```

### 4. 从 Gemini 页面提取图片

Gemini 生成的图片在页面中以 `<img>` 形式出现，src 是 blob URL。用 CDP 提取：

```python
# 通过 CDP Page.captureScreenshot 截取图片区域
# 或 canvas.toDataURL (注意 WebSocket 消息大小限制 1MB)
```

**推荐方式：** CDP 的 `Page.captureScreenshot` 带 `clip` 参数，直接截取图片所在区域。

图片坐标从 `img.getBoundingClientRect()` 获取。

### 5. 保存到 Hugo 目录

```bash
mkdir -p hugo-site/static/images/posts/<slug>/
# 保存为 cover.png
```

### 6. 设置文章 cover frontmatter

在 `index.md` 的 frontmatter 中追加：

```yaml
cover:
  image: /images/posts/<slug>/cover.png
```

### 7. 提交发布

```bash
git add hugo-site/static/images/posts/<slug>/cover.png \
       hugo-site/content/posts/<slug>/index.md
git commit -m "feat: add AI-generated cover image for <title>"
git push
```

### 8. 验证

访问 `https://angelife.github.io/posts/<slug>/` 确认封面图正常显示。

## 关键陷阱

### Chrome CDP 启动
- 必须加 `--user-data-dir`，否则 Chrome 拒绝 CDP
- 不能用默认 Profile，会报 "DevTools remote debugging requires a non-default data directory"
- 多个 Chrome 实例不要冲突：先 `pkill -x "Google Chrome"` 再启动

### 登录态
- Cookie 文件跨 Profile 复制不生效（Chrome 加密绑定 Profile）
- 最可靠方式：用户手动在 CDP Chrome 窗口登录一次，`--user-data-dir` 会保持登录

### 图片提取（避免 UI 污染）

Gemini 生成的图片以 `<img>` 出现在页面，src 是 blob URL（不能 curl 下载）。

**提取方式优先级：**

1. **Playwright `page.screenshot({clip})`** — 最可靠。不会像 CDP WebSocket 那样被 1MB 消息限制截断，适合高清图
2. **CDP `Page.captureScreenshot`** — 需要 clip，高 scale 时可能超 websocket 上限
3. **canvas.toDataURL** — 小图可用，大图会超 1MB WebSocket 限制

**关键陷阱：clip 必须紧贴图片边界，绝不加 padding。**

```
// ❌ 错 — 加 padding 会截到 Gemini UI
clip = { x: r.x-15, y: r.y-15, width: r.w+30, height: r.h+30 }

// ✅ 对 — 紧贴边界
clip = { x: r.x, y: r.y, width: r.w, height: r.h, scale: 2 }
```

Gemini 界面的麦克风按钮、发送按钮、"使用麦克风"标签紧邻图片，padding 超过 2px 就会把 UI 元素截进来，封面图上会出现"使用麦克风"字样。如果已经污染了，收紧 clip 重新截图即可。

**推荐的 Node.js 工具（web-ai-cdp-bridge skill）：**
```js
const { chromium } = require('playwright-core');
const page = await browser.page();
const buf = await page.screenshot({ clip: { x, y, w, h, scale: 2 } });
```

### CAPTCHA 拦截
- 机房 IP 触发 Google 验证码概率 > 90%
- 需要用户手动过验证码后继续
- 家庭宽带/手机热点出口 IP 存活时间更长
- 模拟人类行为（可变打字延迟、鼠标移动、粘贴长文本）只能延缓检测，不能根治

## 相关文件

- `~/.hermes/skills/hermes-gemini-web/scripts/index.js` — 入口
- `~/.hermes/skills/hermes-gemini-web/scripts/composer.js` — 输入模拟（含人类行为）
- `~/.hermes/skills/hermes-gemini-web/scripts/reader.js` — 回复提取（按 "Gemini 说" 分段）
- `~/.hermes/skills/hermes-gemini-web/scripts/browser.js` — CDP 连接管理
- `~/.hermes/skills/hermes-gemini-web/scripts/page.js` — Gemini Tab 查找/打开

## 替代方案

如果 Gemini Web 频繁触发 CAPTCHA，改用 API 路线：
- Google Gemini API（`generativelanguage.googleapis.com`）— 需要 key，无 CAPTCHA
- 内置 `image_generate` 工具 — 需要 FAL_KEY 配置
