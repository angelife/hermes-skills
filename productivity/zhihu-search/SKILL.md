---
name: zhihu-search
description: 知乎官方 API 搜索 — 站内搜索 / 全网搜索 / 热榜。直接调用 developer.zhihu.com 接口，返回结构化结果。
tags: [zhihu, search, 知乎]
triggers:
  - "搜一下 X"
  - "知乎搜 X"
  - "站内搜索 X"
  - "全网搜索 X"
  - "搜索 X"
  - "search X"
  - "用双引擎搜 X"
---

# Unified Search — 知乎 + Tavily 双引擎搜索

## 核心工作流

当用户要求搜索某主题时，**同时调用知乎站内搜索 + Tavily 全网搜索**，合并输出。

## 为什么双引擎

| | 知乎搜索 | Tavily |
|---|---|---|
| 范围 | 知乎站内（问答/文章） | 全网（新闻/技术文档/博客） |
| 优势 | 中文社区质量高，有投票排序 | 时效性强，覆盖面广 |
| 适合 | "X 好用吗"、"X 深度评测" | "X 价格"、"X 最新动态" |
| 互补 | 社区口碑/深度内容 | 即时信息/技术文档 |

## 搜索引擎配置

### 知乎搜索

| 端点 | 方法 | URL |
|---|---|---|
| 全网搜索 | GET | `https://developer.zhihu.com/api/v1/content/global_search` |
| 站内搜索 | GET | `https://developer.zhihu.com/api/v1/content/zhihu_search` |
| 热榜 | GET | `https://developer.zhihu.com/api/v1/content/hot_list` |

**认证要求：**
- `Authorization: Bearer <ZHIHU_API_KEY>` — 从 `~/.hermes/.env` 读取
- `X-Request-Timestamp: <动态 unix 秒>` — 每次请求前重新生成，5 分钟前失效
- 参数名 **`Query`**（大写 Q）— 小写全部返回 "query is required"

### Tavily 搜索

| 端点 | 方法 | URL |
|---|---|---|
| Web 搜索 | POST | `https://api.tavily.com/search` |

**认证要求：**
- `Authorization: Bearer <TAVILY_API_KEY>` — 从 `~/.hermes/.env` 读取
- 参数名 `query`（小写）

## Python 调用模板

```python
import time, urllib.request, json, urllib.parse

# ========== 读取 API Keys ==========
def read_keys():
    keys = {}
    with open('/Users/macos/.hermes/.env') as f:
        for line in f:
            line = line.strip()
            if line.startswith('ZHIHU_API_KEY=') or line.startswith('ZHIHU_KEY='):
                keys['zhihu'] = line.split('=', 1)[1].strip()
            if line.startswith('TAVILY_API_KEY='):
                keys['tavily'] = line.split('=', 1)[1].strip()
    return keys

# ========== 知乎搜索 ==========
def zhihu_search(query: str, limit: int = 5, endpoint: str = "zhihu_search") -> list:
    """
    endpoint: "global_search" (全网) 或 "zhihu_search" (站内搜索)
    返回: Items 列表
    """
    keys = read_keys()
    if not keys.get('zhihu'):
        return []
    
    params = urllib.parse.urlencode({
        "Query": query,       # 大写 Q！
        "limit": str(limit),
        "page": "1",
    })
    url = f"https://developer.zhihu.com/api/v1/content/{endpoint}?{params}"
    TS = str(int(time.time()))
    
    req = urllib.request.Request(url, headers={
        "Authorization": f"Bearer {keys['zhihu']}",
        "X-Request-Timestamp": TS,
    })
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            data = json.loads(r.read())
            if data.get("Code") != 0:
                return []
            return data["Data"].get("Items", [])
    except Exception:
        return []

# ========== Tavily 搜索 ==========
def tavily_search(query: str, limit: int = 5) -> list:
    """
    返回: results 列表，每项含 title, url, content
    """
    keys = read_keys()
    if not keys.get('tavily'):
        return []
    
    body = json.dumps({
        "query": query,       # 小写 q
        "max_results": limit,
    }).encode()
    
    req = urllib.request.Request(
        "https://api.tavily.com/search",
        data=body,
        headers={
            "Authorization": f"Bearer {keys['tavily']}",
            "Content-Type": "application/json",
        }
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            data = json.loads(r.read())
            return data.get("results", [])
    except Exception:
        return []

# ========== 合并输出 ==========
def unified_search(query: str, limit: int = 5):
    """双引擎搜索，合并输出"""
    zhihu_items = zhihu_search(query, limit, "zhihu_search")
    tavily_items = tavily_search(query, limit)
    
    print(f"\n## 🔍 搜索「{query}」— 知乎 + Tavily 双引擎\n")
    
    # 知乎结果
    if zhihu_items:
        print(f"\n### 📖 知乎站内（{len(zhihu_items)} 条）\n")
        for i, item in enumerate(zhihu_items, 1):
            ct = item.get("ContentType", "文章") or "文章"
            author = item.get("AuthorName", "佚名")
            votes = item.get("VoteUpCount", 0)
            print(f"**{i}. [{item['Title']}]({item['Url']})**")
            print(f"   作者: {author} | 点赞: {votes} | 类型: {ct}")
            text = item.get("ContentText", "")
            if text:
                print(f"   摘要: {text[:150]}...")
            print()
    
    # Tavily 结果
    if tavily_items:
        print(f"\n### 🌐 Tavily 全网（{len(tavily_items)} 条）\n")
        for i, item in enumerate(tavily_items, 1):
            title = item.get("title", "无标题")
            url = item.get("url", "")
            content = item.get("content", "")
            print(f"**{i}. [{title}]({url})**")
            if content:
                print(f"   摘要: {content[:150]}...")
            print()
    
    # 都失败
    if not zhihu_items and not tavily_items:
        print("❌ 两个搜索引擎都返回空，请检查 API Key 或网络")
```

## 输出格式

```markdown
## 🔍 搜索「Tavily」— 知乎 + Tavily 双引擎

### 📖 知乎站内（5 条）

**1. [「2025 五大热门 MCP 搜索工具深度实测」](https://...)**
   作者: 孟健AI编程 | 点赞: 42 | 类型: Article
   摘要: Exa 有自己训练的模型...

**2. [AI Agent的"搜索大脑"进化史](https://...)**
   作者: sunnyzhao | 点赞: 1 | 类型: Article
   摘要: Tavily的技术架构体现了...

### 🌐 Tavily 全网（5 条）

**1. [Tavily - AI Agent Search API](https://tavily.com)**
   摘要: Tavily is an API for AI agents and LLMs...

**2. [Nebius to acquire Tavily](https://...)**
   摘要: Dutch AI cloud firm Nebius to acquire...
```

## 知乎结果字段

| 字段 | 说明 |
|---|---|
| `Title` | 标题 |
| `ContentText` | 摘要/全文片段 |
| `ContentType` | 内容类型（Article/Question/Answer 等） |
| `ContentID` | 内容 ID |
| `Url` | 原始链接 |
| `AuthorName` | 作者名 |
| `VoteUpCount` | 点赞数 |
| `CommentCount` | 评论数 |
| `AuthorityLevel` | 权威等级 |
| `RankingScore` | 相关度评分 |
| `CommentInfoList` | 评论列表 |

## 已知坑

1. **知乎参数名大小写**：`Query` 必须大写 Q。`query`/`q`/`keyword` 全部返回 "query is required"
2. **时间戳过期**：`X-Request-Timestamp` 5 分钟前失效，必须每次请求重新生成
3. **空 content**：API 可能返回 HTTP 200 但 `ContentText` 为空字符串，跳过即可
4. **Tavily 免费额度**：每月 1000 credits，Basic 搜索消耗 1 credit/次
5. **双引擎超时**：两个 API 并发请求，总超时设为 20 秒（单个 15 秒 + 等待）
6. **热榜接口**：`hot_list` 端点无分页参数，直接 GET 即可

## 参考

- 知乎开放平台文档：`https://developer.zhihu.com/api-docs/business-api/zhihu-search`
- 知乎鉴权说明：`https://developer.zhihu.com/docs?key=authorization`
- 知乎 API 参考文件：`~/.hermes/skills/devops/hermes-provider-config/references/zhihu-api.md`
- Tavily 文档：`https://docs.tavily.com`