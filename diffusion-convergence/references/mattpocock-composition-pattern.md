# Matt Pocock Skills 组合模式参考

从 [mattpocock/skills](https://github.com/mattpocock/skills) (160K⭐) 学到的设计模式。

## 核心哲学

- **小、可组合、易修改** — 入口 skill <500 字节，只做一件事
- **`disable-model-invocation: true`** — 纯执行型 skill 不让模型在对话里误触发
- **链式调用** — 一个 skill 完成 → 调用下一个

## 5-Skill 流水线

```
/grill-with-docs      → 用 domain-modeling skill 压榨需求（245 字节）
    ↓
/to-spec              → 生成 PRD（Problem/User Stories/Impl Decisions/Testing/Out of Scope）
    ↓
/to-tickets           → 拆成垂直切片 ticket，标注 block 关系
    ↓
/implement            → 按 ticket 用 TDD 实现，常跑 typecheck+test
    ↓
/code-review          → 双轴并行：Standards（编码规范）+ Spec（需求匹配）
```

## to-spec 模板结构

```
## Problem Statement
## Solution
## User Stories（编号列表，As a... I want... so that...）
## Implementation Decisions（不含文件路径/代码片段）
## Testing Decisions（只测外部行为）
## Out of Scope
## Further Notes
```

## to-tickets 垂直切片规则

- 每个 slice 切透所有层（schema/API/UI/test）— 垂直而非水平
- 一个完成的 slice 可独立 demo 或验证
- 每个 slice 适合单个 context window
- 标注 block 边：哪些 ticket 完成后才能开始这个
- **Frontier 工作法**：只处理「所有 blocker 都已完成」的 ticket。线性链就从顶到底。
- 大范围重构用 **expand–contract** 模式：
  1. Expand：旧形式旁加新形式，什么都不坏
  2. Migrate：按 blast radius 分批迁移 call site（每批一个 ticket，blocked by expand）
  3. Contract：所有 caller 迁移完毕后删除旧形式（blocked by 所有 migrate batch）

## code-review 双轴并行审查

Matt Pocock 的 code-review skill 是最复杂的一个（6.7KB），核心设计：

**两个独立审查轴**，同时用 sub-agent 并行跑：

| 轴 | 审查内容 | 评分方式 |
|------|---------|---------|
| **Standards** | 代码是否符合 repo 编码规范 + Fowler 代码坏味道基线 | 硬违规（违反规范）vs 判断性调用（坏味道） |
| **Spec** | 代码是否正确实现 Issue/PRD 要求 | 缺失项 / 超范围 / 实现错误 |

**关键设计**：
- 两个 sub-agent 并行运行，防止相互污染 context
- 审查结果分开报告，不合并排名 — 一个轴 pass 另一个可能 fail
- 范基准（Fowler 坏味道：Mysterious Name / Duplicated Code / Feature Envy / Data Clumps / Primitive Obsession / Repeated Switches / Shotgun Surgery / Divergent Change / Speculative Generality / Message Chains / Middle Man / Refused Bequest）
- 只审查 diff（相对于固定 commit/branch/tag），不扫描全库

## 对我们的启发

1. `diffusion-convergence` 收敛完可自动输出 to-spec 格式的文档
2. 可把输出阶段拆成独立 skill（converge → format → implement）
3. 收敛中的决策日志可映射到 to-tickets 的 block 图
