# 交接说明：个人阅读历史多平台对照

## 项目定位

这是一个"稳定性优先"的长期同步任务，不是一次性爬取任务。所有技术选型都围绕稳定性、可恢复性和低打扰展开。

## 目标

把用户多年来在豆瓣标记的书目，与微信读书的公开书目做一次对齐，输出一份个人可查阅的对照表。仅用于个人知识管理与阅读回顾，不涉及商业用途或对外分发。

## 已确认前提

1. 用户豆瓣账号 `Thomas.Xie` 处于登录态，可通过浏览器读取其主页公开书单
2. 用户微信读书 API key 已配置在本地，仅用于读取公开书目信息
3. 已产出首批对照样本 `batch_01.tsv`（旧字段集）和 `batch_02.tsv`（新字段集含 match_confidence），证明映射链路可用

## 数据范围

- 豆瓣侧：8461 本（历史"读过"）
- 每批处理规模：默认 50 本，连续 3 批稳定后可提到 100 本，超时率 <2% 时可提到 200-300 本，任何一批超时率 >=5% 立即降回 50 本
- 最终目标：生成完整 `master.tsv`，保留中间分批结果

## 输出格式

TSV 结构，固定 14+3 列：

```
douban_subject_id
douban_title
douban_author
douban_pubDate
douban_rating
weread_bookId
weread_title
weread_author
weread_rating
readingCount
status                  # matched / not_found / skip_seen / timeout / error
deepLink
best_mark_count
best_mark_preview
match_confidence        # HIGH / MEDIUM / LOW
query_source            # cache / api / retry / manual
last_checked            # ISO 8601
```

注意：`batch_01.tsv` 是历史验证样本，不含后三列；后续批次统一按本规范输出。

## 核心设计

### 1. 状态文件（state.json）

记录当前进度，支持中断恢复。中断后重新执行 `runner_v2.py`，从 `next_index` 继续。

### 2. 缓存（cache.json）

以豆瓣 subject_id 为键，缓存微信读书查询结果。命中且 90 天内直接使用，避免重复请求。

### 3. 批量执行（runner_v2.py）

每批 50 本，逐本查缓存→查API→写TSV→更新state。

### 4. 跳过文件（skip.tsv）

单次查询失败（timeout、接口异常）时写入 skip.tsv，后续可通过 `--retry-skip` 补跑。

### 5. 合并策略

每完成一个批次，立即合并进 master.tsv。按豆瓣ID去重，保留最新批次，升序排序。

### 6. 匹配置信度

- HIGH：ISBN 完全一致，或书名+作者完全一致
- MEDIUM：书名一致，作者部分一致或有译名差异
- LOW：书名相似，作者不同，或需人工确认

## 运行策略

- 默认每批 50 本
- 连续 3 批稳定（超时率 <2%）后提升到 100 本
- 仅在超时率 <2% 且无报错时提升到 200-300 本
- 任何一批超时率 >=5%，立即降回 50 本
- 优先保证断点续跑、缓存命中、去重合并和可恢复性
- 任何优化都不得以提高请求频率为代价

## 关键文件位置

- 项目目录：`/Users/macos/douban_import_batches/`
- 首3批对照结果：`/Users/macos/douban_import_batches/output/batch_0[12].tsv`
- 主 runner：`/Users/macos/douban_import_batches/scripts/runner_v2.py`

## 接手第一步

1. 阅读 `scripts/runner_v2.py`，理解豆瓣翻页 + 微信搜索的固定节奏
2. 检查 `opencli auth status` 中 site=douban 仍为 `logged_in: true`
3. 以 50 本为批次启动 runner_v2.py，观察超时率
4. 连续 3 批超时率 <2%，再评估是否提高批次大小

## 一句话

这是一项以"个人阅读资料整理"为目标的长期对照任务。所有技术选型都围绕稳定性、可恢复性和低打扰展开。
