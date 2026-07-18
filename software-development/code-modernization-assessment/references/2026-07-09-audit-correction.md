# 2026-07-09: 前端审计纠偏 → .hermes_rules 重写 + 本技能诞生

## 发生了什么

用户要求基于 `.hermes_rules` 和 Baseline 标准做前端局部审计。助手（土同学）撰写了详细的审计报告，核心建议包括：

- 用 `light-dark()` 替换 JS 主题切换
- 用 CSS `@container` 替换 `@media` 硬编码断点
- 用 CSS `anchor-name` / `position-anchor` 替换 JS DOM 插入
- 删除 old-site 遗留 JS

## 用户的纠正

用户指出：这些建议本身就是在**追新**——从一组具体技术名词出发找替代方案，而不是从"现有代码有什么真问题"出发。助理说的"坚定原则优先于新功能"是对的，但审计却按新功能逐个推荐替换，自相矛盾。

**核心纠正：** "你现在用的方式才是现代的" —— 现有的 clear / explicit / debuggable 代码就是最现代的选择。不要为了用新特性而盲目推翻它。

## 产出

1. `.hermes_rules` Rule #1 从具体技术名词重写为 process-driven 三原则（拒绝追新强迫症 / Baseline 动态审查 / 重构准则）
2. 本技能作为所有"技术现代化评估"类任务的参考框架

## 教训

- 审计报告的情绪/语气可能正确（"坚定原则优先"），但具体建议若仍以新功能为出发点，就自相矛盾
- 用户对"原则 vs 执行"的偏差非常敏感
- 知识（学了一个新 CSS 特性）和判断（该不该在这用）要分开

## 后续：原则的正确应用

修正后，在同一会话中按照新原则对 `js/main.js` 做了减法规格主题切换重构：

- **砍掉** 6 个冗余函数（`applyTheme`、`applySystem`、`getSaved`、`getSystemTheme`、`updateThemeToggle`、`addListener` 回退）
- **依据**：页面内联 boot script 已在 DOMContentLoaded 前完成 theme dataset 初始化，main.js 不需要重做
- **不引入** 任何新 CSS 特性（`light-dark()` 虽已 Widely Available，但不满足"降低复杂度"门槛——现有 JS 逻辑清晰可控，替换后不会消灭第三方依赖也不会减少行数）
- **结果**：91 行 → 47 行（-48%），行为零变化，全部通过 ad-hoc 验证
- **验证方式**：Node.js 语法检查 + 死函数残留检测 + 关键行为模式清单 + 行数硬约束
