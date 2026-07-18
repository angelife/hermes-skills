---
name: wechat-article
description: 提取微信公众号文章内容，绕过验证码，清洗排版为结构化阅读笔记
version: 1.3.0
author: Hermes Agent
tags: [wechat, weixin, 微信公众号, 文章提取, 内容抓取]
---

# WeChat Article — 微信公众号文章提取

## 概述

提取微信公众号文章（`mp.weixin.qq.com`）正文内容，支持：
- 绕过微信防爬验证码
- 清洗 HTML 为可读 Markdown
- 提取标题、作者、发布时间
- 结构化摘要（book-to-skill 风格）

## 使用场景

- 用户发来公众号链接，需要你看内容
- 需要把公众号文章整理为笔记 / 摘要
- 需要把多篇公众号文章合并为 skill

## 核心方法（按推荐优先级排列）

### 方法一（推荐首选）：web_extract 直接拉取

**Hermes 内置工具，零依赖，零设置，一调用就出结果。**

```python
web_extract(urls=["https://mp.weixin.qq.com/s/<ARTICLE_ID>"])
```

**为什么能绕过验证码？** 微信的验证码/风控墙只挡 JSON API 调用，不挡页面 HTML 本身。大多数公众号文章的正文直接渲染在 HTML 的 `js_content` div 中。所以 `web_extract` 能直接提取到完整内容，不需要任何额外工具。

**判定标准：** 页面 > 1MB 时，即使有验证码拦截，正文大概率已在 HTML 中。页面 < 10KB 时才是真正被完全拦截。

**优点：** 零依赖、零设置、一调用就出结果、不消耗额外 token。
**缺点：** 少数纯 JS 动态加载的文章无法提取（此时降级到方法二）。

---

### 方法二：Hermes 浏览器工具（JS 动态渲染时使用）

当 `web_extract` 提取到的 `js_content` 为空（内容由 JS 动态渲染）时，使用 Hermes 内置浏览器工具。

**操作步骤：**
```python
# 1. 用 browser_navigate 打开文章 URL
# 2. 用 browser_snapshot(full=true) 获取渲染后页面内容
# 3. 从 snapshot 中提取标题和正文
```

**优点：** 零额外依赖（Hermes 自带），能渲染 JS 动态内容。
**缺点：** 消耗 token，比 web_extract 慢。

---

### 方法三：curl + Python 提取（备选）

```bash
curl -s -L -A "Mozilla/5.0 ..." "URL" -o /tmp/raw.html
python3 -c "
import re, html
with open('/tmp/raw.html') as f: c = f.read()
m = re.search(r'id=\"js_content\"[^>]*>(.*?)</div>\s*<script', c, re.DOTALL)
if m: print(html.unescape(re.sub(r'<[^>]+>', '', m.group(1))))
"
```

### 方法四：OpenCLI weixin download（最可靠但需额外设置）

绕过微信 JS 动态渲染和扫码墙的最可靠方式，但需要 OpenCLI + Chrome 扩展。仅当前三种方法都失败时使用。

**前提条件：** 见原文档。</think>

<｜DSML｜tool_calls>
<｜DSML｜invoke name="memory">
<｜DSML｜parameter name="target" string="true">user

绕过微信 JS 动态渲染和扫码墙的最可靠方式。需要 OpenCLI + Chrome 扩展。

**前提条件：**
```bash
# 1. 装 OpenCLI（Node.js）
npm install -g @jackwener/opencli

# 2. 验证安装
opencli --version      # 应输出 v1.8.x

# 3. 装 OpenCLI Chrome 扩展（⚠️ 注意：不是普通的 Browser Bridge！）
# 正确扩展 ID: ildkmabpimmkaediidaifkhjpohdnifk
# 错误扩展 ID: jbajonmonccnibicpjlfkkcenpjcpedo（btraut 的普通 Browser Bridge，端口 3210，不可用）
# 安装地址: https://chromewebstore.google.com/detail/opencli/ildkmabpimmkaediidaifkhjpohdnifk

# 4. 验证扩展连接
opencli doctor
# → [OK] Extension: connected (v1.x.x)
# → [OK] Connectivity: connected in X.Xs

# 5. 如果显示"Extension: not connected"
#    → 检查是否装错了扩展（btraut 的 Browser Bridge 连 3210 端口，对不上 daemon 的 19825）
#    → 卸载错误的扩展，装正确的 OpenCLI 扩展
#    → 或重启 daemon: opencli daemon restart
```

**使用方法：**
```bash
# 下载公众号文章为 Markdown（自动提取正文 + 作者 + 发布时间）
opencli weixin download --url "https://mp.weixin.qq.com/s/<ARTICLE_ID>"

# 输出到指定目录
opencli weixin download --url "https://mp.weixin.qq.com/s/<ARTICLE_ID>" --output ./articles

# JSON 格式输出（方便程序处理）
opencli weixin download --url "https://mp.weixin.qq.com/s/<ARTICLE_ID>" -f json

# 搜索公众号文章（不需要扩展）
opencli weixin search "关键词"
```

**输出：** 自动创建 `weixin-articles/<标题>/<标题>.md`，含 frontmatter（标题、作者、时间、原文链接）+ 正文 Markdown + 图片下载。

**优点：** 零 token 成本、绕过扫码墙、自动提取元数据、自动下载图片。
**缺点：** 需要 Chrome 在后台运行（进程占用约 200MB 内存）。

---

### 方法二：Hermes 浏览器工具（快速落地，无 OpenCLI + JS 动态渲染时推荐）

当 OpenCLI 不可用，且 curl 下载的页面中 `js_content` 为空（内容由 JS 动态渲染）时，使用 Hermes 内置浏览器工具直接从渲染后的页面提取。

**前提条件：** Hermes 浏览器 provider 可用（`hermes-browse` 或 OpenBridge）。

**操作步骤：**
```python
# 1. 用 browser_navigate 打开文章 URL
# 2. 用 browser_snapshot(full=true) 获取渲染后页面内容
# 3. 从 snapshot 中提取标题和正文
```

**优点：** 零额外依赖（Hermes 自带），能渲染 JS 动态内容，有页面的 browser tool 即可。
**缺点：** 消耗 token（页面内容进入上下文），不适合批量处理。

**快速判断：** curl 下载页面 > 1MB 但 `js_content` 为空 → 尝试浏览器工具。

---

### 方法三：curl + Python 提取（备选，无 OpenCLI 时）

```bash
# Step 1: 下载页面
curl -s -L -A "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36" \
  "https://mp.weixin.qq.com/s/<ARTICLE_ID>" -o /tmp/wechat_article.html

# Step 2: 用 Python 从 js_content 提取正文
python3 -c "
import re, html
with open('/tmp/wechat_article.html', 'r', encoding='utf-8', errors='ignore') as f:
    content = f.read()

match = re.search(r'id=\"js_content\"[^>]*>(.*?)</div>\s*<script', content, re.DOTALL)
if match:
    raw = match.group(1)
    text = html.unescape(raw)
    text = re.sub(r'<[^>]+>', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    print(text)
else:
    # 备选：找 title（微信公众号 <title> 常为空，用 og:title 兜底）
    title = ''
    title_m = re.search(r'<title>(.*?)</title>', content)
    if title_m and title_m.group(1).strip():
        title = html.unescape(title_m.group(1).strip())
    if not title:
        og_m = re.search(r'<meta[^>]+property=\"og:title\"[^>]+content=\"([^\"]+)\"', content)
        if og_m:
            title = html.unescape(og_m.group(1).strip())
    if title:
        print('标题:', title)
    print('无法提取正文（可能被微信验证码拦截，建议升级到方法一）')
"

**局限：** 部分文章用纯 JS 动态加载正文，HTML 中 `js_content` 为空，curl 无法提取。此时需要方法一或方法二。

### 方法四：直接 JS 正文提取（当 extract.py 误报"验证码拦截"时）

⚠️ **已知坑：** extract.py 曾因检测 `ticket` 字符串导致误报（`ticket` 在正常页面 JS 中也会出现）。2026-06 已修复此问题。

如果你下载的 HTML 文件 > 1MB 但 extract.py 报错，可以直接手动提取：

```bash
# 下载页面
curl -s -L -A "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36" \
  "https://mp.weixin.qq.com/s/<ARTICLE_ID>" -o /tmp/wechat_raw.html

# 手动提取 js_content
python3 -c "
import re, html
with open('/tmp/wechat_raw.html', 'r', encoding='utf-8', errors='ignore') as f:
    content = f.read()
m = re.search(r'id=\"js_content\"[^>]*>(.*?)</div>\s*<script', content, re.DOTALL)
if m:
    text = html.unescape(m.group(1))
    text = re.sub(r'<br\s*/?>', '\n', text)
    text = re.sub(r'<[^>]+>', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    print(text)
else:
    print('js_content 未找到')
"
```

**判定标准：** 页面 > 1MB 时，即使 extract.py 报"验证码拦截"，也有大概率能直接提取到正文。文件 < 10KB 时才是真正被完全拦截。

## 结构化输出

提取正文后，按以下格式组织：

```markdown
**标题：** 《原文标题》
**作者：** 作者名
**来源：** [公众号名称](原文链接)
**发布时间：** YYYY-MM-DD

**核心观点：**
- 观点一（来自第 X 段）
- 观点二（来自第 X 段）

**关键术语/概念：**
| 术语 | 解释 | 来源章节 |
|------|------|---------|
| term | 定义 | 第 X 段 |

**框架/方法论（如有）：**
1. 步骤一
2. 步骤二

**金句摘录：**
> "原文引用的金句"
```

## 进阶用法：文章 → Skill

如果需要将公众号文章转为可复用的 Hermes Skill（book-to-skill 模式）：

1. 提取正文 + 元数据
2. 拆解为：心智模型 / 关键概念 / 操作步骤 / 术语表
3. 用 `skill_manage(action='create')` 写入 `.hermes/skills/`

## 备用提取方案（验证码拦截时仍然能提取部分内容）

当 `extract.py` 报"微信验证码拦截"时，部分文章页面仍然在 HTML 中嵌入了完整的 `js_content` div（微信将正文渲染在页面中，验证码只挡 JSON API 调用）。

此时可以用 Python 直接从页面源码提取：

```python
import re, html

with open('/tmp/wechat_article.html', 'r', encoding='utf-8', errors='ignore') as f:
    content = f.read()

m = re.search(r'id="js_content"[^>]*>(.*?)</div>\s*<script', content, re.DOTALL)
if m:
    raw = m.group(1)
    text = html.unescape(raw)
    text = re.sub(r'<br\s*/?>', '\n', text)
    text = re.sub(r'<[^>]+>', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    print(text)
else:
    print('正文也未嵌入页面，完全无法提取')
```

注意：这种方法只对正文直接渲染在 HTML 中的文章有效，较新或强保护的公众号可能会用纯 JavaScript 加载正文。

### 常见失败模式

| 现象 | 原因 | 处理 |
|------|------|------|
| 页面 2MB+ 但 extract.py 报验证码拦截 | ❌ extract.py 旧版检测 `ticket` 字符串导致误报（2026-06 已修复） | 直接 js_content 正则提取，见方法四 |
| 提取到大量乱码 | HTML 实体编码未 decode | 用 `html.unescape()` 再处理一次 |
| 内容为空白/仅标题 | js_content 被动态渲染（纯 JS 加载） | 需用 OpenCLI `weixin download` 或方法二（Hermes 浏览器工具）渲染后提取 |
| 提取标题为空 | 微信公众号 `<title>` 标签常为空白或编码内容，纯 `<title>` 正则提取不到 | 使用 `og:title` meta 标签兜底：`<meta property="og:title" content="..." />` |
| 页面显示"Parameter error"空白页 | 链接已失效/过期，或用户复制时截断了 URL（微信内复制常缺少完整参数） | 先向用户确认链接是否完整。完整仍报错则可能被风控拦截。尝试 r.jina.ai 代理或走浏览器渲染 |
| 提取内容不全 | 文章太长被截断 | 检查 `js_content` div 是否完整闭合 |
| OpenCLI `opencli doctor` 持续报 "Extension: not connected" | 装错了扩展：装了 btraut 的普通 Browser Bridge（ID: jbajonmonccnibicpjlfkkcenpjcpedo，端口 3210），而非 jackwener 的 OpenCLI 扩展（ID: ildkmabpimmkaediidaifkhjpohdnifk，端口 19825） | 卸载错误扩展，从 Chrome Web Store 装 https://chromewebstore.google.com/detail/opencli/ildkmabpimmkaediidaifkhjpohdnifk |

## 依赖

- `curl`（系统自带）
- `python3`（系统自带）
- `html` 标准库（系统自带）

无需额外安装。
