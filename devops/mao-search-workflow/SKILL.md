---
name: mao-search-workflow
title: MoA 多智能体问题搜索与整合技能（v2 — 五改落地版）
description: 通用 MoA 问题搜索与方案整合工作流。任何技术问题走标准流程：前提锁定 → 搜索 → 交叉验证 → 整合输出。内置搜索引擎插件架构，支持零代码扩展。
tags: [moa, multi-agent, search, troubleshooting, knowledge-aggregation]
category: devops
---

## Entry Gate

**╔══════════════════════════════════════════════════════╗**
**║  GATE: Before ANY search tool call, load this skill  ║**
**║  with skill_view() first. This is NOT optional.      ║**
**║                                                      ║**
**║  THEN: Before searching, ASK YOURSELF:               ║**
**║  "Does this tool have a manual / README / Wiki       ║**
**║   that I should read FIRST?"                         ║**
**║  If yes → read the manual/page (web_extract/read)    ║**
**║  If stuck → proceed with the search workflow below.  ║**
**╚══════════════════════════════════════════════════════╝**

## 问题解决四层漏斗（用户指令）

**问题出现时，按此顺序层层推进，不可跳层：**

```
第1层：读说明书/README/Wiki
  → 该工具是否有官方文档？先通读相关章节
  → 读完了还不行？

第2层：搜别人现成经验
  → GitHub Issues / 论坛 / 博客
  → 关键词搜错误信息 + 方案
  → 还不行？

第3层：自己动手试
  → 基于前两层的理解，谨慎尝试
  → 两次失败就停，不要死磕

第4层：问 AI（ChatGPT / Claude）
  → 总结问题（环境+精确日志+已尝试+编号）
  → 通过 OpenBridge 同时问多个 AI
```

**⚠️ 每一层都是阀门，不是加速带。**
- 不要跳过第 1 层直接进第 2 层 — 很多问题读说明书就能解决
- 用户说：**"绝大多数问题，其实你看说明书就能够解决的"**
- 用户说：**"你之前为什么每次配置啥都失败？就是你事前的调查都没有做好"**
- 用户说：**"遇到问题，不要自己去尝试，大量的去试错，而是要看有没有别人现成的经验，这样可以节省 Token"**

## 漏斗触发场景

当以下场景出现时，必须从第 1 层开始（而非跳进第 2 层搜解决方案）：
- 首次使用某工具/软件
- 某工具报错但我不熟悉它的配置方式
- 要修改/调试我从未读过文档的系统配置

Concrete failure from a recent session:
- **User asked about KOReorder Mosaic mode on KPW10 Kindle** → I answered "yes it has that" from general KOReorder knowledge → actually only Kobo version has Mosaic à Kindle doesn't. If I had loaded this skill first, the Device-specific pitfall would have stopped me.
- **User asked me to search battery gas gauge recovery** → I made 4 web_search calls ad-hoc without loading this skill → user had to remind me "我之前不是做过搜索技能么" and I had to redo the whole search properly.

**Hard enforcement:**
- "It's just a simple question" is NOT a reason to skip this skill.
- "I know the answer" is NOT a reason to skip this skill.
- "The user is testing me" is NOT a reason to skip this skill.
- If the question touches version-specific behavior, vendor policy, config schemas, platform differences, or feature support boundaries → load this skill FIRST, then answer from verified sources.

**Trigger:** The moment the user asks ANY question needing external info (or a cross-platform feature claim), load this skill FIRST. Before web_search. Before web_extract. Before stating a feature exists on a user's specific hardware.

## Pitfalls

### Default activation failure
**Do NOT** use ad-hoc web_search / web_extract calls when this skill exists. If the question needs external information, the workflow is: `skill_view('mao-search-workflow') → premise locking → engine selection → search → cross-verify → structured output`. Skipping to ad-hoc search means you lose premise locking, engine selection, and structured output — all of which the user relies on.

**Concrete failures from this session:**
1. User asked to search battery gas gauge recovery → made 4 ad-hoc web_search calls, wrote a scattered summary, THEN user said "我之前不是做过搜索技能么" → had to redo the whole search using the proper workflow.
2. User asked about KOReorder Mosaic mode on KPW10 → answered "yes it has that" without searching → actually only Kobo has it, Kindle doesn't.
3. User asked about CLI vs GUI model-validation differences for Claude Desktop → answered from general knowledge without loading this skill → user corrected with "你让你用 我们之前做好的 搜索 skill".

The user has explicitly flagged all three failures. If you catch yourself reaching for a bare web_search call, stop and load this skill first.

### Local-CLI success ≠ browser/extension pipeline available
When diagnosing "why does this work in terminal but fail in managed/sandboxed execution?", do **not** conclude from a single successful CLI-only probe that the full localhost or browser-extension chain is also reachable. Common incorrect leaps:
- `opencli status` works ⇒ `opencli weixin download` must also work.
- A background job succeeded on the host shell ⇒ the same job path is available inside a sandbox/code-execution runtime.

These confuse **host runtime** with **sandboxed runtime**, and **CLI layer** with **browser-extension layer**. Treat them as separate execution domains. If the failure only appears in browser/extension-dependent paths, must verify whether the cause is: network/localhost restriction, runtime timeout/cutoff, or true architecture boundary. Do not declare any of these until you have observed the bridge/daemon/extension trace from inside that exact runtime.

### Comparison questions that look easy but aren't
"CLI vs GUI", "Desktop vs Code", "App A vs App B" questions often depend on:
- Specific version behavior changes
- Vendor policy shifts
- Config schema validation at the client layer
- Platform-specific restrictions that differ from general documentation

These MUST go through this skill even if the answer seems obvious from general knowledge. General knowledge answers to comparison questions are frequently stale, oversimplified, or wrong for the specific version/environment in question.

## Purpose

为**任何技术问题**提供标准化的搜索、分析、整合、输出流程。通过多引擎并行获取信息，多智能体交叉验证后输出最优方案。

## Triggers

- **ANY technical question that requires external information. Load this skill BEFORE making any search tool calls. This is the DEFAULT search flow — not a fallback for when ad-hoc search fails.**
- 遇到技术问题需要系统性搜索解决方案
- 单一搜索结果不够充分，需要多源交叉验证
- 需要综合多个来源的碎片信息形成完整方案
- 复杂问题需要拆解为多个子问题并行处理
- 用户对之前找的方案不满意，需要更全面分析

## Pitfalls

### Default activation failure
**Do NOT** use ad-hoc web_search / web_extract calls when this skill exists. If the question needs external information, the workflow is: `skill_view('mao-search-workflow') → premise locking → engine selection → search → cross-verify → structured output`. Skipping to ad-hoc search means you lose premise locking, engine selection, and structured output — all of which the user relies on.

**Concrete failures from this session:**
1. User asked to search battery gas gauge recovery → made 4 ad-hoc web_search calls, wrote a scattered summary, THEN user said "我之前不是做过搜索技能么" → had to redo the whole search using the proper workflow (premise locking → engine selection → structured output → reference file)
2. User asked about KOReorder Mosaic mode on KPW10 → answered "yes it has that" without searching → actually only Kobo has it, Kindle doesn't

The user has explicitly flagged both failures. If you catch yourself reaching for a bare web_search call, stop and load this skill first.

### Device-specific features — do not state from general knowledge
Do NOT say "software X has feature Y" based on general knowledge of that software without verifying that the feature exists on the user's specific hardware platform. KOReorder ≠ same features on Kindle vs Kobo; TWRP ≠ same support across devices; fastboot commands ≠ available on every OEM. The most common failure pattern: making a claim about a cross-platform tool based on experience with one platform, without checking whether the second platform differs. When the user asks about a feature of a cross-platform tool, load this skill and search for "<tool> <feature> on <device> <model>" before stating whether it exists or how to use it.

## 搜索引擎架构

插件式搜索架构，每新增一个搜索源只需在 `## 搜索引擎注册表` 中注册，无需改动核心工作流。

### 搜索引擎注册表

| 序号 | 搜索引擎 | 类型 | 触发条件 | 配置依赖 | 扩展状态 |
|------|---------|------|---------|---------|---------|
| 1 | **web_search** (Tavily/默认) | 全网搜索 | 默认启用 | 无（内置） | ✅ 已注册 |
| 2 | **知乎搜索** | 中文社区 | 中文经验、评测、口碑 | ZHIHU_API_KEY | ✅ 已注册 |
| 3 | **微信读书** | 书籍内容 | 书籍知识、理论框架 | WEREAD_API_KEY | ✅ 已注册 |
| 4 | **web_extract** | 页面内容 | 需要读特定 URL 全文 | 无（内置） | ✅ 已注册 |
| 5 | **blogwatcher** | RSS/博客 | 追踪技术博客更新 | blogwatcher-cli | 📋 可选 |
| 6 | **arxiv** | 学术论文 | 学术前沿、算法论文 | arxiv CLI | 📋 可选 |
| 7 | **youtube-content** | 视频教程 | 操作类问题视频演示 | youtube-transcript | 📋 可选 |
| 8 | **自定义搜索** | 任意 API | 用户指定特定 API/服务 | 按需配置 | 🔧 可扩展 |

**扩展新搜索引擎的规则**：
1. 在上方表格中新增一行（名称/类型/触发条件/配置依赖）
2. 在下方 `## 搜索引擎调用模板` 中新增 Python 调用模板
3. 在 `## Phase 1 搜索 Agent` 的输出模板中补充该引擎的调用方式
4. 无需改动 Phase 3/4 的任何内容

## 核心工作流（v2）

```
搜索 Agent（Phase 1 + 2 合并） → 整合 Agent（Phase 3 + 4 合并）
```

**不再用 4 个角色，只用 2 个 Agent 流水线。** 节省角色切换的 prompt 重建和 token 消耗，减少出错点。

---

### Agent A：搜索 Agent（Phase 1 + 2 合并）

**输入**：用户描述的问题现象  
**一次性输出以下所有字段**：

#### 0. 前提假设清单（强制第一步，必须过这关才能继续）

**生成前提清单前，先检索本次对话及可用的历史记忆中是否已有相关事实记录。**

按三档分级标注：

| 档位 | 标注前缀 | 含义 | 示例 |
|------|---------|------|------|
| A | `[历史确认]` | 历史对话中反复提及且为稳定型属性，**自动跳过用户确认**，但必须显式展示来源 | 设备型号、硬件架构 — "依据：历史对话提及 5 次（最近：2026-06-30）" |
| B | `[历史记录-需复核]` | 历史有记录但是易变型属性，**需用户一次性点头**（不从零问，只确认是否仍然成立） | 软件版本、固件来源 — "历史记录显示为 Armbian 23.11，是否仍然成立？" |
| C | `[用户陈述未验证]` / `[系统推测]` | 无历史记录，**必须先让用户确认**，再进入搜索阶段 | "设备平台：MediaTek Filogic ← 必须先确认，因为下载镜像可能是 Amlogic" |

**稳定型 vs 易变型分类规则**：

| 稳定型（标A，自动跳过） | 易变型（标B，需复核） |
|------------------------|----------------------|
| 设备型号 | 软件/系统版本 |
| 硬件架构/SoC | 固件来源/编译版 |
| 物理接口类型 | 配置参数 |
| 网络拓扑结构 | 驱动版本 |
| 网络接口数量 | 内核版本 |
| 设备状态（长期插电/移动使用） | 网络配置 |

**强制规则**：
- 禁止在前提清单有 C 类（未验证/推测）项时直接进入子问题拆解
- B 类项只要求用户一次性点头（"是/否/其他"），不要从零开始问
- A 类项自动标注，但必须在报告中显式展示"这项是从历史记忆自动填充的"，禁止悄悄跳过
- 用户更换过设备后，所有 A 类项自动降级为 C 类

**输出格式**：
```
- [历史确认] 设备型号：斐讯 N1 — 依据：历史对话提及 5 次（最近：2026-06-30）
- [历史记录-需复核] 固件来源：Armbian 23.11 — 历史记录显示为 23.11，是否仍然成立？
- [用户陈述未验证] 设备平台：Amlogic S905D ← 必须先确认，因为下载镜像可能是 MediaTek Filogic
- [系统推测] 固件来源：flippy 编译版
```

#### 1. 问题分类标签

- 系统 / 网络 / 软件 / 硬件 / 配置 / 权限 / 依赖 / 性能（可多选）

#### 2. 子问题拆解

- 拆解为 2-4 个子问题，MECE 原则，每个子问题独立可搜索
- 列出需用户补充确认的关键信息（如果前提清单全是 `[已确认]` 则标注"无"）

#### 3. 搜索关键词（中英文）

- 每类子问题对应 2-3 组英文关键词 + 2-3 组中文关键词

#### 4. 引擎选择（动态决定，不是默认全开）

根据问题分类决定启用哪些引擎，**禁止默认调用所有引擎**。判断规则：

| 问题分类 | 启用引擎 | 排除引擎及理由 |
|---------|---------|--------------|
| 硬件/嵌入式/国产设备 | web_search + 知乎 | 微信读书（非理论类）、arxiv（非学术） |
| 软件配置/操作 | web_search + web_extract | 微信读书（非理论）、arxiv（非学术） |
| 中文经验/口碑 | 知乎搜索 + web_search | 微信读书（非书籍知识） |
| 理论/方法论 | 微信读书 + web_search + arxiv | 知乎（社区非系统知识） |
| 学术/算法 | arxiv + web_search | 微信读书（非书籍知识） |
| 视频教程优先 | web_search + youtube-content | 知乎（非视频）、微信读书 |

强制规则：**若问题分类不含"理论/方法论"标签，禁止调用微信读书引擎。**

#### 5. 搜索结果（每个引擎独立返回）

- 至少 3 条不同来源的相关结果
- 每条结果标注：来源类型 / 是否点开验证原文 / 适用条件 / 失败案例
- 提取关键命令/配置/代码片段
- 标注冲突信息（不同来源给出矛盾方案时）

**搜索引擎调用模板**：

```python
# 引擎 1: web_search (Tavily/默认全网搜索)
from hermes_tools import web_search
result = web_search("关键词", limit=5)
# 返回: {"data": {"web": [{"url", "title", "description"}, ...]}}

# 引擎 2: web_extract (读指定 URL 全文)
from hermes_tools import web_extract
result = web_extract(["https://url1", "https://url2"])
# 返回: {"results": [{"url", "title", "content", "error"}]}

# 引擎 3: 知乎搜索
# POST https://developer.zhihu.com/api/v1/content/{endpoint}
# 需要: ZHIHU_API_KEY + 动态 X-Request-Timestamp(unix 秒)
# 注意: 参数名 "Query" 大写 Q，否则返回 "query is required"

# 引擎 4: 微信读书
# POST https://i.weread.qq.com/api/agent/gateway
# 鉴权: Authorization: Bearer <WEREAD_API_KEY>
# body: {"api_name": "/store/search", "keyword": "...", "skill_version": "1.0.3"}
# scope: 0=全部, 10=电子书, 6=作者, 12=全文, 13=书单, 2=公众号, 4=文章

# 引擎 5+: 预留扩展点（新增搜索引擎在此处加模板）
```

**搜索关键词构造**：
```
# 错误信息直搜（最优先）
"完整错误信息" site:github.com

# GitHub Issues 专项搜索
"错误信息" site:github.com/xxx/xxx/issues

# 多源交叉
"问题描述" fix OR solution OR workaround

# 时间范围限定
"问题描述" 2024..2026
```

---

### Agent B：整合 Agent（Phase 3 + 4 合并）

**输入**：搜索 Agent 返回的全部结果（含前提清单/分类/关键词/搜索结果）  
**处理逻辑**：

#### 1. 去重

- 合并相同方案，保留最完整版本

#### 1.5 跨引擎来源去重（新增，不可跳过）

**在统计"独立来源数"之前，必须先对全部引擎的原始结果做来源去重：**

1. 收集所有引擎返回的来源 URL
2. 按 URL 分组，同一 URL 只计 1 个独立来源
3. 如果同一 URL 在不同引擎中被描述为不同内容，以最早/最完整的那个为准
4. 去重后的来源才计入"独立来源数"

**⚠️ 未去重的后果：**如果来源列表中存在同一 URL 被重复计数，可信度等级必须自动降一档。

#### 2. 冲突解决（按问题类型分流，不再写死"官方 > 社区"）

| 场景 | 冲突解决优先级 |
|------|--------------|
| 设备/技术栈仍由官方积极维护 | 官方文档 > 社区经验 |
| 设备已停产/小众/嵌入式国产硬件 | 社区验证次数 > 官方文档（官方可能已不维护） |
| 中文社区活跃领域（路由器/国产硬件/嵌入式） | 中文来源优先级提高，不再默认英文优先 |
| 所有场景通用 | 近 12 个月内方案 > 旧方案（技术栈可能已变），有失败记录的必须标注 |

#### 3. 可信度评估（替代原有"成功率百分比"）

**禁止使用百分比量化成功率，必须用可信度等级 + 三项依据：**

**⚠️ 可信度等级与独立来源数挂钩（非充分但必要条件，不可例外）：**

| 可信度等级 | 独立来源数 | 定义 |
|-----------|-----------|------|
| 高 | ≥2 个 | ≥2 个独立、相关、已验证原文的来源，且无矛盾信息 |
| 中 | 1 个 | 1 个独立验证来源，或 2+ 个来源但存在部分矛盾/适用条件不完全匹配 |
| 低 | 0 个 | 0 个验证来源，或仅有未验证/不相关来源 |

**⚠️ 小众设备/冷门操作上限限制：**若客观上只有 1 个来源存在（小众设备如坚果 Pro3/冷门操作），可信度上限为"中"，必须在依据栏注明"该操作目前仅有单一可查证来源，建议操作前在论坛/群组二次确认"。

**⚠️ 未验证来源硬规则：**
- 来源标注为"原文抓取失败"或"仅标题/摘要可见" → 该来源不计入独立来源数，不得作为可信度判断的支持依据
- 未验证来源只能在"待验证线索"栏单独列出，供用户自行查证
- 同一来源在不同方案中的处理必须一致：违反则可信度自动降级一档

**⚠️ 来源相关性校验（逐条自检，不可跳过）：**
生成"独立来源数"前，Agent 必须对清单内每个来源**逐条自问**：
> *"这条来源的内容，是否直接对应本方案的具体操作步骤（而非同一设备下的其他方案/同一大类问题）？"*

不通过则剔除，并在"待验证线索"或"已排除来源"栏注明：`[已排除] [URL] — 该来源支持的是方案X（[方案名]）的具体操作，与本方案不直接相关，不计入独立来源数`。
计入独立来源数的每一条来源，必须同时满足：(1) 原文已成功抓取 (2) 内容直接支持该方案的具体操作步骤（而非仅提及同一设备/话题） (3) 跨引擎 URL 去重后唯一。违反则可信度降一档并标注"来源相关性存疑"。每条来源必须标注支持的具体操作内容，如：`[B站文章](url) — 已验证原文，支持了"长按三键进908"的步骤描述`。

**⚠️ 命令平台适配性规则：**步骤中的命令行命令必须标注运行平台。Agent 自己补充的命令必须确认在用户实际平台（macOS/Linux/Android）上可用。macOS 上不原生支持的工具（如 lsusb, grep -r 的某些 flag, awk 的高级用法）必须标注"需安装 Homebrew 工具包"或使用平台等价命令。出现在刷机/硬件操作关键节点上的命令尤其需谨慎核对。

#### 4. 结构化输出 + NLM 合成

Agent B 输出结构化方案后，**必须将搜索结果全部喂入 NotebookLM 做统一分析**，不做手动综合：

```bash
# 创建 NLM 笔记本
nlm create notebook "<问题>-搜索分析"

# 将所有搜索材料合并喂入
CONTENT=$(cat /tmp/search_results_combined.md)
nlm add text <notebook_id> "$CONTENT" --title "搜索材料" --wait

# NLM 出统一方案
nlm query notebook <notebook_id> "基于这些材料给出综合方案。列出共识、分歧、可信度。"
```

**关键规则：**
- 手动输出的结构化方案仅作为中间过程
- **最终决策必须来自 NLM**，不来自我手动综合
- 这是用户 2026-07-16 强行纠正的核心原则

## 与三通道模型的关系

mao-search-workflow 对应三通道模型中的：

| 通道 | 对应技能 |
|------|---------|
| **A — 问三AI** | `triple-ai-nlm-synthesis` |
| **B — 搜+喂NLM** | **mao-search-workflow** → NLM |
| **C — MoA 交叉** | mao-search-workflow + 多引擎 |
| **D — Grok API** | 直调 xhahlf.top |

所有通道的输出 → 全部喂 NLM → NLM 出最终方案。**上层统一走 `triple-ai-nlm-synthesis` 的 NLM 合成步骤。**

## 约束与规则

- **不伪造信息**：找不到就是找不到，不要编造命令或方案
- **标注来源**：每个方案标注来自哪个信息源，是否点开验证过原文
- **标注时效**：注明方案适用的软件版本和时间范围
- **不跳结论**：先确认复现条件再下判断
- **前提锁定强制**：Phase 1 第一步必须是前提清单，有未验证项（C类）必须停下来问用户
- **可信度替代百分比**：禁止用"成功率 XX%"，必须用高/中/低 + 三项依据。高=≥2个独立验证来源，中=1个独立验证来源，低=0个验证来源。小众设备/冷门操作只有1个来源时上限为"中"
- **动态引擎选择**：根据问题分类动态启用引擎，禁止默认全开
- **冲突分流**：不再写死"官方 > 社区"，按设备维护状态动态调整
- **安全警告**：涉及 root/刷机的操作必须标注风险
- **硬件改造方案完整性**：涉及焊接/拆焊/开壳的物理操作，步骤必须给出具体判断条件（什么情况下做、什么情况下不做）和参考链接。如果步骤不完整或判断条件缺失，必须标注"步骤不完整，不建议直接执行，需先找原始教程逐图核对"并降级可信度
- **命令平台适配性**：步骤中的命令行命令必须标注运行平台。Agent 自己补充的命令必须确认在用户实际平台（macOS/Linux/Android）上可用。macOS 上不原生支持的工具（如 lsusb）必须标注"需安装 Homebrew 工具包"或使用平台等价命令。刷机/硬件操作关键节点上的命令尤其需谨慎核对
- **零成本优先**：优先推荐免费方案，不接受付费方案
- **精确描述**：涉及硬件操作的描述必须精确到按键/端口/文件路径

---

## 已覆盖的历史问题速查

### 1. S905D vs S905X 硬件差异
N1 是 S905D（无 DVB 电路），S905X 有 DVB 但不同主板。DTB 文件不通用，刷错会导致无网络/负载高。ophub 镜像选 `s905d` 系列。

### 2. USB 供电不足
症状：插鼠标/OTG 网卡没反应，频繁掉线黑屏。
修复：
1. 换靠近 HDMI 的 USB 口（供电更强）
2. 用带供电的 USB Hub
3. 外接 USB 电源（公对公 USB 线，电脑 USB 供电到 N1）
4. 拆开 N1，在指示灯附近触点短接（需要电烙铁）

### 3. apt/dpkg 锁死
```bash
ps aux | grep apt
kill -9 <PID>
sudo rm /var/lib/dpkg/lock-frontend
sudo rm /var/lib/dpkg/lock
sudo rm /var/cache/apt/archives/lock
sudo dpkg --configure -a
sudo apt update
```
预防：刷机后先 `dpkg --configure -a` 再 `apt update`。

### 4. SSH 首次登录 / 改密码自动断开
- 密码 1234 → 输入两遍新密码 → 自动断开是正常的
- 改密码后自动退出 → 换 U 盘再试（恩山已知坑）
- 用英文键盘输密码，不要输入法

### 5. MAC 地址变化导致 DHCP 掉线
症状：路由器后台看 IP 闪一下掉线。根因：Amlogic 从某版本起改了 MAC 生成算法，每次重启 eth0 的 MAC 变。
修复：在路由器后台绑定 MAC→IP，或 Armbian 中设静态 IP（`armbian-config → Network → Fixed IP`）。

### 6. DTB 不匹配
症状：无网络、CPU 负载异常高、HDMI 无输出。修复：修改 `/boot/uEnv.ini` 指向正确 DTB（N1 用 s905d 系列）。

### 7. U 盘兼容性
- Class 10 以上 USB 2.0 U 盘（N1 只有 USB 2.0 接口）
- 品牌 U 盘（三星/闪迪/金士顿）
- 容量 8-32GB，不推荐杂牌/扩容盘

---

## 参考资源

- GitHub Issues：https://github.com/xxx/xxx/issues
- StackOverflow：https://stackoverflow.com
- 恩山无线论坛：https://www.right.com.cn/forum/
- 博客园：https://www.cnblogs.com/
- ZNDS：https://www.znds.com/
- 知乎：https://www.zhihu.com

## Session Knowledge Bank (掉进过的坑)

- `references/claude-desktop-vs-cli-third-party-inference.md` — **CLI vs GUI 不是功能差异，是客户端校验差异**。Claude Desktop 1.6259.1 开始对 Gateway 模型名做 Anthropic-style 校验，Claude Code CLI 仍允许自定义模型名。由此类问题进入时优先查该参考文件。
- `references/claude-desktop-harness-sandbox-limits.md` — **Claude Desktop code execution 的通用限制证据**。GitHub #71152 表明 harness-level sandbox 会 block localhost/network endpoints；#22542 表明 30–60s MCP tool call 不可靠，60s+ 常过载；#59989 表明 Local Agent Mode 存在约 5 分钟 wall-clock cycle limit。由任何“Desktop/Code tab 不能完成但终端能完成”的任务进入时优先查该参考文件。
- `references/software-project-evaluation.md` — **软件项目可信度评估模板**。当用户让你评估一个开源项目是否靠谱时，走六轴评估流程（GitHub 健康度 / 包管理器数据 / 社区口碑 / Bugs 和 Issue 质量 / 安全性 / 竞争对比），按可信度等级输出。来源：OmniRoute 评估会话 (2026-07-07)。
