# Skill 蒸馏方法论（2026-07-13 实践）

## 原理

Skill 太胖 → 加载慢、关键规则被淹没、token 浪费。蒸馏目标：
- SKILL.md 只保留：触发条件 + 核心规则 + 关键约束
- 示例/案例/反例 → 移到 `references/` 目录
- 信息不丢，只是分层

## 本次蒸馏成果

| Skill | 原来 | 现在 | 省 |
|-------|------|------|----|
| moa-sourcing-rules | 676 行 / 42KB | ~140 行 / 5KB | -89% |
| hermes-provider-config | 1009 行 / 49KB | ~120 行 / 4KB | -88% |
| hermes-memory-providers | 862 行 / 37KB | ~90 行 / 3KB | -90% |

## 操作步骤

### 1. 通读全文，识别结构
```
前 20 行 → frontmatter + 触发条件
中间 → 核心规则（要保留）
后半 → 案例/反例/详细解释（可移走）
末尾 → 参考文件/附录
```

### 2. 分类内容
- **必须留 SKILL.md**：触发条件、核心规则、一级约束（每条约 1-3 行）
- **可移 references/**：详细案例、反例、对比表格、诊断流程、版本历史
- **可删**：空目录、已 supersede 的过时内容、跟自己不相关的

### 3. 重写 SKILL.md
- 用 table 浓缩规则（比 prose 省 50% 空间）
- 触发条件用 bullet list（一眼扫完）
- 每个 section 不超过 15 行
- 末尾留一行指针：`详细案例见 references/xxx.md`

### 4. 建 references/ 目录
```bash
mkdir -p <skill>/references/
# 把移出的内容分段写进独立的 .md 文件
```

### 5. 验证
- `wc -l SKILL.md` 确认从 ~800 降到 ~100
- 通读一遍确认核心规则没丢
- 检查 references/ 文件引用路径是否正确

## 合并原则

当多个 skill 内容重叠时：
- **四合一**：保留最完整的一个作为主体，其余 delete(AbsorbedInto)
- **吸收**：旧 skill → delete(absorbed_into=新skill)
- **改名**：直接 mv 目录 + patch frontmatter 中的 name

## 生命周期标签

| 标签 | 含义 | 操作 |
|------|------|------|
| `deprecated: true` | 已归档，不再更新 | frontmatter 加一行，description 前加 [ARCHIVED] |
| delete | 已吸收到别的 skill | `skill_manage delete absorbed_into=<target>` |
| 四合一 | 多个 skill 合并为一个 | 建 umbrella → 逐个 absorbed_into |
