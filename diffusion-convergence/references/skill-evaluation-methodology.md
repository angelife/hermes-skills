# Skill 评估方法论（Eval-Driven Improvement）

来源：群文章「如何训练 Skill 让它自进化」+ AI AgentTeam2026

## 两个核心指标

| 指标 | 含义 | 决定因素 |
|------|------|---------|
| 触发率 | AI 对"该不该用这个 Skill"的判断准确率 | description 字段写得好不好 |
| 输出质量 | 触发后 AI 按 Skill 干活的效果 | SKILL.md 正文规则写得好不好 |

## Eval 循环

```
写/改 Skill → 跑 Eval → 看数据 → 改进 → 再跑 Eval → ...
```

### 第 1 步：写初版
- description 以 "Use when" 或 "触发词：" 开头，明确什么时候用
- 正文写 3-5 条核心规则
- 给 1 个完整示例

### 第 2 步：跑触发率测试
生成 20 个模拟查询（10 个应该触发 + 10 个不应该触发），逐个测试 description 能否正确判断。

**Python 评估脚本模板：**
```python
keywords = ["触发词1", "触发词2", ...]
should_trigger = ["查询1", "查询2", ...]
should_not = ["查询1", "查询2", ...]

def fires(q):
    return sum(1 for kw in keywords if kw.lower() in q.lower()) >= 2

tp = sum(1 for q in should_trigger if fires(q))
tn = sum(1 for q in should_not if not fires(q))
fp = sum(1 for q in should_not if fires(q))
fn = sum(1 for q in should_trigger if not fires(q))
print(f"TP:{tp} TN:{tn} FP:{fp} FN:{fn}  Acc:{(tp+tn)/20*100:.0f}%")
```

### 第 3 步：看数据定位问题
| 问题 | 原因 | 修复 |
|------|------|------|
| 触发率低（< 85%） | description 太宽泛或太窄 | 增加/减少触发词，明确边界 |
| 误触发高 | description 边界模糊 | 加"NOT for"排除场景 |
| 输出质量差 | 规则太模糊 | 加具体示例、反例、检查清单 |

### 第 4 步：改进
- 根据 Eval 数据调整 description 和正文
- 触发率目标：> 95%（10/10 该触发 + 10/10 不该触发）
- 输出质量目标：3-5 个真实场景稳定输出

### 第 5 步：回归
- 每次改进后重新跑 Eval
- 项目在变、模型在变，Skill 也要跟着变
- 定期回归测试（每月或每季度）

## 注意事项
- 触发率用关键词模拟评估是近似值，实际 Hermes 用语义匹配更准确
- 输出质量评估需要人工判断，无法完全自动化
- 用户反馈是最好的训练数据 — 每次纠正都是一次训练机会
