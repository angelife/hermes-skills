---
name: code-modernization-assessment
description: >-
  Framework for evaluating whether to replace existing working code with
  "newer" technical approaches. Encodes the principle that stable, clear,
  explicit, debuggable implementations are usually the most modern choice
  — novelty alone is never sufficient justification for a rewrite.
tags:
  - engineering-decision
  - refactoring
  - web-standards
  - baseline
  - technical-debt
---

## ⚠️ 触发条件

以下场景**必须提前加载本技能**，不得跳过：

| 触发场景 | 示例 |
|---------|------|
| 被要求做"技术现代化"审计或评估 | "看看哪些 JS 可以用现代 CSS 代替"、"审计前端技术栈" |
| 建议用新特性替换现有实现 | "可以用 Container Queries 重写这个 grid" |
| 讨论代码重构方向 | "要不要把 jQuery 去掉换成原生？" |
| 评估第三方库取舍 | "这个 50KB 的库能不能用浏览器原生 API 替代？" |

**加载后先自检：** 我是否已经预设"新=好"的倾向？重读本节第一句再往下走。

---

## 核心原则

### 现有的稳定实现，通常就是最现代的

Clear、Explicit、Debuggable 的现有代码，比一个"用了新特性但更难调试"的替代品更现代。浏览器新 API 不是免费的技术债消除券——每引入一项新特性都有隐形成本：

- 开发者认知开销（团队/维护者是否熟悉）
- Baseline 覆盖缺口（老旧设备、小众浏览器）
- Polyfill / 降级代码体积
- 调试工具链支持（DevTools 对新特性的覆盖程度）

**这不等于永远不重构。** 而是：重构的理由不能是"它老了所以该换"，必须是"替换后显著降低了代码复杂度或消灭了真正的第三方依赖"。从"追新"变成"减负"。

---

## 前置操作

### 0. 加载项目级约束文件

```bash
# 如果项目根目录存在 .hermes_rules，必须先读
test -f .hermes_rules && cat .hermes_rules
```

`.hermes_rules` 是项目级硬约束，优先于本技能的所有建议。如果它定义了特定的评估标准（如 "拒绝追新强迫症"），以其为准。

---

## 评估流程（三步检查）

在建议任何技术替换前，依次通过这三关：

### 第一关：现有的实现有什么问题？

先客观回答：

- [ ] 现有代码是否**可读、可调试**？（代码清晰度）
- [ ] 现有代码是否有**实际性能问题**，还是只是"感觉不够现代"？（性能证据）
- [ ] 现有代码的依赖是否**真实可维护**？（如果是手写 50 行纯 JS，比引入一个 20KB 的库更轻）
- [ ] 替换是否值得用户（目标受众）的浏览器覆盖率损失？

**如果现有实现清晰、无性能问题、依赖可控 → 停止，维持现状。** 不要因为"刚学了一个新特性"就找地方用。

### 第二关：目标新特性的 Baseline 状态

在推荐任何新 Web 能力前，必须查 [Web.dev Baseline](https://web.dev/baseline) 确认兼容性状态：

| 状态 | 含义 | 允许操作 |
|------|------|---------|
| **Widely Available** | 跨主流浏览器稳定支持 ≥2 年 | 可推荐，但门槛仍看第三关 |
| **Newly Available** | 刚进入稳定通道，覆盖不全 | **禁止**作为重构理由，必须有 polyfill/降级方案才可提及 |
| **Limited / Non‑Standard** | 实验性或仅单浏览器 | 不允许出现在推荐清单中 |

**实用查法：** `web_search("baseline <feature-name> web.dev")` 或直接访问 Baseline 页面。

### 第三关：替换是否真的降低了复杂度？

- [ ] 替换后能**删除现有的第三方依赖**吗？（如删掉整个 jQuery / 一个 npm 包）
- [ ] 替换后的代码量比现有方案**少还是多**？（新 API 往往需要 polyfill）
- [ ] 替换后是否更容易调试？（DevTools 对该特性的支持成熟度）
- [ ] 替换是否引入了新的隐式行为？（CSS 特性常有你不知道的 side effects）

**通过标准：** 新方案必须**显著降低代码复杂度**（如消灭复杂的三方依赖）且 Baseline 为 Widely Available。两个条件缺一不可。

---

## 审计输出格式

推荐用表格结构呈现审计结果，每项变更独立一行，附通过/不通过理由：

```markdown
| 模块 | 现有方案 | 建议 | 理由 |
|------|---------|------|------|
| js/main.js | 91 行 JS 主题切换 | 做减法（→47行） | 与内联 boot script 重复，砍 6 个冗余函数 |
| js/search.js | indexOf 模糊搜索 | 不动 | 清晰、无依赖、无性能问题 — 不满足"降低复杂度"门槛 |
| old-site JS | jQuery 1.4.2 | 不动 | 内容独立渲染，删 JS 只会产生 404 console 错误 |
```

优先用"做减法"（删冗余）而非"做替换"（加新特性）。如果某条评估结果是"不动"，明确写出原因。

---

## 变更后的验证

无论建议是否被采纳执行，交付前必须做可重复的验证：

| 验证项 | 方法 |
|-------|------|
| 语法正确性 | `new Function(code)` 或 `node --check` |
| 死代码清除 | 搜索旧函数名是否残留 |
| 行为关键模式 | 列出不可少的行为清单（如 `localStorage.getItem`、`dataset.theme`），逐一确认 |
| 行数约束 | 与原始行数对比，声明增减百分比 |

用 ad-hoc 临时脚本（`mktemp /tmp/hermes-verify-XXXX.js`），执行后自清理。明确标注为 ad-hoc 验证而非 suíte green。

---

## 常见陷阱

### 1. "npm 包 = 重，浏览器原生 = 轻"不是绝对的

一个 2KB 的 well-maintained 库，可能比用 3 个不同浏览器 API 拼凑出的方案更可靠、更容易理解、更少边缘情况。

### 2. 新 CSS 特性不是零成本的

- `@container`（容器查询）—— 需要在父元素上声明 `container-type`，改变了层叠上下文，可能干扰子元素的 `position: fixed` / `z-index`
- `anchor-name` / `position-anchor` —— 调试时 DevTools 仍不够直观，且 polyfill 方案体积大
- `light-dark()` —— 浏览器兼容良好（Baseline 2024），可优先使用，但前提是确认用户群体没有大量 Safari 旧版

### 3. 不把"我没用过"等同于"这代码过时了"

`display: table` + `table-cell` 做垂直居中，比 flexbox 早，但在 2026 年依然是每浏览器 100% 覆盖的可靠方案。不要因为自己更熟悉 flexbox 就说前者"该换"。

### 4. "现代"是手段不是目的

用户明确要求的不是"变现代"而是**减少复杂度**、**提高可维护性**。如果替换后代码行数增加、依赖数量不变、调试更困难——那它就不是"现代化"，是"折腾化"。

---

## 项目级约束联动

项目中若存在 `.hermes_rules`，其 `Modern Web Engineering Standard (Process-Driven)` 节是硬约束，优先于本技能的所有建议。本技能提供的只是评估流程，`.hermes_rules` 定义的才是项目内的强制标准。

---

## 参考案例

> 参考文件：`references/2026-07-09-audit-correction.md` — 本技能的诞生背景。一次前端审计中，助手基于多个具体技术名词（Anchor Positioning、Container Queries）推荐替换现有 JS，被用户纠正为"现有的稳定实现就是最现代的"，从而促成 `.hermes_rules` 重写和本技能的建立。
>
> 后续操作：在该原则指导下，对 `js/main.js` 做了纯粹做减法的重构（91 行 → 47 行），砍掉 6 个与内联 boot script 重复的初始化函数、移除已过时的 `matchMedia.addListener` 回退，不引入任何新 CSS 特性。验证通过。（2026-07-09）
