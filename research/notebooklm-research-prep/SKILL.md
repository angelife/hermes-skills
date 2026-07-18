---
name: notebooklm-research-prep
title: "NotebookLM 项目前期研究 — 全面采集 + 深度消化"
description: "做项目前先把相关资料搜全 → 喂 NotebookLM → 拿分析回来 → 再动手。避免一知半解就开干。"
category: research
tags: [research, notebooklm, preparation, skill]
---

# NotebookLM 项目前期研究 — 全面采集 + 深度消化

## 触发条件

当用户说以下任一指令时：
- "把这个研究明白"
- "吃透这个说明书"
- "看看这个东西能不能用"
- "做项目前的准备"
- 提到要部署/安装/实验一个不熟悉的技术/工具

## 原则

- **不要直接读文档就开干** — 你消化不如 NotebookLM 快且全。
- **查证溯源先行** — 检查记忆/hindsight/skill 中有没有已有记录，避免重复研究。
- **沿用现成** — 先查 NotebookLM 里有没有已有笔记本，有就复用，没有才建新的。
- **全面覆盖** — 搜资料要覆盖：官方文档、深度分析、实战教程、已知 bug/issues、社区讨论、学术论文（如有）。
- **先查再建** — 建笔记本前先 `nlm notebook list` 看有没有同主题已存在的。
- **NLM 是统一分析引擎** — 所有信息来源（OpenBridge 三AI、web_search、Grok API、MoA）的原始输出全部喂 NLM 做合成，不自已手动对比/综合。NLM 的合成"非常高效精准"。
- **NLM 是商业完整版** — 用户已付费购买完整功能（thomasx.xie@gmail.com），不限用量，大胆用。

## 标准流程

### Step 1: 查存量

```bash
# 查 hindsight 有没有相关记录
hindsight_recall query="<工具名>"

# 查 NotebookLM 已有笔记本
nlm notebook list | grep -i "<工具名>"
```

如果已有 NotebookLM 笔记本且资料够用 → 跳过 Step 3，直接 Step 4。

### Step 2: 全面搜索资料

至少搜 3-5 个方向，每方向 5-8 条结果：

| 方向 | 搜索关键词示例 |
|------|--------------|
| 官方信息 | `<工具名> 官方文档/readme/getting started` |
| 深度分析 | `<工具名> 架构 原理 深度解析` |
| 实战部署 | `<工具名> 部署 安装 配置 实战` |
| 已知问题 | `<工具名> issues bugs troubleshooting` |
| 社区讨论 | `<工具名> reddit discussion 踩坑 经验` |
| 学术论文 | `<工具名> paper arXiv` (如适用) |

用 `web_search` 并行搜多组关键词，不要串行一个一个搜。

### Step 3: 创建笔记本并喂资料

```bash
# 建笔记本（如果不存在）
nlm create notebook "<项目名> - 全面研究"

# 从 URL 批量喂资料（一次最多 8 个，分批）
nlm add url <notebook_id> --url "<url1>" --wait
nlm add url <notebook_id> --url "<url2>" --wait
```

**喂资料原则：**
- 一次最多 8 个 URL，分批喂
- 优先喂：官方 README > 官方文档 > 深度分析 > 实战教程 > 已知 issue > 社区讨论
- 学术论文 arXiv 链接也喂进去
- 关键 issue（尤其是集成 bug）必须包括

### Step 4: 深度提问

一次性问 5-6 个覆盖全局的问题：

```bash
nlm query notebook <notebook_id> "请全面分析 <工具名>。核心要点：
1) 和同类方案的本质区别
2) 核心架构和工作原理
3) <集成框架名> 的集成方式和步骤（如适用）
4) 部署到目标环境的资源开销和注意事项
5) 局限性和已知问题
6) 优缺点总结"
```

### Step 5: 输出消化结论

把 NotebookLM 的回答提炼为 5 条以内的关键判断，直接回答：
- 这个工具能不能用？
- 装在哪？
- 有什么坑要注意？

## 输出格式

```
## 📖 <项目名> 研究结论

### 核心判断
<一句话结论：能用/不能用/需实验>

### 关键信息
1. <要点1>
2. <要点2>
3. <要点3>

### 已知风险/坑
- <坑1>
- <坑2>

### 下一步
<具体行动>
```

## Pitfalls

- ❌ 不要跳过 Step 1 — 先查历史记录，不要重复建笔记本
- ❌ 不要只搜中文/只搜英文 — 国内外都要覆盖
- ❌ 不要遗漏已知 issue — 集成 bug 装完才发现最浪费时间
- ❌ 不要在喂资料时中断（`--wait` 参数很重要）
- ❌ 不要一次性喂超过 8 个 URL（NotebookLM 处理上限）
- ✅ 喂完后再加一轮问题细化不懂的部分

## 参考文件

本技能 `references/` 目录存放具体项目的研究结论。例如：

- `references/openviking-research-2026-07.md` — OpenViking 研究：许可证、已知 bug (#5721, #50133)、Cloudflare 可行性、部署要点

每次完成项目研究后，把核心发现的引用信息（许可证、已知 bug、部署约束、关键对比数据）追加到这个目录的对应文件中，供后续部署时直接查。
