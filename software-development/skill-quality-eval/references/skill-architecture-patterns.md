# Skill 架构模式（来自 mattpocock/skills）

从 160K⭐ 的 [mattpocock/skills](https://github.com/mattpocock/skills) 提炼的设计模式。

## 1. disable-model-invocation

纯执行型 skill 不应参与对话触发判断，加这个标记让模型不在对话中随意调用：

```yaml
disable-model-invocation: true
```

**适用场景**：编排型 skill（调用其他 skill）、流程约束型 skill、纯模板输出型 skill。

## 2. 组合链（Composition Chain）

入口 skill 极度精简（<500 chars），只做两件事：
1. 定义触发条件
2. 委托给其他 skill

示例（mattpocock 的 `implement`，仅 433 chars）：
```yaml
disable-model-invocation: true
---
Implement the work described by the user in the spec or tickets.
Use /tdd where possible.
Run typechecking regularly, single test files regularly.
Once done, use /code-review to review the work.
```

**链式关系**：`grill-with-docs → domain-modeling → to-spec → to-tickets → implement → code-review`

## 3. 模板驱动输出（Template-Driven）

用 XML 标记定义输出模板，放在 SKILL.md 中。关键设计：

### Template 设计原则
- 放在 `<spec-template>` 等自定义 XML 标签中，明确这是模板而非正文
- 字段用 **粗体标题 + 描述段落** 而非表格
- 包含 `Example` 小节展示真实用法
- 有明确的 `Out of Scope` 字段防止范围蔓延

参考 `to-spec` 的模板结构：
```
Problem Statement → Solution → User Stories → Implementation Decisions → Testing Decisions → Out of Scope → Further Notes
```

## 4. 双轴并行审查（Two-Axis Parallel Review）

`code-review` 用两个并行 sub-agent 分开审查：
- **Standards 轴**：是否符合代码风格 + Fowler 代码坏味
- **Spec 轴**：是否实现了 spec 要求

目的是防止"代码规范但功能错了"或"功能对了但代码写得烂"互相掩盖。

## 5. 垂直切片（Vertical Slicing）

`to-tickets` 将 spec 分解为 **tracer bullet** 风格的 ticket：
- 每个切片贯穿所有层（schema → API → UI → 测试）
- 每个切片在单 context window 内可完成
- 每个 ticket 标注依赖（blocked by）
- 从无依赖的 ticket 开始执行（"work the frontier"）

## 6. Domain Glossary 优先

`domain-modeling` 要求在 spec/tickets/code-review 中统一使用项目领域术语（ubiquitous language），并在 `CONTEXT.md` 中维护术语表。

## 7. 固定比较点（Fixed Point Diff）

`code-review` 要求用户指定一个固定点（commit/branch/tag），比较 HEAD 到该点的 diff。避免"审所有代码"这种无边界请求。
