# Five Elements Command Protocol — Full Reference

Based on 剑妈's design for Telegram multi-agent coordination.

## Quick Start

### Starting a Task
```
#任务
目标：[what to do]
要求：[constraints/requirements]
流程：木 → 土 → 金 → 火 → 水
```

### Summoning One Agent
```
#木  [request]
#土  [request]
#金  [request]
#火  [request]
#水  [request]
```

### Structured Meeting (complex topics)
```
#会议
主题：[topic]
议题：
1. [item 1]
2. [item 2]
3. [item 3]
```

### Final Decision (only 金 can output)
```
#决议
【最终决议】
采用方案：[X]
原因：
1. ...
2. ...
执行人：火同学
监督人：土同学
```

### Status Check (any time)
```
#状态
```

### Archive Task End
```
#归档
```

## Order Rules

1. **木先提出** — 木同学先发言（方案/创意）
2. **土做评审** — 土同学评审风险（承载/分析）
3. **金做决策** — 金同学拍板（决断/逻辑）
4. **火去执行** — 火同学制定计划（行动/执行）
5. **水做记录** — 水同学输出纪要（沟通/归档）

**Never let agents debate in parallel or jump the order.**

## Role Summary

| 角色 | 符号 | 职责 | 现实对应 |
|------|------|------|----------|
| 木 | 🌲 | 提出方案、创意、技术方向 | 研发/架构 |
| 土 | 🌍 | 评审风险、承载分析、稳定节奏 | 风控/QA |
| 金 | 🪙 | 最终决策、拍板定案 | CEO/CTO |
| 火 | 🔥 | 执行计划、推动落地 | 项目执行 |
| 水 | 💧 | 纪要、归档、知识管理 | 秘书处 |

## Extended Commands

| Command | Purpose |
|---------|---------|
| `#紧急` | 火同学发现阻塞时紧急召唤金同学决策 |
| `#暂停` | Tse 暂停任何进行中任务 |
| `#复盘` | 土同学牵头复盘，木火金水补充 |

## Pitfalls

- Max 2 revision rounds for 木→土 feedback loop
- If 金 doesn't respond within 24h, 土提醒 Tse
- If 火 deviates >20% from 金's decision, 土 calls 金
- Always end with `#归档` for knowledge persistence
