---
name: douban-weread-import
description: >-
  把豆瓣读书书单、Zotero 阅读库、微信读书公开信息映射为本地 Obsidian 阅读资产。
  最终落库到 Obsidian，保留 TSV 对照表、deepLink 列表和 weread 公开数据接口。
  每批默认 50 本，支持断点续跑（state.json + cache.json）。
  触发词："导豆瓣到 Obsidian"、"建豆瓣书库"、"build douban vault"、"整理豆瓣阅读记录"、
  "建本地书库"、"打通阅读库"、"把 Zotero 导进来"、"打通博客和阅读库"。
version: 0.4.0
pinned: true
---

# 豆瓣读书 → 本地阅读资产 / Obsidian 落库

## 目标

以**本地知识库为主**，把用户多年在豆瓣标记的书目，整理为可持续维护的阅读资产：
- 豆瓣公开书单作为主要书目源
- 微信读书只作为公开信息补充接口，不是最终落库平台
- 最终交付物：
  - Obsidian vault 里的分层笔记（已匹配 / 未匹配 / Reading.md 总索引）
  - 原始 TSV 对照表
  - deepLink 列表（便于半自动跳转查看）
- 不保存任何账号信息

## 架构决策：合流系统，不是单向投影

用户明确否定了“以 Zotero 为唯一真源、双向压扁进 Obsidian”的做法，因为那样会在两处产生结构性损失：
1. Zotero collections（1457 个）是多归属 DAG，压入 Obsidian folders 会爆炸式碎裂
2. 多作者有序信息、itemType、notes 被压平
3. Obsidian 若有独立知识节点，会退化成不可逆同步问题
4. Douban / WeRead 有独立主权数据，反向污染 Zotero 主键会产生幽灵重复

正确架构是三层模型：
- Layer 1（Truth）：Zotero 本地库不动，作为 truth layer
- Layer 2（Graph）：Obsidian 里的前置语义层，保留 zotero_itemID、itemType、creators[]、collections[]、isbn/douban_subject_id/weread_bookId
- Layer 3（View）：Obsidian folder + tag 只做导航/查询投影

对应的两层 guard：
- Guard A：ID 强绑定，zotero_itemID 唯一，不允许 title-only merge
- Guard B：反向写禁止，Obsidian 只 attach metadata，不 overwrite Zotero fields

collection 映射策略：folder = source/type（阅读/未匹配/Zotero），collection 全部以 tag 形式保留，不进入文件夹结构。

## 重要边界：本地优先，平台次之

- 微信读书 Agent API 没有“加入书架”写入接口，只适合做读取层辅助
- 不要把“能否上架微信读书”当成项目成败标准
- 核心判断标准：**数据有没有沉淀在你的本地 Obsidian 库里**
- 远期目标不是“导进微信读书”，而是**让豆瓣、微信读书、Zotero、博客、笔记都在本地形成可互相引用的阅读资产**
- 每次新增数据源，优先补到本地库，而不是反过来把本地库导去平台

## 豆瓣 collect 分页的真实边界（已实测修正）

- `start=1245` **不是** 404 边界；实际 curl/CLI 验证：HTTP 200，页面有 `.subject-item`
- 真实可抓区间的实测结论：`next_index≈2190` / `seen≈1666` 后命中率收敛到近 0
- 但 `start≈1395+` 后已出现**大量空页**；这不是脚本问题，是账号公开列表的访问限制/反爬衰减
- 正确停止条件（按重要性排序）：
  1. 同一 `start` 页面 HTTP 200 但解析到 **0 条 `.subject-item`**，且连续 3 个 `start` 均如此
  2. 连续 **2 个完整批次** matched=0，且批次内大量 `not_found` + dt≈0.1s（说明命中率收敛）
  3. 连续出现真正的 `HTTP 404`，且对同一 URL 重试 2 次仍 404
- **注意**：不要看到单页 404 就停；要用“连续 3 空页 / 连续 2 批 0 matched”双条件才判定边界
- 若条件 1/2 满足而条件 3 未满足，说明账号还有书但已被软限流；应暂停 30-60 分钟再继续，而不是立即停

## 禁止繁衍续跑文件

- 中断后必须**追加回原批次 TSV**，而不是新建 `batch_09_continuing`
- 只有批次本来就结束后，才开 `batch_10`
- 碎片化续跑文件会破坏 `master.tsv` 去重、混淆 `finished_batches`

## 判断“没数据” vs “被反爬” 的两步法

1. 先看页面是否真解析不到 `.subject-item`
2. 再看同一页是不是连续大量 `not_found` + matched=0
3. 满足“连续多页无新 subject_id 且 matched 连续为 0”才认定接口命中率收敛，可停
4. 不要被后台早退日志吓到；只要 `state.next_index` 和 TSV 在推进，就不算阻塞

## 豆瓣反爬应对节奏（用户明确反馈后修正）

用户反馈：密度太高像机器人，后台虽未显式报 403/404，但命中率骤降。

- 默认节奏：**2-4s 随机延迟**，每 50 本停 **30-60s**
- 连续出现 `not_found`、命中率连续不佳：直接暂停比加密度更有效
- 不要让同构搜索无限空转；命中率收敛时改策略，不要硬扛
- 若怀疑被软限流：停 30-60 分钟再继续，而不是调小间隔

## 后台 runner 稳定性铁律

- macOS 上必看到 `can't change option: monitor` / `gitstatus failed` 噪声
- 这个噪声**不代表脚本坏了**，只看 TSV 是否增长、state 是否推进
- 脚本永远是 cattle 模式，自动续跑优先于重新发明新脚本

## state.json 脏状态处理

```python
import json
from pathlib import Path
state = json.loads(Path('/Users/macos/douban_import_batches/state.json').read_text(encoding='utf-8'))
state['finished_batches'] = sorted(set(state.get('finished_batches', [])))
state['next_index'] = max(int(state.get('next_index', 0)), 2190)
```

## 用户偏好

- 用户原话：**“一直抓完就完事了。只要它不提示什么问题，你就一直抓。”**
- 真实的“有问题”只有：TSV 停止增长、state 停止推进、匹配率收敛到连续 0、页面空转
- 在这些条件满足之前，不主动停下，也不重复询问

## Zotero 完整库提取

- 这台 Mac 上的 Zotero **不是残库**：215 items、215 keys、全部有 dateAdded
- 可以用 `Zotero/complete/` 目录一次落盘，保留所有原始字段
- 以后旧硬盘大库回来后，增量 merge，不改现有 canonical notes

## 执行模式：cattle，不死保 + 连续跑模式

后台长跑在这台 Mac 上**不稳定**。`opencli` 子进程可能看到 stderr 噪声就早退。

正确姿势：
- 用 `terminal(background=True, notify_on_complete=True)` 跑，但预期它可能中途退出
- 挂了就重跑：state.json 记录进度，cache.json 缓存已查结果，自动跳过已处理的 subject_id
- 期望值设为“**会死，但随时可重启**”

**用户明确偏好**：用户说过“中间不要再停下来了，一直抓完就完事了。只要它不提示什么问题，你就一直抓。”
- 这并不意味着无限盲跑。**“不提示问题”的判定标准**：
  1. state.json 在推进
  2. TSV 在增长
  3. 没有连续大批 timeout/error/404
- 若连续 50 本全部 `not_found` 或出现结构性 404，必须停下来报告，而不是继续盲跑
- 若只是 macOS 早退，立即重启，不重复处理

## 适配：miss rate 漂移收敛规则 + 数据边界判断

实测经验：
- 前 5 批：match 率 20-30%
- 6 批之后：常掉到 0-3%
- 这不是脚本故障，是接口命中率本身衰减

执行规则：
- 先连续跑 2-3 批。如果新 matched 连续为 0 或 ≤3，停止同构搜索
- 此时有两种替代策略：
  1. 优先用 ISBN 搜索 weread，可能重新激活命中率
  2. 先做 consolidation：把现有数据归档做静态高质量对照视图，后续再重启
- 不要为了“抓完”而浪费超 100 本全是 0 命中的批次数

**豆瓣 collect 分页的实际数据边界**：
- 账号 `Thomas.Xie` 的公开“读过”列表，在 `start≈1245` 之后返回空页或 404，不是脚本问题
- 单页探测：`curl 'https://book.douban.com/people/{profile}/collect?start=1245&sort=time&rating=all&filter=all&mode=grid'` 若返回 200 但解析不到 `.item/.subject-item`，说明已到底
- 不要继续盲跑空页；应切换策略或通知用户当前看到的就是实际可爬边界

## state.json 脏状态修复命令

```python
import json
from pathlib import Path
state = json.loads(Path('state.json').read_text())
state['finished_batches'] = sorted(set(state.get('finished_batches', [])))
state['next_index'] = max(state['next_index'], sum(1 for p in Path('output').glob('batch_*.tsv')) * 50)
```

续跑前先跑一遍，清除重复批次条目、calibrate next_index。

## 三账合一：已拥有 / 已读过 / 想读

用户最终要的不是“平台导来导去”，而是把三本账**合并进同一个 Zotero book note**：

- **已拥有**：来自 NAS 离线电子书库。可用文件名解析出标题/作者/格式/路径，建立 Obsidian 书单。优先级最低，只证明“我有这本书”。
- **已读过**：来自豆瓣“读过”标记。提供时间线、评分、标签、简短评论。优先级最高，直接 enrichment 到对应 Zotero book note。
- **想读**：来自豆瓣“想读”标记。作为待办书单，可随时转“已读过”。

合并规则：
1. 以 Zotero `zotero_itemID` 为主键
2. 豆瓣通过 `ISBN > douban_subject_id > title+author` 挂到 Zotero book
3. NAS 电子书通过 `ISBN > title+author` 挂到 Zotero book
4. 三者共存同一 frontmatter，字段不打架：`douban_*`、`weread_*`、`nas_*`

对应 Obsidian 视图：
- `知识编译/2026/阅读/` - 豆瓣映射主目录
- `知识编译/2026/阅读/NAS书单/` - 已拥有书单（Dataview 可查）
- `知识编译/2026/阅读/阅读总库/` - 三账合一眼图，按 status 标签分组

## 交付物：TSV + Obsidian 库 + deepLink 列表 + 三账索引

1. TSV：`/Users/macos/douban_import_batches/output/batch_NN.tsv`
2. Obsidian 库：`/Users/macos/Documents/Obsidian Vault/知识编译/2026/阅读/` 下的：
   - `Reading.md`：总索引
   - `豆瓣匹配/`：已上架/可打开微信读书的书籍笔记
   - `未匹配/`：微信读书未找到的书籍笔记
   - `数据源/`：原始 TSV 副本
3. 链接列表：`output/obsidian_links.md`
4. 状态与缓存：`state.json`、`cache.json`
5. Obsidian 单笔记内容必须包含：豆瓣链接、微信读书 link、简介、分类、出版社、ISBN、置信度、来源、划线数、评分标签。不要只保留书名。

## 阶段化交付建议

优先把当前批次落进 Obsidian，而不是追求继续扩大数量：

```
batch_02 完成
    ↓
生成 batch_02_links.txt
    ↓
生成/更新 Obsidian 笔记
    ↓
交付给用户查看
    ↓
继续 batch_03
```

遇到用户说“先不导了，我想整理 Obsidian”时，立刻切到 Obsidian 落库/优化，不要继续追批次。

## 重要边界：微信读书 Agent API 没有"加入书架"接口

[KNOWN, HIGH] 微信读书 skill 1.0.4 的 17 个接口全部是**只读**的：
- `/shelf/sync` 只能读书架列表，不能写入
- 没有 `/shelf/add`、`/book/favorite` 或任何上架接口
- 用 `api_name: /_list` 可以列出全部可用接口

所以这个项目**只能做映射对照**，不能把匹配到的书自动上架到微信读书。
如果用户要上架，两条路：
1. 用 TSV 里的 `deepLink` 字段生成链接列表，手动逐个点开（半自动上架）
2. 抓包分析微信读书 app 的内部 HTTP 请求，不走 Agent API（需要用户配合）

**不要对用户说"已同步到微信读书"**，只能说"已生成对照表"。

## 前置检查

```bash
opencli auth status | grep -A1 "site: douban"
grep '^wrk-' /Users/macos/key.txt
```

- douban 必须 `logged_in: true`
- key 必须存在且以 `wrk-` 开头

## 执行模式：cattle，不死保

后台长跑在这台 Mac 上**不稳定**。`opencli` 子进程会看到 stderr 里 zsh/gitstatus 初始化噪声就早退。

**正确姿势**：
- 用 `terminal(background=True, notify_on_complete=True)` 跑，但期望它可能中途退出
- 若跑挂了，直接重新执行 `runner_v2.py`：state.json 记录进度，cache.json 缓存已查结果，会自动跳过已处理的 subject_id
- 期望值设为“**会死，但随时可重启**”

**用户偏好**：用户明确要求“一直抓完就完事了”。所以：
- 不要一遇到早退就问“继续吗”
- 自动校验 state.json 后立即按原策略继续
- 只有碰到结构性阻塞，或豆瓣页面持续 404 / 全 not_found，才明确报告并建议切换策略

## 节奏约定

用户原话："**能导多少导多少，不着急，慢点**"。

**实测节奏**（batch_02 真实数据）：
- 每本书 0.1-1.3 秒（比预估快很多）
- 50 本约 4-5 分钟
- 零超时，微信读书接口表现稳定
- 8461 本全量约 170 批 × 5 分钟 ≈ 14 小时纯运行
- 实际分批跑，按"有空就跑一批"模式，大概 2-3 周

**启动前对用户说的话**：
> 开始批 XX，预计约 Y 分钟，产出文件 output/batch_XX.tsv

## 项目目录结构

```
/Users/macos/douban_import_batches/
├── HANDOFF.md                  # 完整交接文档
├── state.json                  # 运行状态（断点续跑）
├── cache.json                  # 微信读书查询缓存
├── output/
│   ├── batch_01.tsv            # 历史验证样本（旧字段，无 match_confidence）
│   ├── batch_02.tsv            # 新字段集样本
│   └── master.tsv              # 最终合并结果
├── scripts/
│   ├── runner_v2.py            # 主 runner（带 state + cache）
│   ├── pacing_test.py          # 早期验证模板
│   └── batch_01_run.py         # 首批 runner
├── logs/
│   └── batch_XX.log
└── fetch.log
```

## 核心 runner（scripts/runner_v2.py）

见 `scripts/runner_v2.py`。它负责：
1. 读取 `state.json` 获取 `next_index`
2. 从豆瓣 `/people/{PROFILE}/collect?start={next_index}` 翻页
3. 对每本书：
   - 查 `cache.json`，命中且 90 天内直接用缓存
   - 未命中则调微信读书 `/store/search`
   - 调 `/book/bestbookmarks` 取热门划线前 5 条
   - 计算 `match_confidence`（HIGH/MEDIUM/LOW）
   - 写入当前批次 TSV
4. 每处理完 50 本（默认）更新 state.json
5. 批次结束后更新 cache.json

## TSV schema（v2 字段集）

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
status                 # matched / not_found / skip_seen / timeout / error
deepLink
best_mark_count
best_mark_preview
match_confidence        # HIGH / MEDIUM / LOW
query_source           # cache / api / retry / manual
last_checked           # ISO 8601
```

**注意**：`batch_01.tsv` 是历史验证样本，不含最后三列；`batch_02.tsv` 起统一按新规范输出。

## state.json 结构

```json
{
    "next_index": 105,
    "current_batch": 3,
    "finished_batches": [2],
    "total_seen": 101,
    "total_matched": 30,
    "last_run_ts": 1783171722
}
```

中断后重新执行 `runner_v2.py`，从 `next_index` 继续。

## 续跑与状态校验

- 若同一批次被中断，不要把续跑写进新 TSV；优先以追加方式写回同批次文件
- 禁止繁衍出 `batch_09_continuing` 这种碎片；合成/master 阶段会重复或漏行
- 续跑前先校验 `state.json`：`total_seen` 应该与现存 `batch_*.tsv` 行数一致，`finished_batches` 不应有重复批次
- 若 `state.json` 已脏，先人工修复到与 TSV 一致，再继续

## 豆瓣分页实测发现（2026-07-05）

- `start=1245` **不是**脚本边界；curl/opencli 实测：HTTP 200，存在 `.subject-item`
- 误判为空页/404，常见原因：
  1. macOS/Hermes 子进程提前退出，把未返回页面的结果当成空
  2. `opencli browser eval` 的返回有长度截断/噪声
- 真正边界判定：连续 **3 个 start 都解析不到 `disqus_thread/载入”`须切换策略或报告当前可抓边界
- 若页面能 open、但元数据不完整：优先用 OpenCLI 浏览器态解析，少用纯 requests
- 软限流信号：命中率骤降 + 大量无意义跳页，而不是 404
- 每 5 批左右做一次全量校验：`batch_*.tsv` 总行数 + `master.tsv` 去重数 + `state.total_seen`

## cache.json 结构

以豆瓣 subject_id 为键，缓存微信读书查询结果，避免重复请求。

```json
{
    "35434553": {
        "weread_bookId": "3300084674",
        "weread_title": "惊呆了！原来这就是社会学",
        "weread_rating": 830,
        "match_confidence": "HIGH",
        "last_checked": "2026-07-04T20:32:18+00:00"
    }
}
```

缓存策略：命中且 `last_checked` 在 90 天内直接使用，否则重新请求并回写。

## 运行方式

```bash
python3 /Users/macos/douban_import_batches/scripts/runner_v2.py > /Users/macos/douban_import_batches/logs/batch_XX.log 2>&1
```

用 `terminal(background=True, notify_on_complete=True)` 跑。不要用 `&` / `nohup` / `disown`。

## 批次运行策略（稳定性优先）

- 默认每批 50 本
- 连续 3 批稳定（超时率 <2%）后提升到 100 本
- 仅在超时率 <2% 且无报错时提升到 200-300 本
- 任何一批超时率 >=5%，立即降回 50 本
- 任何优化都不得以提高请求频率为代价

## 合并策略

每完成一个批次，立即合并进 `master.tsv`：
1. 读取所有 `batch_*.tsv`
2. 以 `douban_subject_id` 为主键去重
3. 若同一 ID 出现在多个批次，保留最新批次的数据
4. 按 `douban_subject_id` 升序排序
5. 重写 `master.tsv`

## 交接文档

完整交接说明在 `/Users/macos/douban_import_batches/HANDOFF.md`，可直接给别的 AI 或开发者接手。

## 已知限制

1. 豆瓣 8461 本全量无法一次性稳定跑完，必须分批
2. 批量加入书架：微信读书 Agent API **没有写入接口**，只能做映射对照，不能自动上架
3. `/readdata/detail` 返回 499，是参数问题，不是版本问题
4. 微信读书未上架书籍只标 `not_found`，不补盗版资源
5. 豆瓣依赖 OpenCLI 浏览器登录态；若 Chrome 退出登录需重新绑定
6. macOS 上长跑脚本可能早退，按 cattle 模式处理：挂了再跑
7. 豆瓣列表页通常拿不到精确评分，若需要评分，需额外逐本抓详情页；当前 `douban_rating` 多为空
8. 微信读书公开接口当前未返回书籍分类/tag 字段，暂时用评分/划线/置信度标签代替
9. 豆瓣页面标签未作为独立字段导入，避免逐个详情页开销；后续可选补充
10. NAS 旧书库通常是 Calibre 结构（`.sdr` + `metadata.db`），不是 Zotero；若 `metadata.db` 可读，可直接重建书目索引
11. Zotero 可从 `items` + `itemData` + `itemDataValues` + `itemCreators` + `tags` + `collections` 直接读取结构化书目
12. WEREAD_API_KEY：`/Users/macos/key.txt` 里以 `wrk-` 开头的那一行；长度 28
13. 后端被动早退 + stderr 噪声（zsh/gitstatus）经常同时出现；若 log 里出现了 `can't change option: monitor` 或 `gitstatus failed`，不代表脚本逻辑失败，只看 TSV 输出和 state.json 是否推进
14. Zotero 场景下：读取时先 `cp` 原库到 `/tmp/...sqlite`，否则 `OperationalError: database is locked`。这是反复验证过的可复现修复模式
15. Zotero→Obsidian canonical export 的最小必要字段：`zotero_itemID, title, creators, date, publisher, ISBN, url, libraryCatalog, itemType, tags, collections, dateAdded, dateModified, source_system`
16. Obsidian note 文件名去重规则：若同名 note 已存在，追加 `__zotero{itemID}`
17. Zotero 的 `collections` 不要再降维成 folder；folder = source/type，collection = tags/parent/child metadata
18. 项目语义目标是“知识资产库”，不是“阅读记录清单”；所有字段设计优先支持后续语义查询和 Dataview
19. 豆瓣移动端列表页 `m.douban.com/people/{profile}/collect?start={n}` 在部分分页后返回 404；当前 runner 的 title 解析只取第一个命中，返回的是整页首条书名，不是逐条，需要修正解析逻辑，或优先使用 OpenCLI 浏览器登录态取桌面页
20. 连续后台中断后 `state.json` 会出现脏状态：`finished_batches` 含重复批次、`next_index` 未推进；续跑前务必人工校验
21. 追加续跑时，优先将输出追加回**同一批次 TSV**，而不是繁衍出 batch_09 / batch_09_continuing / batch_10 多重碎片；碎片化后合成 `master.tsv` 时会重复或漏行
22. U-NAS/蜗牛星际 SMB 可挂载，但部分目录可能无读权限；先列顶层再定向找 `metadata.db` / `zotero.sqlite`，不要盲搜整机

## 三库索引页（可交付最小闭环）

在 Obsidian 里做一个**一站总索引入口**，让字段级连通真正可被用户感知，不只是理论上的链接。

推荐放：
- `/Users/macos/Documents/Obsidian Vault/知识编译/2026/阅读/Reading.md`
- 内容至少含 3 个 Dataview 查询：
  - Zotero canonical notes
  - 豆瓣映射全部条目
  - 微信读书已匹配条目
- 每本书通过 `isbn`、`douban_link`、`deepLink` 省略号级联到两端
- 这样用户一开索引页就能确认“这三库是连着的”，不需要看几百条笔记

## 边界修正：离线资产不是结构化数据源

- NAS 上的电子书、电影、课程、`.sdr`、`metadata.db` 都属于**离线资产仓库**
- 它们有“藏书/观影时间戳”价值，但**不要把它们升格为结构化数据源并入主链路**
- 只有在这些资产里找回 `zotero.sqlite`、`Calibre metadata.db`、豆瓣原始 JSON 时，才值得做一次结构性导入
- 项目主心骨始终是：**豆瓣（索引）→ Zotero（正规数据库）→ Obsidian（工作层）→ 微信读书（读取补充）**

## 现实兜底：找不到旧硬盘大库，系统仍继续生长

用户可能有 7000-9000 本的旧 Zotero 大库，但如果旧笔记本硬盘找不到，不要反复搜 NAS/磁盘探测。

正确姿态：
1. 承认当前库规模就是“骨架版”，不是“全量版”
2. 继续铺豆瓣 batch，继续完善 Obsidian 索引页
3. 旧硬盘以后找回来，再做一次增量 merge
4. 任何并发任务不要让主链路悬空等待

## 三库连接键优先级

按这个顺序做 match，避免 title-only 幽灵重复：
1. `ISBN`
2. `douban_subject_id`（从 Zotero url 提取）
3. `title + douban_author`（兜底）
4. 微信读书 `weread_bookId` 只挂到 Zotero/book note 上，不做主子项

## 闭环标准（以后接手的容易验收）

验收三库真正打通时，检查：
- Zotero note 里有 `douban_link` 和 `deepLink`
- Obsidian Dataview 能同时看到 `zotero_itemID` 和 `weread_bookId`
- 字段不在不同页面里平行生长，而是同一 frontmatter 下共存
- 旧硬盘大库回来后，增量 merge 不重复、不覆盖、只补新增

## 交付标准（修订版）

最终交付物不是“导完多少本”，而是：
- 用户在 Obsidian 里能看到一条书同时连着 Zotero、豆瓣、微信读书
- 旧硬盘回来后能增量 merge 而不破坏现有数据
- 索引页随时可用，不需要再看 200 个单独的 TSV

## Wineyard / Disaster Recovery Notes

1. Zotero 场景下：读取时先 `cp` 原库到 `/tmp/...sqlite`，否则 `OperationalError: database locked`。这是反复验证过的可复现修复模式
2. NAS 扫描不要盲搜整棵 `find`；先列顶层目录，再定向找 `metadata.db` / `zotero.sqlite`
3. U-NAS/蜗牛星际 SMB 共享可挂载，但部分目录可能无读权限；优先走 Web 管理界面或调整 SMB 权限
4. 旧库不在 NAS 上时，不要无限探测；承认当前库规模是“骨架版”，继续铺数据，找到后增量 merge

## Obsidian 三库索引（Working成品）

实际已在 Obsidian 落地的三库索引：
- `阅读/Reading.md`：总索引 + 豆瓣映射 Dataview
- `阅读/三库对照.md`：Zotero + 豆瓣 + 微信读书 + NAS 一览
- `Zotero/Canonical Graph.md`：Zotero 主库 Dataview，按 itemType 分组

三库连接键优先级：
1. ISBN
2. douban_subject_id
3. title + author
4. weread_bookId 仅作为 enrichment 挂载字段

## 用户偏好（铁律）

- 说人话，不要技术腔过度。被纠正后立刻切换极简执行语体
- 不要二选一提问，不要重复给选项表。用户要的是"你说我做"
- 不要停在解释层。先跑出样子，做完再看怎么改
- 速度优先稳，优先人工可恢复
- 没拿到旧硬盘大库时，现实是什么就交付什么，不要空谈架构

## 角色与心眼

- 用户始终是阅读资产的唯一主人。你做的是"本地采集+索引"，不是迁移去第三方
- 主心骨在用户本地：豆瓣是索引，Zotero 是正规数据库，Obsidian 是工作层
- NAS/电子书/影音只是离线仓库，不是结构化数据源，不纳入主链路
- 未拿到旧硬盘大库之前，先承认现实规模，再交付当前成果
- 用户的最终问题不是“同步到微信读书”，而是让本地 Obsidian 成为可引用的知识资产中心
