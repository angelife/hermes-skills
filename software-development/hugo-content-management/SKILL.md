---
name: hugo-content-management
description: Hugo 内容管理基座：内容盘点、重复检测、归档页去重、分类/系列一致性校验。适用于 blog 迁移后清理、series/posts 重复、frontmatter 审计、站点内容健康度检查。
trigger:
  - 用户说「归档页重复」「内容重复」「去重」「清理重复」
  - 用户怀疑存在 posts/与 series/ 重复内容
  - 需要盘点站点内容、检测 orphan/空分类
  - blog 迁移后清理 Blogger/WP 残留副本
  - 用户问站点性能优化、构建加速、WebP 转换、CSP、Lighthouse 分数
  - 用户说「关于页过时」「架构图页面」「完成度」「合并关于和架构」
  - 用户要求在架构图上标注模块完成状态
  - 用户说「部署」「上线」「发布」— 不中断全流程自动化完成
  - 用户质疑「网站没看到更新」「还没更新」— 先 curl 线上验证再排查
  - 用户说「颜色和网站整体不一致」「页面风格与网站不一致」「栏目风格要一致」— 检查是否使用了 standalone HTML，需转为 Hugo 内容页继承主题
---

# Hugo 内容管理

## 铁律

**用户报告重复时，只信内容级比对，不信标题/URL 文本匹配。用户说“绝大部分内容相同就是相同”时，判定口径放宽到 title/date 重复即视同重复；但最终关闭需要 body similarity 证据，不要仅凭标题删文。**

尤其 Blogger 迁移站点常见 pattern：
- `content/posts/...` 存正文
- `content/series/<分类>/...` 也存一份正文几乎相同的文章
这会导致归档页把同一主体显示两次，但标题可能只有细微差别。

## 检测流程

1. 先按 `(title, date)` 建立索引，分组比对 `posts/`、`series/<name>/` 以及两者之间
2. 对疑似重复对计算 body similarity；ratio ≥ 0.9 视为同文
3. 再输出决策表：保留哪份、删除哪份、是否需要 alias；删除前列出清单，用户确认后执行
4. 若用户只给了标题样本，优先按样本反查对应 pair 做内容级验证，不要盲猜全部

## 决策原则

- **`posts/` 为主权目录**；`series/` 仅为分类视图
- 优先删除 `series/` 内与 `posts/` body 高度重复的文件
- 除非 series 版本有独立 frontmatter 或结构性差异，否则不保留双本
- 删除前给出清单，让用户确认（尤其涉及 5 篇以上时）

## 坑

- **minified HTML 正则提取是陷阱**：大型站点归档页 minify 后无换行，`re.findall(r'<li>...')` 经常返回 0 条。直接扫 source markdown 更稳。
- **title 微调 ≠ 不同文章**：迁移时常见「王石」vs「王石论隐退」这类标题漂移，但正文 99%+ 相同，必须 body hash 或 SequenceMatcher ratio > 0.95 才算重复。
- **GitHub Pages 缓存**：删除/提交后线上可能仍显示旧版 5-10 分钟；确认时抓线上 HTML 看是否还有 series 路径，Series 404 说明本地已生效，线上只是缓存。
- **不要盲猜 regex**：归档页 HTML 提取失败时，先 `grep -n 'post-item' public/archives/index.html | head` 看真实结构，再适配选择器。
- **Static HTML 不继承站点头/脚/主题/评论**（2026-07-16）：用户明确纠正「整体要和网站版面一致吧 这是最基本的 栏目风格要一致吧」。`static/` 下的独立 HTML 文件不经过 Hugo 模板渲染，因此缺失：
  - 站点头部（导航栏）、站点页脚（版权+RSS）
  - giscus 评论
  - 主题样式（颜色、字体、布局）——会导致颜色不一致的独立页面
  **解决方案：** 将需要自定义 HTML 的页面转为 Hugo 内容页 + 自定义布局模板：
  1. 在 `content/<section>/<page>/_index.md` 创建内容页（只有 frontmatter）
  2. 在 `layouts/_default/<layout-name>.html` 创建自定义布局，使用 `{{ define "main" }}` + `{{ partial "header.html" . }}` / `{{ partial "footer.html" . }}` 包含站点头尾
  3. 在 frontmatter 中指定 `layout: "<layout-name>"`
  4. 从 `static/` 删除旧 HTML 文件
  5. SVG/颜色必须适配浅色主题（白底、柔和的色块和边框），与 polk-x 主题一致
  详参考 `references/standalone-html-pages.md` 和 `references/completion-status-table.md`
- **Static HTML 覆盖依赖 content 文件删除**：Hugo 构建顺序是 content → static，static/* 不会覆盖已存在的 content/ 生成页。部署独立 HTML 前必须先 `rm content/.../index.md`。
- **合并页面不留重定向**（2026-07-16）：用户明确纠正「内容以新的为主 旧的淘汰了」。about ≈ 架构图 → 合并到架构图（把关于内容作为架构图页面顶部的介绍段），删 about 全部源文件（content + static），更新所有链接（菜单 config、首页 _index.md、布局模板中的 nav），不留 redirect 或中间页。旧的全删掉。不要保留 "关于" 的独立页面。
- **部署后必须验证线上**：build → rsync → commit → push 做完不等于上线。用户说「网站没看到更新么」说明漏了验证。必须 `curl -s` 或 `web_extract` 抓线上 URL 确认关键内容已更新。
- **部署全流程不中断**：用户说「部署」意味着从 build 到 git push 一次做完。不要在中间问「要推吗」或等确认。推完再告知。用户在多次被要求盯着推后会说「你做事不要老要我盯着」——避免这种纠错的方法：用户说「部署」后直接跑完 build → rsync → git add → commit → push → 在线验证，一步不漏。

## 变更记录

详见 `references/duplicate-detection.md` 的检测脚本模板、`references/hugo-root-sync-discipline.md` 的发布源同步纪律、`references/cross-site-search-unification.md` 的静态内容+Hugo 搜索统一方案，以及 `references/standalone-html-pages.md` 的自定义 HTML 页面部署，和 `references/completion-status-table.md` 的架构图模块状态展示。

## Kindle / 静态内容交付

当需要为静态归档内容（如 `static/old-site/`）提供 Kindle 版入口时：

### 统一脚本模式

脚本 `.scripts/extend-search-index.py` 承担两个任务，通过检查 `public/old-site/` 是否存在自动判断模式：

```python
PUBLIC = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.getcwd(), "hugo-site", "public")
# Mode 1: pre-build — 从 static/old-site/ 读取，生成 layouts/partials/kindle-old-site-list.html
#   扫描 static/old-site/*.html（仅根目录），提取 <title> + os.path.getmtime()
#   输出纯 HTML partial（80 条目，按 mtime 倒序）
# Mode 2: post-build — 从 public/old-site/ 读取，扩展 public/index.json
#   追加 entries：categories="旧站存档", tags="旧站,存档"
#   幂等：跳过 permalink 已存在的条目
```

### 两步 CI 部署（完整 YAML 结构）

```yaml
# Step 1: pre-build（public/ 还不存在，脚本仅执行 mode 1）
- name: Generate Kindle old-site list partial (pre-build)
  run: python3 .scripts/extend-search-index.py

# Step 2: Hugo 构建（partial 已就位，模板可引用）
- name: Build
  working-directory: hugo-site
  run: hugo --gc --minify --cleanDestinationDir

# Step 3: post-build（public/ 已存在，脚本执行 mode 2）
- name: Extend search index with old-site entries (post-build)
  run: python3 .scripts/extend-search-index.py
```

### 旧站 banner 更新

首次注入 Python 脚本（`add-oldsite-banner.py`）用 `re.sub(r'(<body[^>]*>)', ...)` 在 `<body>` 后插入横幅。

后续追加链接（如增加 Kindle 版入口）必须用 Python 字符串 slice，**不要用 sed**——sed 含中文/特殊字符的 attribute 值会报 `bad flag in substitute command`：

```python
idx = content.find('</div>', content.find('background:#fff8e1'))
content = content[:idx] + KINDLE_LINK + content[idx:]
```

### 设备检测

- Kindle 设备通过 UA 匹配 `/Kindle|Silk|KFTT|KF[A-Z]+/` 检测
- `reader-redirect.js`（存于 `hugo-site/static/js/reader-redirect.js` 和根 `js/reader-redirect.js`）
  - 新站 `/posts/:slug/` → 重定向到 `/kindle/posts/:slug/`
  - 首页 `/` / `/index.html` → 重定向到 `/kindle/`
  - 旧站 `/old-site/` → 加 `?kindle=1` 参数非做跳转（静态 HTML 可直接渲染）
  - `?normal=1` 或 `?desktop=1` 参数强制桌面视图
- **必须同步两份**：`hugo-site/static/js/`（Hugo 构建使用）和根 `js/`（根目录静态页面使用）

### 导航栏链接

```toml
[[menu.main]]
  name = "📖 Kindle"
  url = "/kindle/"
  weight = 45
```

首页不显示顶栏导航（`header.html` 含 `{{ if not .IsHome }}`），需进入内页才能看到。

### CI 路径陷阱

`extend-search-index.py` 必须使用相对路径（`os.getcwd()`），不能硬编码 `~/angelife.github.com/hugo-site/public`。GitHub Actions 的 `$HOME` 是 `/home/runner/`，但仓库 checkout 在 `$GITHUB_WORKSPACE`（`/home/runner/work/<repo>/<repo>/`），硬编码路径在 CI 上静默失败。`b0b39e04` 修复过这个问题。

## 坑：封面图 frontmatter 格式不一致

Hugo 站存在两种 `cover.image` 写法：

1. **标准写法**：`cover:\n  image: /images/posts/.../cover.png`（缩进在 cover 下）
2. **旧写法**：`cover: []\nimage: /images/posts/.../cover.png`（image 是顶级字段）

第 2 种写法 frontmatter 里虽然有图片路径，但主题模板读取 `cover.image` 时拿不到，导致文章无封面显示。

### 批量修复

```python
import re
from pathlib import Path

site = Path('content/posts')
for md in site.rglob('index.md'):
    content = md.read_text()
    
    # 匹配 cover: [] + image: 分行
    if 'cover: []' in content and re.search(r'^image:\s*/images/', content, re.MULTILINE):
        m = re.search(r'^image:\s*(.*)', content, re.MULTILINE)
        if m:
            img_path = m.group(1).strip()
            new_content = re.sub(
                r'^(cover:\s*\[\])\n(image:\s*/images/[^\n]+)',
                lambda mo: f'cover:\n  image: {mo.group(2).split(":",1)[1].strip()}',
                content, count=1, flags=re.MULTILINE
            )
            md.write_text(new_content)
```

### 验证

```python
import re
from pathlib import Path

site = Path('content/posts')
total = with_cover = 0
for md in site.rglob('index.md'):
    total += 1
    if re.search(r'^cover:\s*\n\s*image:', md.read_text(), re.MULTILINE):
        with_cover += 1
print(f"Total: {total}, With cover: {with_cover}")
# 目标：103/103
```

## Hugo 构建优化（性能 + 安全）

以下技巧适用于提升 Hugo 站点的 Lighthouse 评分、页面加载速度和安全性。

### 1. 构建标志

`hugo --gc --minify --cleanDestinationDir` 已是我们 CI 的标准命令：

| 标志 | 作用 |
|------|------|
| `--gc` | 构建后运行垃圾回收，删除未使用的缓存文件 |
| `--minify` | 压缩 HTML / CSS / JS 输出（移除多余空白、注释） |
| `--cleanDestinationDir` | 删除旧构建的残留文件，避免新旧文件混合 |

**验证**: 用 `hugo --gc --minify --templateMetrics --templateHints` 获取模板性能指标。

### 2. WebP / AVIF 图片转换

Hugo 内置 `images.Processor` 支持在构建时批量转换图片格式。在模板中（如 `_default/single.html`）：

```go-html-template
{{ $img := .Resources.GetMatch "cover.*" }}
{{ if $img }}
  {{ $webp := $img.Process "webp q80" }}
  <picture>
    <source srcset="{{ $webp.RelPermalink }}" type="image/webp">
    <img src="{{ $img.RelPermalink }}" alt="{{ .Title }}">
  </picture>
{{ end }}
```

更多格式选项：
- `webp q80` — WebP 质量 80%
- `avif q60` — AVIF 质量 60%（比 WebP 更小但某些浏览器不支持）
- `resize 800x webp` — 缩放 + 格式转换

**注意**: 这只对 Hugo **页面资源**（page bundle 内的图片）生效。`static/` 目录下的图片不会自动处理，需外部工具（`cwebp`, `imagemagick`）预处理。

### 3. Content-Security-Policy (CSP)

在部署层（nginx / Caddy / Cloudflare Workers）设置 CSP 头可大幅提升安全性：

```nginx
# nginx 示例
add_header Content-Security-Policy "
  default-src 'self';
  img-src 'self' https: data:;
  script-src 'self' 'unsafe-inline';
  style-src 'self' 'unsafe-inline';
  font-src 'self' https://fonts.gstatic.com;
  frame-ancestors 'none';
" always;
```

对于全静态站点，`default-src 'self'` 是最严格的起点，根据需要放宽。

### 4. 预压缩 (Pre-compression)

对于 nginx / Caddy 反向代理，可以预生成 `.gz` 和 `.br` 文件让服务器直接发送，避免实时压缩消耗 CPU：

```bash
# 对整个 public/ 目录预压缩
find public/ -type f \( -name "*.html" -o -name "*.css" -o -name "*.js" \) \
  -exec gzip -kf {} \; \
  -exec brotli -kf {} \;
```

Hugo 未来版本可能内置 pre-compression 支持（相关讨论进行中），届时可替代手动脚本。

### 参考文章

Julien Wittouck. "Optimizing a Hugo site's performance and security." *Codeka.io*, Feb. 2026.
https://codeka.io/en/2026/02/20/optimizing-a-hugo-sites-performance-and-security

## 变更记录

- 2026-07-05：建立技能，收录内容去重流程、坑点、缓存校验方法。
- 2026-07-06：新增“仓库根目录 = GitHub Pages 发布源”同步纪律。
- 2026-07-09：新增 Kindle/静态内容交付、两步 CI 模式、设备检测 redirect 模式。
- 2026-07-09：细化 Kindle 部分——统一脚本模式、CI YAML 片段、banner 更新技术、reader-redirect 双同步要求、CI 路径陷阱（`b0b39e04`）。
- 2026-07-10：新增封面图 frontmatter 格式不一致检测与批量修复方案。
- 2026-07-14：新增「Hugo 构建优化」章节（WebP/AVIF 转换、CSP 头、预压缩、build flags）。
- 2026-07-16：新增「Static HTML 不继承主题」陷阱 + 自定义布局模板模式；强化「部署全流程不中断」；细化「合并页面不留重定向」操作清单；更新 completion-status-table 参考加 light 配色。
