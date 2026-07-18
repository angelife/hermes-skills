# Zotero 对接笔记

## 本机现状
- Zotero 已安装：`/Applications/Zotero.app`
- 本地库路径：`/Users/macos/Zotero/zotero.sqlite`
- 附件存储：`/Users/macos/Zotero/storage/`
- Profile：`/Users/macos/Library/Application Support/Zotero/Profiles/cyfct7sr.default/`
- 库正在同步中，条目数持续增长；读取时应先复制一份到 `/tmp/zotero_readonly.sqlite`，避免锁库
- 本次实测导入 207 条书目类条目到 Obsidian

## 可对接字段
优先键：
1. `douban_subject_id`
2. `isbn`
3. `douban_title` + `douban_author`

Zotero 侧可用字段：
- `itemID`、`title`、`creators`（firstName/lastName 拼接）、`ISBN`、`date`、`publisher`
- `abstractNote`、`url`、`libraryCatalog`、`tags`、`dateAdded`、`dateModified`
- 大量条目 `libraryCatalog = Douban`，且 `url` 形如 `https://book.douban.com/subject/XXX/`，可直接提取豆瓣 ID

## 对接流程
1. 复制库：`cp /Users/macos/Zotero/zotero.sqlite /tmp/zotero_readonly_*.sqlite`
2. 读取 `items` + `itemData` + `itemDataValues` + `fields` + `itemTypes` + `itemCreators` + `itemTags` + `collections` + `collectionItems` + `itemNotes`
3. 从 `url` 字段正则提取豆瓣 ID：`https://book.douban.com/subject/(\d+)`
4. 从 `itemTags` + `tags` 读取标签；collection 不要压成 folder，保留为 tag 或 frontmatter arrays
5. 生成 Obsidian 笔记到 `/Users/macos/Documents/Obsidian Vault/Zotero/`
6. 每笔记包含：zotero_itemID, itemType, title, creators[], date, publisher, isbn, url, tags[], collections[], dateAdded, dateModified, source_system

## 实测规模与本机会遇到的现实
- 本机实测：213 items / 32 books / 1457 collections / 40 item types
- collections 在导出的 frontmatter 里保全为数组，不作为文件夹
- `operationalError: database is locked` 是反复验证过的可复现问题，只读副本解决
- 用户主库约 7000-9000 本，常在旧硬盘/旧机/备份中；拿到旧库后增量 import 即可，以 `zotero_itemID` 幂等

## 用户边界与心眼
- 用户明确拒绝“Zotero 唯一真源 + 双向压扁进 Obsidian”方案
- 正确三层：Layer1 Zotero truth → Layer2 Obsidian canonical graph → Layer3 tag/folder view
- 两 guard：ID 强绑定 `zotero_itemID`；Obsidian 只 attach metadata，不 overwrite Zotero fields
- 用户最终诉求是把本地 Obsidian 建成可引用知识资产中心，不是“同步到微信读书”
- NAS 电子书/影音是离线仓库，不是结构化数据源，不纳入主链路
- 没拿到旧硬盘大库前，先承认现实规模，不要空谈架构

## Obsidian 落库结构
```
/Users/macos/Documents/Obsidian Vault/
├── 知识编译/2026/阅读/
│   ├── Reading.md
│   ├── 豆瓣匹配/          ← 66 本 matched
│   ├── 未匹配/            ← 很多
│   └── 数据源/
└── Zotero/                ← 207 本导入
    ├── Zotero Index.md
    └── *.md
```

## 标签策略
- 保留 Zotero 原始标签，去掉 `Douban`
- 额外加 `Zotero` 根标签
- 用户已有标签如 `Topic: 身份认同`、`社会学`、`政治学` 等保留

## 增量导入
- 再次执行时跳过已存在的文件（按 title 去重）
- 若 title 重复，追加 `__zotero{itemID}` 后缀
- 读完 `dateModified` 只导入比上次更新的条目

## 风险点
- 库被 Zotero.app 锁定时，必须复制后读副本
- Zotero 条目类型混合（book/newspaperArticle/encyclopediaArticle/ blogPost 等），导入时按需求 filter
- 旧库条目可能缺 ISBN / abstract，不补，保持原始缺失
- 用户历史中断点：约 9000+ 条项目；直接全量导入 Obsidian 时应保持分批，不一次性并发写
- 用户指出“豆瓣插件当年不理想”，因此不要依赖新增“用旧插件恢复”这类方向；现有 OpenCLI + weread skill 路线更稳
- WeRead API 无 write 接口，不能上架书架；已改走本地 Obsidian 主链路

## 未来导旧硬盘大库时的最小增量策略
- 以 `zotero_itemID` 为唯一幂等键
- 标题重复追加 `__zotero{itemID}`
- 先读后比对，不改原库；显式 multi-pass：Zotero parser → canonical graph builder → Obsidian renderer
