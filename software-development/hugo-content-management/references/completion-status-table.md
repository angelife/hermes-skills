# 架构图完成度明细表（卡片样式）

用于在架构图页面下方展示每个模块的子模块完成状态。

## 注意：颜色必须适配主题

- **dark 独立页面**：白字 #e2e8f0 + 深色背景 #020617，使用霓虹色 #34d399/#fbbf24
- **light Hugo 标准页面**：深灰字 #333 + 白底，使用柔和的绿色 #10b981 / 黄色 #f59e0b。`class="tag tag-stable"` / `class="tag tag-wip"`

当从 standalone HTML 转为 Hugo 内容页时，所有颜色必须从 dark palette 转换为 light palette。

## 样式

与架构图一致的暗色主题。两列网格布局，每格一张 `class="card"` 内嵌 `<table>`。

## 状态标记

- `● 稳定` — 绿色 `#34d399`，模块可正常运行
- `○ 在建` — 黄色 `#fbbf24`，已搭建但未完善或未日常使用

## 表格结构

```html
<div class="card" style="padding:16px;">
  <div style="color:#22d3ee;font-weight:600;margin-bottom:8px;">📥 输入层</div>
  <table style="width:100%;border-collapse:collapse;font-size:10px;">
    <tr style="color:#64748b;">
      <td style="padding:2px 4px;">子模块名</td>
      <td style="padding:2px 4px;color:#34d399;">● 稳定</td>
      <td style="padding:2px 4px;color:#475569;">备注说明</td>
    </tr>
  </table>
</div>
```

## 布局

- 使用 `display:grid;grid-template-columns:1fr 1fr;gap:12px` 两列
- 编辑工作面跨两列：`grid-column:1/-1`
- 图例中加两行：已完成 ●（绿色） / 在建 ○（黄色）

## 适用场景

- 架构图/roadmap 需要展示各模块开发状态
- 项目展示页需要区分稳定/在建模块
