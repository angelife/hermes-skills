# Obsidian Vault 落库格式

## 目录结构

实际库结构：
- `/Users/macos/Documents/Obsidian Vault/知识编译/2026/阅读/`
  - `Reading.md`：总索引
  - `豆瓣匹配/`：matched 书籍
  - `未匹配/`：微信读书未找到
  - `数据源/`：TSV 副本
  - `obsidian_links.md`：matched 的 Obsidian 链接列表
- `/Users/macos/Documents/Obsidian Vault/Zotero/`：历史 Zotero 导入
  - `Zotero Index.md`
  - 所有 Zotero book 类条目按 title 生成 .md 文件

## 单本书笔记格式

```markdown
---
douban_subject_id: 35434553
douban_title: 书名
douban_author: 作者
douban_pubDate: 出版信息
douban_rating: 
weread_bookId: 
weread_title: 
weread_author: 
weread_rating: 
readingCount: 
status: matched
deepLink: 
best_mark_count: 2
best_mark_preview: 热门划线预览
match_confidence: MEDIUM
query_source: api
last_checked: 2026-07-04T13:24:15+00:00
douban_link: https://book.douban.com/subject/35434553/
tags:
  - 阅读
  - 豆瓣
  - 微信读书已上架
  - 置信度:HIGH
  - 来源:api
  - 微信评分:8.3
  - 划线:5条
---

## 热门划线预览

> 划线文本

## 链接

- [打开微信读书](deepLink)
- [豆瓣页面](douban_link)

## 关联

- [[书名|微信读书]]
- [[外部|豆瓣页面|https://book.douban.com/subject/...]]
```

## 标签规范

- 必带：`阅读`、`豆瓣`
- 已上架：`微信读书已上架`
- 未找到：`微信读书未匹配`
- 置信度：`置信度:HIGH/MEDIUM/LOW`
- 来源：`来源:api/cache/retry/manual`
- 评分：`微信评分:X.X`（weread_rating/100）
- 划线：`划线:N条`（best_mark_count>0 时）
- 译名差异：`译名差异`（weread_title != douban_title）
- 作者：`作者:外文`（非中文字符）

## Reading.md 总索引

包含：统计数字、目录链接、使用说明。每次重建时更新时间戳。