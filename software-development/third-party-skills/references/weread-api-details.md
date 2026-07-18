# 微信读书 (WeRead) API 详情

基于 2026-06-20 的集成测试结果。

## 入口

```
POST https://i.weread.qq.com/api/agent/gateway
```

## 认证

- Header: `Authorization: Bearer $WEREAD_API_KEY`
- 环境变量: `WEREAD_API_KEY=wrk-xxxxxxxx` 格式
- 配置位置: `~/.hermes/.env`

## 请求规范

```json
{
  "api_name": "/store/search",
  "keyword": "三体",
  "count": 3,
  "skill_version": "1.0.3"
}
```

**关键规则：**
- `skill_version` 必须传，值取 SKILL.md 顶部的 `version` 字段
- 所有业务参数**必须平铺在 body 顶层**，不能套在 `params` 里
- `/shelf/sync` 统计书架条数公式：`books.length + albums.length + (mp 非空 ? 1 : 0)`

## 已确认可用的接口

| api_name | 用途 |
|----------|------|
| `/store/search` | 搜索书籍/作者/书单/听书/公众号 |
| `/shelf/sync` | 用户书架（含听书/讲书） |
| `/book/info` | 书籍基本信息 |
| `/book/chapterinfo` | 章节目录 |
| `/book/bookmarklist` | 用户在某本书的划线 |
| `/book/bestbookmarks` | 热门划线（含文本+人数） |
| `/book/underlines` | 章节划线热度统计（不含文本） |
| `/book/recommend` | 个性化推荐 |
| `/book/similar` | 相似推荐 |
| `/book/getprogress` | 阅读进度 |
| `/book/readreviews` | 章节划线下想法列表 |
| `/review/list` | 书籍公开点评 |
| `/review/list/mine` | 用户个人想法/笔记 |
| `/review/single` | 单条想法详情 |
| `/readdata/detail` | 阅读统计（周/月/年/总） |
| `/user/notebooks` | 有笔记的书籍列表 |
| `/discover/interact/type3` | 发现页朋友在读 |
| `/_list` | 查看所有可用接口 |

## 测试验证结果（2026-06-20）

- ✅ `/store/search` — 搜索"三体"返回三体全集(评分930)、三体1(878)、三体2·黑暗森林(933)
- ✅ `/shelf/sync` — 用户书架正常，含"文章收藏"和《神雕侠侣》有声书
- ✅ `/_list` — 返回完整 17 个接口列表及参数定义
