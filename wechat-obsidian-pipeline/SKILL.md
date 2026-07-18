---
name: wechat-obsidian-pipeline
title: "微信→Obsidian 知识流水线 — 备份→精读→评级→迭代"
description: "微信文章全流程：全文备份到 Obsidian（防删）→ 深度精读 → 评级(★1-5) + 分析笔记 → NotebookLM 迭代分析 → LLM Wiki 归并。白天采集，晚上消化。"
version: 1.1.0
author: 土同学
tags: [wechat, obsidian, reading, analysis, notebooklm]
---

# WeChat → Obsidian 知识流水线

## 昼夜分工

| 时段 | 做什么 |
|------|--------|
| **白天** | 采集、提取文章链接、全文备份到 Obsidian |
| **晚上** | 精读、评级、写分析笔记、NotebookLM 迭代分析 |

## Trigger

当需要处理微信群聊/私聊分享的公众号文章时使用。

---

## Phase 0: 连接手机 & 拉取 DB

参见「手机连接」「DB 拉取解密」部分（同原 pipeline）。

## Phase 1: 提取文章链接

从 `message` 表提取 type=49 + mp.weixin.qq.com 消息。

## Phase 2: 全文备份到 Obsidian（防删）

**这是第一优先级操作。** 公众号文章随时可能被删，必须先备份原文。

```bash
# 1. 抓取全文
web_extract(url="https://mp.weixin.qq.com/s/XXXXX")

# 2. 写入 Obsidian，按公众号名分目录
# 路径: ~/Documents/Obsidian Vault/微信公众号文章/<公众号名>/YYYY-MM-DD - <标题>.md
# 写入完整 frontmatter + 全文 Markdown
```

**关键区分：**
- ✅ **全文备份 ≠ 记忆注入**。备份是存原文到 Obsidian（外部资料仓库），不进 Hindsight / MEMORY.md
- ✅ 备份是为了防止微信删文后信息丢失
- ❌ 外部文章链接和数据永远不进个人记忆系统

Obsidian 中的文件结构：
```
微信公众号文章/
  极客之家/
    2026-07-11 - 又一个神级Skill....md     ← 原文全文备份
    2026-07-11 - 又一个神级Skill..._分析笔记.md  ← 分析笔记（见Phase 5）
    attachments/                             ← 图片附件
  GitHubDaily/
    ...
```

## Phase 3: 深度精读（晚上）

逐篇阅读，理解核心内容。关注：
- 核心论点 / 技术方案
- 与现有系统的关联度
- 可落地的改进点
- 引用或交叉链接的其他知识点

## Phase 4: 评级

每篇文章按两个维度打分：

| 评级 | 含义 |
|:----:|------|
| ★★★★★ | 直接相关，能落地，有具体启发 |
| ★★★★☆ | 相关，部分可借鉴 |
| ★★★☆☆ | 好内容，但不直接实用 |
| ★★☆☆☆ | 泛读，仅知识扩展 |
| ★☆☆☆☆ | 不相关 |

## Phase 5: 写分析笔记

在原文同目录下创建 `_分析笔记.md` 文件，包含：

```markdown
---
title: "分析笔记：<文章标题>"
source: "<公众号名>"
analyzed_at: "<日期>"
rating: ★★★★☆
applicability: ★★★☆☆
---

## 核心论点

## 关键概念

## 与我们系统的关联
| 现有系统 | 文章启示 |
|---------|---------|

## 可落地的改进
- [ ] 具体待办事项

## 交叉链接
- → [[关联笔记/概念]]

## NotebookLM 补充分析（4 字段强制）
### 引用源
### 现状对照（已有 / 没有 / 做过类似）
### 是否另起炉灶
### 下一步 1 个动作
### 可复用产物
- [ ] 已写入本笔记 / skill / 配置 / 脚本
```

## Phase 6: NotebookLM 深度分析（架构/设计文默认走；需代理）

**禁止只丢微信 URL。** 用户纠正（2026-07-17）：地址 NLM 认不出，必须喂全文。

```bash
# 1. 用 Phase 2 已备份的 Obsidian 全文（先剥 frontmatter，见 notebooklm-analyze）
# 2. nlm add text <notebook_id> "<正文>" --title "标题" --wait
# 3. 强制 4 字段 query（缺一重问）：
nlm query notebook <id> "只基于本 notebook：
1) 核心洞察+引用源
2) 对照我们系统：已有/没有/做过类似
3) 是否另起炉灶？能复用什么？
4) 下一步唯一推荐动作
禁止泛泛建议。" --timeout 180
# 4. 结果追加到 _分析笔记.md；并至少落 1 个可复用物
#    （笔记 / skill 补丁 / 配置改动 / cron）— 不许看完就关
# 5. 执行前对照本地代码/配置，人拍板后再改系统
```

**顺序铁律：** 备份 →（可先粗读评级）→ **NLM 统一方案（4 字段）** → 落可复用物 → 对照现状 → 人拍板 → 再改系统。

**垃圾水文可不走 NLM：** ★☆☆☆☆ 或不相关 → 一句话点评即可，不喂 NLM。
## Phase 7: 迭代循环

```
多篇分析笔记汇总 → 提炼共识/分歧 → 
再喂给 NotebookLM 做交叉分析 → 
拉回结果 → 更新 Wiki
```

## Phase 8: 群内「类似文章」批量整理 → NLM 交叉（2026-07-17 定型）

用户说「拉取微信群的类似文章全部整理然后推给 nlm」时，走整包闭环，不要只处理单篇。

```
1. 解密微信库（优先已知 key，见 android-wechat-db-decrypt）
2. 扫 type=49 / mp.weixin.qq.com，按群过滤（半神之路等）
3. 关键词精选（NotebookLM / 知识库 / Hermes / Skill / 浏览器 / Agent）
4. 去重 → 全文备份 Obsidian（公众号分目录）
5. 精选 12–20 篇剥 frontmatter → nlm add text（禁止只丢 URL）
6. 交叉 query → 落 技术消化/<主题>/ 清单+分析
7. 若用户要「晚上无人化训练」→ 再问 NLM 出任务单并执行（见 notebooklm-analyze 夜训节）
```

**落库约定：**
- 原文：`微信公众号文章/<公众号>/YYYY-MM-DD - 标题.md`
- 交叉分析/清单：`技术消化/<主题>/YYYY-MM-DD - NLM交叉分析.md`
- 夜训产物：`技术消化/夜训-YYYY-MM-DD/` + `~/.hermes/state/night-training-YYYY-MM-DD/`

**半神之路示例（2026-07-17）：**
- room：`57867408450@chatroom`
- 高相关去重约 107 篇；精选 17 源喂 NLM
- 笔记本：`半神之路-Agent知识库-NLM交叉消化`

## 常用群聊 room ID

| 群聊 | room ID | 人数 |
|------|---------|:----:|
| Light Player 内测交流群 | `43050229556@chatroom` | 200 |
| 🐻🧠 《内驱式学习》读者群 💛 | `45767126259@chatroom` | 179 |
| 半神之路 | `57867408450@chatroom` | 16 |

## Pitfalls

- **Telegram JSON 导出不包含文章 URL（2026-07-16 发现）** — `all_微信搬运工.json` 等频道导出文件只有 `id, date, from, text` 四个字段，无 URL/entity 信息。text 字段仅包含文章标题 + "原文"文字，没有链接。从这类导出中**无法**提取 mp.weixin.qq.com URL。
  - 替代路径：直接通过 Telegram API 访问频道获取带实体的消息，或从微信 DB `message` 表提取 type=49 消息。
  - 如果只有标题没有链接 → 标记"仅标题，无法获取原文"。
- **NLM 只丢 mp.weixin URL 无效（2026-07-17）** — 必须全文 → Obsidian → `nlm add text`；CLI 勿带 `---` frontmatter。
- **外部文章建议整包照改 = 另起炉灶** — NLM 3 步清单也要对照本地（主模型路径、已有 prompt caching、Hindsight）再收敛；方向对 ≠ 全改。
- **只贴聊天不落产物** — Phase 6 后必须至少 1 个可复用物；缺 4 字段（引用/对照/另起炉灶/下一步）重问。
- **为接 NLM 另装 Claude Cowork / notebooklm-py** — 已有 `nlm`，禁止另起炉灶。
- 外部文章不进 Hindsight / MEMORY.md（只进 Obsidian）
- NotebookLM 需要代理才能连 Google（nlm doctor 确认 cookies 有效）
- 分析笔记的评级要诚实，不为了凑数打高分
- 交叉链接用 `→ [[笔记名]]` 格式，保持 Obsidian 双向链接可追溯
- 重复文章：同一主题多篇时，合并分析笔记并链接互相引用
