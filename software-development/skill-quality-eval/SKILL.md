---
name: skill-quality-eval
description: "Skill 质量评估与迭代循环。用 20 条测试查触发率，用 3-5 场景查输出质量，数据驱动改进。适用于：新建 skill 后的第一轮优化、用户反馈 skill 不准/该触发没触发/不该触发乱触发时。不适用于 skill 内容本身大的重构。"
disable-model-invocation: true
tags: [skills, evaluation, quality, testing, iteration]
related_skills: [hermes-agent-skill-authoring, diffusion-convergence]
---

# Skill 质量评估 (Skill Quality Eval)

数据驱动地评估和迭代 skill 质量，基于 skill-creator 方法论。

## 何时使用

- 新建 skill 后，需要验证 description 触发是否准确
- 用户反馈 "这个 skill 没触发" / "不该触发时乱触发"
- 修改了 description，需要验证修改效果
- 准备发布 skill 前的最后检查

## 触发率评估

### 方法

1. 生成 20 条测试查询（从 description + 实际使用场景衍生）：
   - 10 条 **应该触发**（覆盖各种合法触发场景）
   - 10 条 **不应该触发**（边缘案例 + 上下文接近但不应该触发的场景）
2. 用关键词代理或 LLM 判断每条是否触发
3. 统计 4 个维度

### 指标

| 维度 | 含义 | 改进方向 |
|------|------|----------|
| TP | 应该触发且触发 | ✅ |
| TN | 不该触发且未触发 | ✅ |
| FP | 不该触发但误触 | description 太宽泛，加边界条件 |
| FN | 应该触发但漏过 | description 漏关键词/场景 |

### 快速评估模板

```python
# 1. 从 skill 的 description 中提取关键词
keywords = ["词1", "词2", "词3", ...]
threshold = 2  # 命中多少关键词视为触发

# 2. 测试查询
should_trigger = [
    "触发场景1的描述",
    "触发场景2的描述",
    ...
]  # 10个
should_not = [
    "不该触发的场景",
    ...
]  # 10个

# 3. 评估
def fires(q):
    ql = q.lower()
    return sum(1 for kw in keywords if kw.lower() in ql) >= threshold

tp = sum(1 for q in should_trigger if fires(q))
fn = sum(1 for q in should_trigger if not fires(q))
tn = sum(1 for q in should_not if not fires(q))
fp = sum(1 for q in should_not if fires(q))

print(f"TP:{tp} TN:{tn} FP:{fp} FN:{fn}  Acc:{(tp+tn)/20*100:.0f}%")
if fn:
    print(f"漏掉:", [q for q in should_trigger if not fires(q)])
if fp:
    print(f"误触:", [q for q in should_not if fires(q)])
```

### 改进策略

- **FN 多**：description 末尾追加触发关键词（"触发词：X、Y、Z"）
- **FP 多**：description 加否定限定（"不要用于..."、"区别于..."）
- 每次改完重新跑评估，直到准确率 ≥ 90%

## 输出质量评估

### 方法

1. 准备 3-5 个真实场景
2. 对每个场景：对比有 Skill 和无 Skill 的输出
3. 按 SKILL.md 中的规则逐条检查遵守情况

### 检查清单

- [ ] 规则执行率：几条规则被遵守
- [ ] 输出结构：是否按模板/格式输出
- [ ] 边界覆盖：异常/边缘情况有处理
- [ ] 一致性：多次运行结果是否稳定

## 迭代循环

```
写/改 Skill → 跑 Eval → 看数据 → 改进 → 再跑 Eval
```

- 第一轮：聚焦触发率（拉到 90%+）
- 第二轮：聚焦输出质量（拉到稳定可靠）
- 后续轮次：回归测试，确保老场景不退化

## 注意事项

1. **关键词评估是 proxy**：真实 LLM 用语义匹配会更准/更差。主要用于快速迭代 description。
2. **数据驱动，不靠感觉**：每次修改前后都跑一次评估，看数字是否真的改善了。
3. **description 是第一杠杆**：触发率问题 90% 是 description 不够精确，不是 SKILL.md 正文写得不好。
4. **定期回归**：模型更新后可能影响触发行为，核心 skill 每月跑一次回归。
