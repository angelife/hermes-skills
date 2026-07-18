# 2026-07-18 Complete MEMORY.md Rewrite Event

## 摘要
Day 4→Day 5 之间（2026-07-16→2026-07-18），MEMORY.md 被**完全重写**。22条旧条目全部删除，替换为22条新条目（SOUL.md 规则提炼 + 环境信息）。USER.md 同时从5条扩展至11条（+120%）。

## 关键数据

| 指标 | Day 4 (07-16) | Day 5 (07-18) | 变化 |
|------|---------------|---------------|------|
| MEMORY 条目 | 21 | 22 | +1 |
| MEMORY 字符 | 3679 | 3926 | +247 (+7%) |
| MEMORY 超载 | 67% | 78% | +11pp |
| USER 条目 | 5 | 11 | +6 (+120%) |
| USER 字符 | 1115 | 2082 | +967 (+87%) |
| USER 超载 | -19% | +51% | +70pp |

## 条目变化明细

### 删除的旧条目（22条）
- 用户对空输出/重复结果反感（264c）
- 中文写作准则：不强调无需强调的事（283c）→ 移动到 SOUL.md
- 强约束：安装/连接/免费类留证据（62c）
- OpenBridge 替代 CDP（75c）
- Kindle PW5 规格（101c）
- 外部链接不进 Hindsight（219c）
- aux.vision provider（109c）
- Doom Emacs 已就绪（128c）
- 模型优先顺序（181c）
- Style: hates trial-and-error（75c）
- 网络拓扑：IP段（219c）
- 先问 AI 核心指令（128c）
- 核心工作流：先查已有系统（173c）
- CORE PHILOSOPHY（109c）→ 保留为新版
- NIGHT WORK（155c）→ 保留为新版
- THREE-STRIKES（75c）→ 保留为新版
- MECHANISM OVER RULES（181c）→ 保留为新版
- KNOWLEDGE SYSTEM: NotebookLM（128c）→ 保留为新版
- WORKING CONDITIONS（120c）→ 保留为新版

### 新增条目（22条）
[1] 问模型必给细节 — [PREF] (172c)
[2] 完全授权直接推进 — [PREF] (168c)
[3] 问题解决层级 — [PROC] (109c)
[4] 有现成系统先用 — [PREF] (62c)
[5] CORE PHILOSOPHY — [PREF] (181c) ← 旧版精简保留
[6] NIGHT WORK — [PREF] (155c) ← 旧版保留
[7] THREE-STRIKES + 先问AI — [PROC] (128c) ← 合并
[8] MECHANISM OVER RULES — [PROC] (181c) ← 旧版保留
[9] WORKING CONDITIONS — [ENV] (120c) ← 旧版保留
[10] X同学定义 — [ENV] (75c) ← 新添加
[11] User核心哲学：慢就是快 — [PREF] (128c) ← 新添加
[12] User简介+WeChat DB key — [ENV] (219c) ← 新添加
[13] NLM中心制 — [PROC] (219c) ← 新添加
[14] 独立执行偏好 — [PREF] (128c) ← 新添加
[15] L3-L4自主性 — [PREF] (173c) ← 新添加
[16] ADB路径 — [ENV] (109c) ← 新添加
[17] 会话寿命 — [TECH] (128c) ← 新添加
[18] Kindle配置 — [ENV] (155c) ← 旧版精简
[19] 舰桥:28080 — [ENV] (155c) ← 新添加
[20] 中途打扰协议 — [PREF] (219c) ← 新添加
[21] Key test — [TECH] (128c) ← 新添加
[22] Mi8 WiFi — [ENV] (155c) ← 新添加

## SOUL.md Bleed 分析
新增的22条中有9条（[1]-[9]）是 SOUL.md 的直接规则提炼：
- `问模型必给细节` ← SOUL.md 行为基石部分
- `完全授权直接推进` ← SOUL.md 行为基石
- `问题解决层级` ← SOUL.md 行动原则
- `有现成系统先用` ← SOUL.md 行为基石
- `CORE PHILOSOPHY` ← SOUL.md 收敛原则
- `NIGHT WORK` ← SOUL.md 昼夜分工
- `THREE-STRIKES` ← SOUL.md 三次规则
- `MECHANISM OVER RULES` ← SOUL.md 强制前检
- `WORKING CONDITIONS` ← SOUL.md 隐含规则

这9条与系统提示中的 SOUL.md **完全重复**，是典型的 SOUL.md bleed 模式。若在 execution 阶段，这9条应优先删除，可释放约1400字符（MEMORY.md 从3926降至~2500，接近2200上限）。

## 后续观察
- 如果 MEMORY.md 再被重写一次，说明用户在主动测试不同的记忆存储策略
- USER.md 的扩展暗示用户对用户画像的精确度要求提高
- 超载问题需要 execution 阶段才能解决（day >= 7）
