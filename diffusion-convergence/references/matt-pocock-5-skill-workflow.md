# Matt Pocock 的 5-Skill 开发流水线

来源：github.com/mattpocock/skills（160K Stars, 13.8K Forks）

## 5 个 Skill

| Skill | 功能 | 说明 |
|-------|------|------|
| /grill-with-docs | 需求澄清 | AI 阅读现有文件，追问模糊/矛盾/缺失的地方，直到产品逻辑和边界足够清楚 |
| /to-spec | 生成规格 | 把讨论整理成正式规格文档，包含功能目标、使用情境、边界条件、验收标准 |
| /to-tickets | 拆解任务 | 将规格拆成可执行的开发 Ticket，每张有明确范围与依赖关系 |
| /implement | 执行实现 | 根据 Ticket 写代码、改文件、跑测试，沿着已确认的规格逐步执行 |
| /code-review | 审查代码 | 检查程序代码、测试覆盖、潜在错误、规格落差 |

## 与扩散收敛法的关系

扩散收敛法 = 第 1-2 步（grill→spec）的精炼版本。Matt Pocock 在此基础上延伸了 tickets→implement→review 的全链路。

## 可借鉴的点

1. **分阶段锁死** — 每步输出是下一步的输入，不跳步
2. **规格先行** — 写代码前必须有用户确认的正式规格
3. **Ticket 粒度** — 单张 Ticket 不自太大，每个有独立依赖和范围
4. **Review 独立** — 实现和审查由不同流程执行，避免盲区
