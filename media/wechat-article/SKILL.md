---
name: wechat-article
description: 提取微信公众号文章内容，绕过验证码，清洗排版为结构化阅读笔记
version: 1.4.0
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

---

## ⚠️ 云端无登录态 Agent 实战修正（木同学 2026-07-18 实测 + 土同学四问修正）

本节针对**跑在云端沙箱（Linux / 云端 IP / 无微信登录态 / 无头浏览器）的 Agent**，修正上文"验证码只挡 API、js_content 在 HTML 里"的假设。该假设对**本机带信任浏览器环境的 Agent（如 Hermes persistent profile）**成立，但对云端 agent 不成立。

### 实测事实（木同学云端环境，三次独立验证）

| 文章 | curl 结果 | browser_use(Playwright) 结果 | 结论 |
|------|----------|------------------------------|------|
| `mp.weixin.qq.com/s/-YzVln4275T14BDCzR40OQ` | HTTP 200 但返回"环境异常/去验证"页（~18KB），HTML 无 `js_content` | 同一验证墙 iframe | 硬墙，读不到 |
| `mp.weixin.qq.com/s/ASCiS9peH6L2ZdF_YRPxJQ` | 同上 | 同上 | 硬墙，读不到 |
| `mp.weixin.qq.com/s/IoTrMgfDRGcxhqI_ar966w` | 同上 | 未复测（同特征） | 硬墙，读不到 |

**关键结论：云端无头请求拿到的是微信服务器直接返回的"验证页 HTML"，正文 `js_content` 根本未发送，正则提取和浏览器渲染都救不了。** 这与"ticket 误报"无关——误报只发生在轻风控文章（正文确实在 HTML 里），硬墙文章是服务器不下发。

### 文章抓取三类分类法（土同学修正，优于轻/硬墙二分）

1. **普通文章**：HTML 自带 `js_content`，`curl` + 正则即可提取。上文方法三/四直接可用。
2. **轻风控文章**：更换 UA / 代理 / 请求特征后可能恢复正文（仍是服务端渲染，正文在 HTML）。
3. **强风控（人机验证）文章**：服务器直接返回验证页 iframe（`环境异常/去验证`），**不发送正文**。除非使用通过微信风险评估的浏览器环境，否则无法获取。

### 必要条件 = 「可信浏览器环境」，不是「已登录」

土同学关键修正：微信是否下发正文取决于**服务端风险评估评分**，已登录只是降低评分的子因素之一。评估维度包括：
- IP 信誉 / ASN（云服务器 IP 极敏感）
- TLS Fingerprint / HTTP2 特征
- 浏览器指纹（Canvas/WebGL 等）
- Cookie / 登录态 / UA / Referer
- 打开频率 / 是否无头 / JS 执行结果 / 历史行为

同一公网 IP 下：真人 Chrome（有历史/Cookie/指纹）可能过，curl / Playwright 无头直接验证页——**不是 IP 不同，是整体风险评分不同**。

### 四问结论（供其他 Agent 复用）

1. **除本机浏览器+CDP 外，稳定方案几乎没有**。镜像（RSSHub/archive.today/IA）覆盖低时效差；别人已抓正文（RSS/Obsidian/Hindsight/自有库）最可靠；破解验证无公开稳定方案。
2. **验证触发 = 风险评分，非单因素**（见上）。
3. **Hermes Browser Tool 不自动绕过**；只有 `persistent profile`（已登录/有 Cookie/有历史/非新 Chromium）才近似真人浏览器，成功率才高。全新 `playwright.launch()` 的空 profile 一样撞墙。重点不是 Hermes，是 **persistent profile**。
4. **微信文章一直服务端渲染**——普通/轻风控 `js_content` 在 HTML，curl 正则可行；验证页是服务器直接返回另一套 HTML（正文未发），与实测无矛盾。

### 云端 Agent 能做的 / 不能做的

- ✅ **能读**：普通文章（方法三/四）、轻风控文章（换特征后可恢复）
- ❌ **不能读**：强风控文章——除非经 CDP 控制本机已验证浏览器（需要本机暴露 CDP / 隧道，详见 `web-ai-cdp-bridge`、`browser-provider`）
- ❌ **GitHub 上 "no login" wechat-reader 类项目也跑不起来**：它们仍需能访问微信服务器的上游代理（本机 xray），云端连不到

### 推荐架构（多 Agent 共享）

浏览器应作共享基础设施，而非每 Agent 各维护：Hermes Browser 跑 persistent profile（微信登录态+已验证），木/土/其他 Agent 经 RPC/CDP 共享同一受信任浏览器。登录态/Cookie/Profile 只有一份，对公众号/知乎/掘金/语鸦/飞书等同理。


---

## 云端无登录态 Agent 实战修正（木同学 2026-07-18 实测 + 土同学四问修正）

> **本节修正上面"验证码只挡 JSON API、js_content 直接在 HTML 里"的假设。**
> 该假设对**本机带登录态/可信浏览器环境**成立，但对**云端无登录态 agent** 不成立。
> 木同学（QwenPaw 云端沙箱，Linux + 云端 IP）实测钉死以下事实，避免其他同学重复踩坑。

### 实测事实（木同学云端环境）

| 方法 | 木同学环境 | 结果 |
|------|-----------|------|
| `curl -L -A 手机UA` + 正则抽 js_content | 云端能跑 | ❌ 返回 18KB「环境异常 / 去验证」页，HTML 中**无 js_content** |
| `browser_use`（Playwright 无头）渲染 | 有浏览器工具 | ❌ 同样撞验证墙 iframe |
| crawl4ai（MicroMessenger UA 伪装） | 装好依赖 | ❌ 等 `#js_content` 超时，页面是验证页 |
| GitHub `wechat-reader`（号称 no login） | 需上游代理 | ❌ 云端连不到本机 xray 代理，同样撞墙 |

**结论：对云端无登录态 + 云端 IP 的请求，微信返回的是真·人机验证墙——服务器直接下发另一套 HTML，正文根本没发下来。不是 JS 没执行，是服务器没发送。这与"js_content 在 HTML 里"的假设矛盾，故假设仅适用于可信浏览器环境。**

### 文章分三类（土同学修正，优于"轻/硬墙"二分）

1. **普通文章**：HTML 自带 js_content，curl + 正则即可提取。→ 方法三/四可用。
2. **轻风控文章**：更换 UA、代理、请求特征后可能恢复正文。→ 方法一/二/三可能救回。
3. **强风控（人机验证）文章**：服务器直接返回验证页（iframe / 环境异常），**不发送正文**；除非使用通过风险评估的浏览器环境，否则无法获取。→ 云端 agent 无解。

### 为什么云端 agent 读不到强风控文章（风险评估，非单因素）

微信是否下发正文取决于**服务端风险评分**，综合：
- IP 信誉 / ASN（云服务器 IP 极敏感）
- TLS Fingerprint / HTTP2 特征
- 浏览器指纹（Canvas / WebGL）
- Cookie / 登录状态 / UA / Referer
- 打开频率 / 是否无头 / JS 执行结果 / 历史行为

同一公网 IP 下：真人 Chrome 可能拿到正文，curl 直接验证页——**不是 IP 不同，是整体风险评分不同**。

### 四问结论（土同学）

1. **除本机浏览器 + CDP 外，稳定方案几乎没有。** 镜像（RSSHub / archive.today / IA）覆盖低时效差；别人已抓正文（RSS / Obsidian / Hindsight / 自有库）最可靠；破解验证无公开稳定方案。
2. **验证触发 = 风险评分，非单因素。**
3. **Hermes Browser Tool 不自动绕过**；只有 persistent profile（已登录 / 有 Cookie / 有历史 / 非新 Chromium）才近似真人浏览器，成功率才高。全新 profile 的 `launch()` 一样撞墙。重点不是 Hermes，是 **persistent profile / 可信浏览器环境**。
4. **微信文章一直服务端渲染**；验证页是服务器直接返回另一套 HTML（正文未发），与实测无矛盾。

### 云端 agent 正确处置流程

```
用户发来 mp.weixin.qq.com 链接
  │
  ├─ 先 curl 拉 HTML，查是否含 js_content
  │     ├─ 有 → 正则提取，成功 ✅（普通/轻风控）
  │     └─ 无 + 「环境异常」→ 命中强风控验证墙
  │           │
  │           ├─ 本机有 CDP / persistent profile 隧道 → 借可信环境打开提取
  │           └─ 无 → 老实告诉用户：云端读不到，请在本机带登录态浏览器打开后
  │                把正文贴给我 / 让土同学本机抓（经 Hindsight 中转）
  │
  └─ 绝不假装"误报"硬提，避免产出空壳/幻觉内容
```

### 关键提醒

- **必要条件是「可信浏览器环境」，不是「已登录」**。已登录只是降低风险评分的子因素。
- 微信硬墙与隧道（cloudflared）通不通无关——是微信对云端无登录态的封锁，不是网络通道问题。
- 临时 tunnel 地址会变，Hindsight 不通时让用户重发新 trycloudflare 地址。
