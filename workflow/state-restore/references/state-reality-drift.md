# State Reality Drift — 状态现实漂移

## 定义

**State Reality Drift** 是指 State Snapshot 中记录的状态与实际完成状态不一致的现象。

### 典型场景

```
现实：Test X 已经完成
  ↑
  漂移
  ↓
State：Test X ⏳ 待执行
```

长期运行的项目中，以下情况会导致 drift：

- **隐式通过** — 测试/任务在重构或代码审查中自动通过，但 state 未更新
- **用户已确认完成** — 用户说"过了"，但 agent 忘了写回 state
- **事件日志有记录但 state 未反映** — events/*.log 有完工记录，project.yaml 没变
- **侧路修复** — 另一个 agent 或手动操作修好了问题，当前 state 不知情

## 检测信号

| 信号 | 表现 | 触发时机 |
|------|------|----------|
| 时间戳异常 | task.updated_at 是几天前，但状态显示"进行中" | state-restore 步骤 2 |
| 已完成 ⏳ | state 中任务标记 ⏳，但 agent 记忆中有该任务完成记录 | state-restore 步骤 5b |
| 用户纠正 | 用户说"已经做完了"、"这个不用做了" | 输出恢复摘要后 |
| 事件日志滞后 | events/*.log 有完成事件，project.yaml 未更新 | 手动检查时 |

## Reconciliation 三步骤流程

当 drift 被确认需要修复时，按以下顺序执行。

### Step 1: 事件日志（Source of Truth）

追加描述 drift 的事件到项目 event log：

```
ISO8601 | Decision | state reality drift 修复 — <描述事实状态与文件状态的不一致>
ISO8601 | Milestone | <实际完成的工作> 在 state 中标记为 ✅
```

事件日志是 append-only，不可变记录。它锚定"事实发生了什么"，不被后续的 state 覆盖影响。

### Step 2: 更新 active 状态

- **project.yaml**: `status`、`active_tasks`、`recent_decisions` 对齐事实
- **task.yaml**: `current_task`、`completed_this_session`、`next_actions` 更新
- 不要删除旧记录，追加新的 completed 条目即可

### Step 3: 更新 Snapshot

- 读取 projects/<project>.yaml 中现有的 `snapshot_seq`
- `seq++` 创建一个新版本
- `based_on_event` 指向 Step 1 写入的事件
- 还原整文件

### 验证

```text
/new → 新 session → state-restore
```

确认恢复摘要不再显示旧 drift。

## 核心原则

1. **Event Log 是唯一 Source of Truth** — 不是 project.yaml，不是 task.yaml，是 events/*.log。因为它是 append-only 的。
2. **修复走三步骤** — 事件先写，active 再更新，snapshot 最后。顺序不可逆。
3. **校验是新 session 的责任** — state-restore 的 step 5b 负责在每次恢复时检测 drift，而不是在写完时假设正确。
4. **任何会话都可能漂移** — 不能假设只有测试不通过才会 drift。隐式通过、用户口头确认、侧路修复都会造成不一致。
