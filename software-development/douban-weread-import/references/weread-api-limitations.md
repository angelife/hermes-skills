# 微信读书 Agent API 接口清单与限制

## 接口总数

微信读书 skill 1.0.4 通过 Agent API Gateway 提供 **17 个接口**，全部为**只读**。

## 完整接口列表

通过 `POST /api/agent/gateway` 发送 `{"api_name": "/_list", "skill_version": "1.0.4"}` 可列出全部可用接口：

```
/review/single          获取单条想法/评论的详情
/book/readreviews       书籍公开点评
/book/bestbookmarks     章节热门划线
/book/underlines        书籍划线列表
/book/recommend         书籍推荐
/book/info              书籍详情
/book/bookmarklist      书签列表
/book/chapterinfo       章节信息
/store/search           搜索书籍
/shelf/sync             获取用户书架列表
/review/list            评论列表
/book/getprogress       阅读进度
/review/list/mine       我的评论列表
/readdata/detail        阅读统计
/user/notebooks         用户笔记本列表
/book/similar           相似书籍推荐
/discover/interact/type3 发现推荐
```

## 关键限制

### 没有写入接口

**[KNOWN, HIGH]** 17 个接口中没有任何"加入书架"、"收藏"、"上架"类写入操作。`/shelf/sync` 只能读取书架列表，不能往书架添加书籍。

这意味着：
- 不能通过 Agent API 自动将豆瓣匹配到的书上架到微信读书
- 如果需要自动上架，必须走另一条路（app 内部 HTTP 请求抓包，不走 Agent API）

### 搜索接口返回结构

`/store/search` 返回的 `results` 数组包含多个分类（如"电子书"、"有声书"），只有 `title == '电子书'` 的分类里才有 `books[].bookInfo`。

### bookId 的重要性

几乎所有书籍相关接口都需要 `bookId`，它只能通过 `/store/search` 获取。没有 ISBN 直查接口。

### deepLink 字段

回包中的 `deepLink` 字段是跳转到微信读书 app 内书籍详情页的链接。如果用户手动点开 deepLink，微信读书 app 会打开书籍详情页，用户可以手动点"加入书架"。这是当前唯一可行的"半自动上架"路径。
