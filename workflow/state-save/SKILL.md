---
name: state-save
description: >-
disable-model-invocation: true
  会话结束时保存 Working State 到 ~/.hermes/state/。
  在用户说"保存状态"/"收工"/"/new" 之前或已知会话即将结束时执行。
version: 1.0
state_schema:
  global: 1.0
  project: 1.0
  task: 1.0
---

# State Save — 保存 Working State

## 硬性前置步骤：所有工作先归档

用户明确指令：**「所有工作完成之后都要写一个笔记备忘。」**

在保存状态之前，必须先完成：

- **每完成一个任务**（无论大小），即刻写 Obsidian 笔记到 `~/Documents/Obsidian Vault/土同学工作档案/`
- 修过的设备/配置 → 写进工作档案
- 学过的工具/软件 → 更新工具清单 `~/.hermes/tool-inventory.md`
- 解决的故障 → 写进相关 skill 的 `references/` 或直接更新 SKILL.md
- 新的技能/经验 → 创建或更新 skill
- 用户分享的链接/资源 → 截图存入工作档案

**不做归档就直接保存状态，等于做了白做。将来回头看什么都没有。**

### 笔记写作规范

用户明确要求笔记必须**纯中文书写**（除非是技术术语本身没有中文翻译）。

- ✅ 全中文叙述，包括操作过程摘要、用途说明、注意事项
- ✅ 技术术语（如 ADB、YAML、SSH）保持原文，不用强行翻译
- ❌ 不混用英文写正文（不写英文短段落/解释/过渡句）
- ❌ 不在中文句子中间插入半句英文描述
- ❌ 不中英文混合写同一个句子/段落
- 结构：用途 → 原理 → 实施方法 → 注意事项 → 验证 → 变更记录
- 文件命名：中文关键词 + `-` + 英文描述后缀

用户原话：**「混合各种语言 是不是说明你同时各个文化背景的人使用 然后记忆串了」**——统一用中文显示，其他看不懂。

## 触发条件

用户说以下任一指令时立即执行：
- "保存状态"
- "收工"
- 明确表示要结束会话
- 已知即将 /new

## 执行步骤

### 1. 读取当前 state 文件

```
global:  ~/.hermes/state/global.yaml
project: ~/.hermes/state/active/project.yaml
task:    ~/.hermes/state/active/task.yaml
events:  ~/.hermes/state/events/<project>.log
```

### 2. 更新 task.yaml

修改以下字段反映当前会话：

```yaml
current_task: <当前会话最后在做的事>
current_blocker: <如果还有阻塞>
completed_this_session:
  - <列表：本会话完成了什么>
next_actions:
  - <列表：下一步应该做什么>
open_questions:
  - <列表：未解决的问题>
```

### 3. 更新 project.yaml（如适用）

只在项目状态有变化时修改：

```yaml
status: <unchanged / progressed / blocked>
blockers: <当前阻塞>
recent_decisions: <本会话做出的决策>
pending_questions: <待确认问题>
resources: <资源状态变化>
```

### 4. 保存项目快照到 projects/

保存当前项目状态为可恢复快照。快照存储在 `projects/` 目录，作为 state-switch 的加载源。

```
cp ~/.hermes/state/active/project.yaml ~/.hermes/state/projects/<project-name-sanitized>.yaml
```

项目名取自 project.yaml 中 `project:` 字段，sanitize（小写、空格变连字符）。

注意：projects/ 下的文件是 **可恢复快照**，不是备份归档。每次保存都是覆盖更新，反映该项目的最新状态。

### 5. 追加事件到项目 event log

```bash
# 追加到项目专属事件日志
echo "ISO8601 | EventType | 简述" >> ~/.hermes/state/events/<project>.log

# 全局事件仍写 global.log
echo "ISO8601 | EventType | 简述" >> ~/.hermes/state/events/global.log
```

事件类型（Domain Event）：

```
Decision       — 做出了什么决定
Preference     — 用户表达了偏好
Correction     — 用户纠正了行为
Milestone      — 完成了重要节点
Failure        — 遇到了失败
Observation    — 重要观察
Hypothesis     — 提出的假设
TaskStarted    — 开始新任务
TaskCompleted  — 完成任务
StateSwitch    — 项目上下文切换
```

### 6. 告知用户

"状态已保存。下次会话输入 '恢复状态' 即可继续。"

## 注意

- 只保存 State，不要保存对话全文
- next_actions 不要超过 5 条
- project.yaml 只在有变化时才写，不要每轮都改
- event log 是 append-only，不要覆盖已有内容
- 项目切换通过 state-switch 脚本自动处理 snapshot-save/load

### State Reality Drift 预防

**关键原则：完成即更新。** 不要在 task 实际完成后才写入 state — 完成后立即更新三个文件中的对应条目。

**容易产生 drift 的场景：**
- **隐式完成** — 测试在验证过程中自然通过（如 Cold Start Recovery 在重构后自动成立），但 agent 只关心了重构本身，忘了标记测试通过
- **用户口头确认** — 用户说"过了"、"好了"，但 agent 没写回 state
- **侧路修复** — 另一个 agent 或手动操作修好了问题，当前 agent 不知情

**写入前自查：**
1. 今天实际完成了什么？（不是"计划完成什么"）
2. completed_this_session 是否包含了所有实际产出？
3. 当前标记为 ⏳ 的任务，是不是其实已经做完了？

如发现 drift 需要修复，参考 state-restore 的 `references/state-reality-drift.md`。

## 参考文档

State 生命周期架构原则（Snapshot ≠ Backup、三文件模型、snapshot 元数据）详见 state-restore 的参考文档：

- `skill_view(name='state-restore', file_path='references/state-lifecycle-model.md')`
- `skill_view(name='state-restore', file_path='references/state-reality-drift.md')` — drift 修复流程

## 与 multi-bot-todo 的关系

`state-save` 处理**单 bot 跨会话连续性**（我记得什么）。

**跨 bot 任务协调**（谁做什么）使用 hermes-multi-bot-todo 项目：
https://github.com/angelife/hermes-multi-bot-todo

两者互补，不替代。