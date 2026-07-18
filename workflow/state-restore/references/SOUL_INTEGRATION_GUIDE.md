# SOUL.md Integration Guide — Hermes Working State

## 目标

在任意 Hermes bot 的 `~/.hermes/SOUL.md` 中加入 Working State 集成指令，使 bot 在新会话中自动恢复工作上下文。

## 集成方式

在 SOUL.md 的身份锚定部分（通常位于文件末尾），添加以下内容：

```markdown
## Working State — 跨会话连续性

新会话启动时，立即加载 state-restore skill 检查 ~/.hermes/state/ 下的 Working State，
恢复上次的目标、进度和决策。会话结束前，确保调用 state-save skill 保存当前状态到 state 文件。
这是保持跨会话连续性的唯一机制。
```

## 验证步骤

1. 确保 setup.sh 已执行完毕（state 目录 + skills + state-switch 就绪）
2. 在 SOUL.md 中添加上述指令
3. 新会话输入 `继续`
4. 应输出如下格式的状态摘要：

```
── 状态恢复 ──────────────────────────────────

上次在做：
  <task.current_task>

进度：
  <completed_this_session 最近5条>

下一步：
  <next_actions>

阻塞：
  <current_blocker 或 无>

决策记录：
  <recent_decisions 最近3条>
─────────────────────────────────────────────
其他项目：
  <项目1>
  <项目2>
  输入 "切换 <项目名>" 可切换。
─────────────────────────────────────────────
```

5. 如果未触发恢复 → 检查 SOUL.md 中是否引用了 `state-restore` skill 名称，以及 skill 是否在 `~/.hermes/skills/workflow/state-restore/SKILL.md` 下。

## 故障排查

| 现象 | 可能原因 | 修复 |
|------|----------|------|
| 新会话没有恢复任何状态 | SOUL.md 未添加指令 | 参考上方集成方式 |
| 恢复但只有 global.yaml | active/project.yaml 不存在 | 手动初始化：`cp templates/active/project.yaml ~/.hermes/state/active/` |
| 恢复但项目名不对 | project.yaml 中的 `project:` 字段未更新 | 更新为实际项目名 |
| state-switch 找不到项目 | projects/ 下没有对应快照 | 先至少在项目中工作过一次并执行 state-save |

## 多 Bot 部署顺序

```
1. 土同学（Mac） — 已部署，主控
2. 火同学（其他机器） — setup.sh → SOUL.md 集成
3. 水同学（Mi6） — setup.sh → SOUL.md 集成
4. 金同学（Mi8） — setup.sh → SOUL.md 集成
```

每个 bot 独立运行自己的 state 文件。跨 bot 协调参见 hermes-multi-bot-todo 项目。