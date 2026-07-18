# 机制锁死实战案例

## 案例 1：Memory 审计（2026-07-03）

完整记录见 `reporting-and-handover-style/references/memory-audit.md`

- **问题：** Memory 83%，无自动压缩机制
- **用户纠正：** 两条错误路线（人工检查、规则存 memory）都被否，最后走 cron job
- **落地：** cron job `memory-audit-observation` 每天 03:00 运行，观察模式 1-2 周后切自动

## 案例 2："这个项目"上下文偏差（2026-07-03）

- **问题：** 用户说"分析这个项目"，我跳到了 Angelife（因为 earlier 引用带偏）
- **用户纠正：** 直接说"不是。是 Hermes"
- **机制锁死修复：** 在 response-protocol pitfall #2 中写入"检查顺序：当前动作 → 最近话题 → 历史上下文"

## 案例 3：SOUL.md 身份锁定

- **问题：** Hermes 跨会话身份漂移
- **方案：** 身份放在 SOUL.md 中通过 startup 注入，不可被用户提示改写
- **类比到 memory：** 规则不能放在 memory 里——memory 本身会被压缩/删，规则应该放在外部代码路径

## 判断检查模板

设计任何方案后，跑这道检查：

1. 如果我忘记执行它，它会自己执行吗？ → 是机制
2. 如果 session memory 被清空，这条规则还在吗？ → 是机制
3. 如果换了模型/provider/终端，这条规则还在吗？ → 是机制（外部代码）

三项全"是" → 机制锁死成功。
任意项"否" → 至少部分行为规范。
