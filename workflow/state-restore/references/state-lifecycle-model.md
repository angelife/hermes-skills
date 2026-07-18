# State 生命周期模型

## 核心原则：Snapshot ≠ Backup

### Backup（运维思维）
- 被动创建
- 保留历史版本
- 不参与恢复逻辑
- 用途：防误操作丢数据

### Snapshot（Runtime 思维）
- 主动生成
- 覆盖更新（反映每个项目最新状态）
- 是 Runtime 恢复的依据
- 用途：state-switch 的加载源

## 目录结构

```
~/.hermes/state/
├── global.yaml                    ← 跨项目偏好（永不被切换覆盖）
├── active/
│   ├── project.yaml               ← 当前激活的项目状态
│   └── task.yaml                  ← 当前任务执行上下文
├── projects/
│   └── <sanitized-name>.yaml      ← 每项目一个快照文件（含元数据）
├── events/
│   ├── global.log                 ← 跨项目事件
│   └── <sanitized-name>.log       ← 每项目事件隔离
└── state-switch                   ← snapshot-save → snapshot-load 脚本
```

## Snapshot 元数据

每个 `projects/<name>.yaml` 文件包含：

```
snapshot_version: 1               ← 格式版本（用于未来迁移）
snapshot_seq: <N>                  ← 快照序列号（单调递增）
created_at: "ISO8601"             ← 创建时间
based_on_event: <event_id>        ← 基于哪个事件生成的快照
```

用途：
- **snapshot_seq**：判断哪个快照最新（在切换或恢复时）
- **created_at**：时间线恢复
- **based_on_event**：追溯状态来源

## state-switch 流程

### 切出（Snapshot Save）
```
active/project.yaml
    │
    ▼
读取 project: 字段（项目名）
    │
    ▼
sanitize → 文件名（小写、空格变连字符）
    │
    ▼
读取旧快照 snapshot_seq，seq++ → 写新快照
    │
    ▼
projects/<sanitized-name>.yaml  ← 覆盖更新
    │
    ▼
events/<target>.log 追加 StateSwitch 事件
```

### 切入（Snapshot Load）
```
projects/<target>.yaml
    │
    ▼
读取元数据（seq, created_at, based_on_event）
    │
    ▼
剥离元数据头 → 写 active/project.yaml
    │
    ▼
重置 active/task.yaml（新项目上下文）
    │
    ▼
events/<project>.log 追加 StateSwitch 事件
```

## 关键约束

1. **global.yaml 不可被切换覆盖** — 跨项目偏好永不被 state-switch 或 state-save 修改
2. **快照覆盖更新** — 每次切出去都保存最新状态，不保留历史版本
3. **Task 状态重置** — 项目切换时 task.yaml 重置为空任务上下文，不继承上一个项目的执行进度
4. **Event 隔离** — 每个项目的事件写入自己的 `.log` 文件，global.log 只写跨项目事件

## 恢复优先级

state-restore 加载时：
1. `global.yaml` → 跨项目偏好
2. `active/project.yaml` → 当前项目状态
3. `active/task.yaml` → 当前任务
4. `projects/` 列表 → 多项目提示
