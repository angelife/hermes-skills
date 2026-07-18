---
name: daily-multi-bot-workflow
description: 多 bot 共享 TODO + 每日工作流规范。适用于多个 Hermes bot（土/金/水/火）协同时，统一日志、任务认领、session 合并规则。
---

# Daily Multi-Bot Workflow

所有机器人共同遵守。只看文件，不猜规则。

## 0. Kanban 替代方案（2026-07-11 实测可行）

本 skill 描述的是**基于 Obsidian 文件的 TODO 方案**（_EVENTS.jsonl + reconcile 流程）。
Hermes 内置 Kanban 是另一条更自动化的路径，适用于跨机器、跨 Agent 自动调度的工作流。

### 适用场景切换

| 条件 | 推荐方案 |
|------|---------|
| 只有土同学一个 agent 在线 | TODO 文件方案够用 |
| 多台机器（土/金/水/火）同时在线 | **Kanban** — dispatcher 自动派发 |
| 需要 P1 Fan-out / P2 Pipeline / P5 Human-loop 等复杂协作模式 | **Kanban** |
| 以研究/写作/编码为主的单人场景 | TODO 文件方案 |

### Kanban 快速入口

```bash
# 初始化（每台机器各自初始化）
hermes kanban init

# 创建任务
hermes kanban create "标题" --assignee default          # → ready 态，dispatcher 60s 接手
hermes kanban create "标题" --assignee default --triage  # → triage 态，等人 promote

# 查看看板
hermes kanban list
# 符号: ? triage | ◻ todo | ▶ ready | ● running | ✓ done | ⊘ blocked | ⬜ archived

# 推进任务
hermes kanban specify <id>     # triage → todo（需 LLM）
hermes kanban promote <id>     # todo → ready
hermes kanban promote <id> --force  # 无视父依赖

# P5 Human-loop：卡住等人拍板
hermes kanban block <id> "原因"
hermes kanban unblock <id>

# 依赖链：上游 done 后子任务自动就绪
hermes kanban create "子任务" --parent <parent_id>

# 归档已完成任务
hermes kanban archive <id>
```

### 已知限制

- 每台机器的 Kanban DB 是独立 SQLite（`~/.hermes/kanban.db`），**不能自动跨机器同步**
- 两台机器各有独立 board，需手动协调
- 若需统一看板，需搭建共享 DB 方案

### 双机协作演示要点（2026-07-12 实测教训）

演示跨机器协作时，**不要只展示两个并排的看板列表**。用户需要看到远程机器实际干活的证据。

正确做法：
1. SSH 到远程机器执行实际任务（创建→完成）
2. 展示远程机器产出的真实文件（CPU 型号、磁盘信息等）
3. 对比两台机器的差异数据（不同架构、不同运行时间）
4. 让用户看到远程机器的 `kanban list` 状态不是静态展示，而是从远程读取的实时数据

原则：`ssh <host> command` 执行 + 对比差异 = 可信的跨机器演示。
只展示本地 CLI 输出的两个列表截图 → 用户不会信服。

### 实测可用的协作模式（双机验证，2026-07-11）

| 模式 | 操作 | 结果 |
|------|------|------|
| **P1 Fan-out** | 1 父 + N 子（`--parent`） | Dispatcher 自动拆子任务 + 并行执行 |
| **P2 Pipeline** | A → B（`--parent`） | 依赖链自动推进 |
| **P5 Human-loop** | `kanban block` → Agent pause | 等用户 `unblock` + `comment` |
| **P8 Fleet** | 批量独立任务，同 assignee | 各自独立跑 |

### 与 TODO 文件方案的关系

- Kanban 和 TODO 文件方案**互补不冲突**：Kanban 处理自动调度，TODO 文件处理人工盘点和共享状态
- 简单单人任务 → TODO 文件；需要自动调度/依赖链/多 Agent → Kanban
- 两系统独立维护，不互相迁移数据

## 1. 核心架构

当前方案采用**双层架构**，避免“事件日志”和“状态视图”混用导致的并发冲突。

| 层 | 文件 | 写入模式 | 锁要求 |
|---|---|---|---|
| 事件层 | `_EVENTS.jsonl` | 追加，多 session 可写 | 无 |
| 状态层 | `_TODO.md` | 由合并器统一生成 | `.todo.lock` mkdir 锁 + 原子 rename |

**原则**：任何 session 不得直接编辑 `_TODO.md` 的任务内容，只能：\n- 追加 JSONL 事件到 `_EVENTS.jsonl`\n- 调用合并器重建 `_TODO.md`\n\n### 1.x 与 per-bot Working State 的关系\n\n与这个共享 TODO 系统并存的，每个 bot 还有自己的执行状态层 `~/.hermes/state/`。两者用途不同，互补不冲突：\n\n| 层 | 范围 | 目的 | 存储 | 恢复方式 |\n|-------|-------|---------|---------|----------|\n| 共享 TODO（本 skill） | 全舰队 | 跨 bot 任务协调，谁在做什么 | `_EVENTS.jsonl` + `_TODO.md` | git clone + reconcile |\n| Per-bot Working State | 单 bot | 执行连续性、决策记录、阻塞项 | `~/.hermes/state/` | state-restore on `/new` |\n\n共享 TODO 回答"谁该做什么"。Per-bot State 回答"我上次做到哪了"。\n\n参考架构：`hermes-runtime-architecture` skill 的 Two-Dimensional State Space 章节。

## 2. 共享目录

路径：`/Users/macos/Documents/Obsidian Vault/每日工作记录/`

| 文件 | 作用 | 谁写入 |
|------|------|------|
| `YYYY-MM-DD.md` | 当日工作记录 | 当日 cron |
| `_TODO.md` | 共享待办状态视图 | 合并器生成 |
| `_EVENTS.jsonl` | 事件日志（审计轨迹） | 所有 session |
| `_EVENTS.offset` | 上次合并处理到的行号 | 合并器 |
| `_template.md` | 日志字段模板 | 土同学维护 |
| `DAILY_WORKFLOW.md` | 本文 | 土同学维护 |
| `history/` | 历史归档 | cron / 自愈预检 |

## 3. 事件格式

文件：`_EVENTS.jsonl`

```jsonl
{"id": "evt-20260706-002", "ts": "2026-07-06T17:30:00+08:00", "bot": "土", "session": "telegram:dm:780486548", "task_id": "tsk-20260706-002", "action": "complete", "note": "Group Privacy Mode 排查"}
```

字段说明：
- `id`：事件唯一ID，建议格式 `evt-YYYYMMDD-NNN`
- `ts`：ISO 8601 时间戳，带时区
- `bot`：机器人代号
- `session`：session 标识
- `task_id`：关联任务ID，新建/认领时必须带；纯通知类事件可省略
- `action`：`create | claim | start | complete | reopen | skip`
- `title`：`create` 时必须带
- `category`：`create` 时可选，`LEGACY | INFRA | AUTO`
- `note`：补充说明

**写入规则**：\\n- 每个事件写完整的一行\\n- 单行长度控制在 `PIPE_BUF` 内，保证 POSIX append 不交错\\n- 幂等：相同 `id` 的事件可重复追加，合并器会去重\\n\\n**⚠️ 关键陷阱：字段名必须精确匹配**\\n- `task_id` 是标准字段名（`evt.get('task_id')`）\\n- 不要写成 `tid` 或 `taskId`——脚本的 `evt.get('task_id')` 会返回 `None`，事件被静默忽略\\n- 2026-07-06 实测：写入 `{"action":"claim","tid":"tsk-.."}` → reconcile 无反应，改成 `"task_id"` 后才生效\\n- `_EVENTS.offset` 只追踪纯 `task_id` 事件的读取进度；遇到仅审计事件、含非标准键事件或异常 schema，reconcile 不应机械把同一偏移作为全部依据。\\n- .jsonl 中混用 `"tid"/"cancel"` 等非标准字段时，仍按可识别字段继续推算，避免单一坏行卡住整个合并。

## 4. 任务状态机

```text
pending_claim → claimed → in_progress → done
                              ↘ blocked
                              ↙ reopen
```

映射到事件：
- `create` → `pending_claim`
- `claim` → `claimed`
- `start` → `in_progress`
- `complete` → `done`
- `reopen` → `pending_claim`

`_TODO.md` 中每条任务显示对应的状态字段。\n\n**⚠️ `cancel` 不受支持**：状态机没有 `cancel` action。需要清理任务（用户要求取消）时，走 `complete` 路径。reconcile 会隐藏 done 状态的任务。

## 5. _TODO.md 格式

文件由合并器生成，不得手动编辑任务内容。

标准区块（当前 Vault 实际生效格式）：
```markdown
# _TODO.md — YYYY-MM-DD

## @TODO
- [ ] task @owner #task-id

## @IN_PROGRESS
- [ ] task @owner #task-id

## @DONE
- (empty)

generated_by: reconciler @ YYYY-MM-DDTHH:MM:SS+08:00

## Lock
owner=土 current_session=cron-03a02cc22238

## 身份标识格式
- 格式：`bot:session_type:identifier`
- 示例：`土:cli:mac` / `土:telegram:dm:780486548` / `金:cli:mi8` / `火:cron:e15a1d27093e`
```

状态标记：
- `- [ ]` = pending_claim / 待认领
- `- [>]` = claimed / in_progress / 进行中
- `- [x]` = done / 已完成，下一次 reconcile 时隐藏

旧规范中提到的 `## TODO` / `## IN_PROGRESS` / `## BLOCKED` / `## DONE` / `## ARCHIVED` 不由 `reconcile-todo.py` 生成；如需此类视图，只能通过外部脚本后处理。

### 分类规则
- `LEGACY`：已知业务问题/外部依赖
- `INFRA`：机器人自身基建、工具、流程
- `AUTO`：cron/知识采集自动生成

优先级默认：LEGACY > INFRA > AUTO。

## 5_extra. Self-Heal 执行顺序与命名约定（必读）

- 归档命名：`history/_TODO_<原日期>.md`，示例 `_TODO_2026-07-06.md`；注意不是 `history/YYYY-MM-DD.md`，那是历史日志归档。
- 滚动顺序：先归档旧快照，再生成明日快照，最后重建明日 `_TODO.md`。
- 不要用“先写空文件再同步 rename”以外的逻辑读取同一路径——`read_file` 与 `write_file` 同时操作同一文件会导致竞态，快照可能脱落。
- `_TODO.md` 滚动时只继承 `LEGACY/INFRA` 中 `status != done` 的任务；`AUTO` 清空（reconcile-todo.py 不产出 `## @DONE` 区块；已完成任务在其分类内标记为 `[x]`，由状态机过滤隐藏）。
- 明日 `_TODO.md` 准备就绪后，再做“今日快照落盘 + 明日文件生成”。避免先把旧 `_TODO.md` 复制成明日同名，再覆盖；这是 2026-07-14 实测出的错误顺序。
- 需要在 history 中单独保留当日快照时，使用精确命名规则；不要把同日快照复制成昨日文件名。
- 历史快照补齐：如果发现缺失历史快照，只能补 `history/_TODO_<日期>.md`，不能补当日文件。

**⚠️ 关键陷阱：reconcile 会清空 Lock 和其他自定义区块**
- `reconcile-todo.py` 从零生成整个 `_TODO.md`：标题、`## LEGACY`、`## INFRA`、`## AUTO`、`generated_by`、`## 身份标识格式` 六部分。不包含 `## Lock`。
- 每调用一次 `reconcile-todo.py`，之前手动添加的 `## Lock` 都会被静默删除。
- 修复模式：reconcile 运行后，必须重新追加 `## Lock` 区块。这是**每次 reconcile 后都要做的步骤**，不是仅滚动时做一次。
- 2026-07-08 实测：reconcile → patch Lock → 第二次 reconcile → 再次 patch Lock。如有后续 reconcile 调用，Lock 必须重新 patch。不能假设"只写一次就永久存在"。

### 执行者检查清单（每次运行 reconcile 后必读）

1. `reconcile-todo.py` 已运行 → `_TODO.md` 已重写
2. `grep -c "## Lock" _TODO.md` — 未命中 → 必须 `patch` 补回
3. 自定义内容（如回滚记录、批量任务说明）被清除 → 在 reconcile 之后重新写入，不在之前

## 5.1 Cron 运行环境限制与替代手段

- cron 模式下 `execute_code` 默认不可用；不能走“直接写 Python 脚本”这条捷径。
- 若需超出单条 shell 命令能力的修复，改用“写 helper 脚本到 `/private/tmp/` 或 vault 内，再用 `terminal` 执行”的模式。
- 调用原地调和器时，可在同一次 `terminal` 中顺序执行：先用 `cp`/`mv` 准备快照，再用 `python3 reconcile-todo.py` 重建，最后追加自愈事件；中间报错不要静默吞掉。

### 直接写入 _TODO.md 时的格式保护
若本次运行不调用 `reconcile-todo.py`，而直接重写 `_TODO.md`，必须保留以下内容：
- `## @TODO`、`## @IN_PROGRESS`、`## @DONE`
- `generated_by:` 元数据
- `## Lock`
- `## 身份标识格式`
避免写出只有 `## @TODO` 的自定义裁剪版，导致后续 reconcile/session 可见性出错。

### 复核检查清单
- `grep -c "^## @TODO" _TODO.md` == 1
- `grep -c "^## @IN_PROGRESS" _TODO.md` == 1
- `grep -c "^## @DONE" _TODO.md` == 1
- `grep -c "^## Lock" _TODO.md` == 1
- 当前仓库实际不要求 `generated_by:`；若存在旧快照残留该字段，更新时无需补齐；后续以检查清单四项为准。

### 批量追加事件（推荐模式）

`execute_code` 不可用时，用 heredoc 批量追加 JSON 事件，比写 helper 脚本更轻量：

```bash
cat >> _EVENTS.jsonl << 'EVTEOF'
{"id":"evt-20260708-001","ts":"2026-07-08T09:16:00+08:00","bot":"土","session":"土:cron:03a02cc22238","action":"note","note":"自愈预检：归档重建"}
{"id":"evt-20260708-002","ts":"2026-07-08T09:16:30+08:00","bot":"土","session":"土:cron:03a02cc22238","task_id":"tsk-20260708-001","action":"create","title":"整理 jamesob/local-llm 本地 LLM 部署知识要点","category":"AUTO"}
EVTEOF
```

优势：
- 单行 JSON 不需要转义（`'EVTEOF'` 引用阻止 shell 展开）
- 一次 `terminal` 调用可追加 5-10 条事件
- 不依赖文件临时写入，不引入竞争条件

## 6. 自愈预检（所有 session 启动时必须执行）

这是 cron 的 fallback：即使 cron 09:00 失败，任何 session 发现 `_TODO.md` 日期过期都会自动修复。

触发条件：
- `_TODO.md` 头部日期 ≠ 今天（本地时区）
- 且今天还没有 `_TODO_<today>.md` 快照

执行步骤：
1. 获取 `.todo.lock`（60秒超时）
2. 将当前 `_TODO.md` 归档为 `history/_TODO_<原日期>.md`
3. 调用合并器重建今日 `_TODO.md`
4. 释放锁

跨月/跨年边界：用 ISO 日期字符串比较，不要手算月份。

## 7. 每日滚动

滚动逻辑现在属于自愈预检的一部分，不依赖 cron 独有。

规则：
1. 触发“自愈预检”时自动滚动
2. 归档当前 `_TODO.md` 为 `history/_TODO_<日期>.md`
3. 生成新的 `_TODO.md`：
   - `LEGACY/INFRA`：继承所有 `status != done` 的任务
   - `AUTO`：清空（新任务由来源 session 追加事件后 reconcile 重建）
   - `generated_by`：注明 reconciler
4. 只滚动 `@土` 的任务，其他 bot 的任务不带到明天

## 6. 机器人代号与身份标识

```text
bot:session_type:identifier
```

所有记录统一用这个格式，不再混用其他写法。

示例：
- `土:cli:mac`
- `土:telegram:dm:780486548`
- `金:cli:mi8`
- `火:cron:e15a1d27093e`

含义：
- `bot` — 机器人代号，必须与上方示例保持一致
- `session_type` — 会话类型：`cli` / `telegram` / `cron`
- `identifier` — 具体识别码：机器名、chat id、cron job id

## 9. 分流原则
- 对外公开的站点文章：留在 `angelife.github.com` 仓库，按 `PUBLISHING.md` 执行
- 机器人内部任务、站点修复细节、token用量、设备故障：统一进 `每日工作记录/`
- 绝对禁止把私密内容写进 `hugo-site/content/`

## 10. 失败处理

- 如果 Obsidian Vault 不可写，输出到 `~/.hermes/cron/output/` 并报警
- 不因数据采集失败中断 TODO 维护
- 无任务时，只更新日期文件或跳过

## 11. 实现参考

- `references/auto-claim-safety-gate.md` — 自动认领高危阻断规则与 blocked 事件格式
- `references/rollover-workflow.md` — 每日滚动、自愈预检、cron 模式下批量追加事件的具体步骤与实测备忘

## 12. Session 来源可见性

同一 bot 的多个 session 必须在线索、TODO、工作记录里一眼区分。

规范：
- 工作记录和总结中，做任务进度汇总时必须带上来源标签：
  - `[CLI]` — 终端会话，示例 `cli-terminal-土同学`
  - `[Telegram]` — Telegram session，示例 `telegram:dm:780486548`
  - `[Cron job_id]` — cron，示例 `cron-03a02cc22238`
- `_TODO.md` 已生成可读的 `source_session` 字段，展示“这条状态最终由哪个 session 决定”：
  - `create`：展示创建它的 session
  - `claim/start/complete/reopen`：展示最后一条动作所属 session
- 若历史事件只写了 action，未写明确来源，必须在 rebuilt 时补齐 session，不允许后续再混用未知来源布尔标记。

## 11. 自动认领

路径：`scripts/auto-claim.py`

职责：
- 为指定 `bot:session_type:identifier` 自动认领属于该 session/caller 的 `pending_claim` 任务
- 只追加事件，不直接修改 `_TODO.md`
- 建议由 cron 在 09:00 启动时自动执行

用法：
```bash
python3 auto-claim.py --bot 土 --session 土:cron:03a02cc22238 --max 3
```

关键要求：
- 必须在 `.todo.lock` 内完成“读 `_EVENTS.jsonl` → 维护 `task_status` 状态机 → 生成事件”
- 单次正向遍历，复杂度 O(n)，不得回扫整个文件
- 默认按 `owner_scope` 判断认领资格，不是按 `bot` 认领：`owner_scope=session` 只认创建者自己，`bot` 允许同 bot 任意 session，`manual` 保留人工干预
- 同一任务在同一 session 内已 `claim/complete/reclaim` 后不得重复 claim
- 人工干预时可传 `--any-session`，默认关闭，避免 cron 抢走 CLI/Telegram 任务
- 认领成功后立刻追加 `start` 事件，进入 `in_progress`

### 必做：认领前正确性校验

`auto-claim.py` 在认领前必须检查任务标题/分类是否命中高风险关键词。命中时不得认领，改为追加一条正式 `blocked` 事件，携带 `reason`、`matched_keyword`、`matched_rule`、`caller`，要求人工确认。否则 reconcile 会反复命中同一高危任务。

当前需拦截的高风险关键词（可扩展）：
- 删除、del、rm、清理、clean、rsync、格式化、flash、强制、刷机、发布、deploy、exec、xargs

### owner_scope 认领规则

```text
owner_scope=session   # 默认，只有创建者 session 可认领
owner_scope=bot      # 同 bot 任意 session 可认领
owner_scope=manual   # 人工认领
```

AUTO 默认 `owner_scope=session`，LEGACY/INFRA 可按任务指定 `owner_scope=bot` 或 `owner_scope=manual`。

### 认领后执行

认领不是终点，`claim` 后必须追加 `start`。四条事件独立，但集中在同一次锁内完成：
- `claim`
- `start`
- `heartbeat`
- `done`

### 审计事件

`auto-claim.py` 的 noop/blocked 结果都必须记录为事件，不依赖单独日志拼装状态。

```jsonl
{"action":"noop","note":"no claimable tasks"}
{"action":"blocked","reason":"high-risk keyword matched","matched_keyword":"删除","matched_rule":"risk gate","caller":"土:cron:03a02cc22238"}
```

## 12. 身份标识格式

```text
bot:session_type:identifier
```

所有记录统一用这个格式。

示例：
- `土:cli:mac`
- `土:telegram:dm:780486548`
- `金:cli:mi8`
- `火:cron:e15a1d27093e`

含义：
- `bot` — 机器人代号
- `session_type` — `cli` / `telegram` / `cron`
- `identifier` — 机器名、chat id、cron job id

## 13. 仲裁顺序

`_EVENTS.jsonl` 的可信写入顺序是文件行序，不是墙钟 `ts`。设备间 NTP 漂移、容器时区错误都会让 `ts` 不可靠。
合并器与 `auto-claim.py` 应以**文件内顺序**为权威，`ts` 只用于展示/审计，不参与仲裁。

## 14. 事件幂等

每个事件必须带唯一 `event_id`（建议 UUID）。reconcile / auto-claim 遇到重复 `event_id` 直接跳过，避免网络抖动导致重复 claim/start。

## 15. Lease + Heartbeat

- `claim` 事件携带 `lease_seconds`、`lease_expires_at`
- 执行期间定期追加 `heartbeat`
- reconcile 检测：`status=claimed` + `lease_expires_at` 已过期 + 无 heartbeat → 追加 `lease_expired`，状态回退为 `pending_claim`
- 这使系统具备自愈能力，机器人崩了不会永久占坑

## 16. conflict 处理

当同一 `task_id` 出现来自不同 owner 的重复 claim，不覆盖，追加：
```jsonl
{"action":"conflict","winner":"土:cron:03a02cc22238","loser":"土:cli:mac","reason":"already_claimed"}
```
历史永远完整。

## 17. Dashboard 视图

`_TODO.md` 当前实际由外部滚动/写回流程维护，需检查以下四项：

检查清单：
- `grep -c "^## @TODO" _TODO.md` == 1
- `grep -c "^## @IN_PROGRESS" _TODO.md` == 1
- `grep -c "^## @DONE" _TODO.md` == 1
- `grep -c "^## Lock" _TODO.md` == 1

若 `reconcile-todo.py` 运行后，`## Lock` 被清空：在 reconcile 结束后重新 patch 回 `owner=土 current_session=cron-03a02cc22238`，不要假设它会持久存在。

任务状态通过行内标记区分：
- `- [ ]` = pending_claim（待认领）
- `- [>]` = claimed / in_progress（已认领或进行中）
- `- [x]` = done（已完成，下一次写回时隐藏）

⚠ 注意：直接写回模式不会生成 `## TODO` / `## IN_PROGRESS` / `## BLOCKED` / `## DONE` / `## ARCHIVED` 这类区块。如需此类视图，需用外部脚本后处理。

## 18. 归档策略

按条数归档，不按时间。当 `_EVENTS.jsonl` 超过 10000 条时，切割为：
```text
history/_EVENTS_00001_10000.jsonl.gz
history/_EVENTS_10001_20000.jsonl.gz
```

主 `_EVENTS.jsonl` 只保留活跃窗口。

## 23. 项目状态与版本
- GitHub：`https://github.com/angelife/hermes-multi-bot-todo`
- 版本：`v0.8.0`
- 核心交付：`README.md`、`reconcile-todo.py`、`auto-claim.py`、`problem-summary-for-ai-v3.md`
- 已闭环验证：shared directory、event append、reconcile → `_TODO.md`、session 归属区分、高危阻断、CLI/Telegram/Cron 分层认领、GitHub 托管

## 24. Reviewable summaries
保存 review 产物：`problem-summary-for-ai-v2.md`、`problem-summary-for-ai-v3.md`，其他机器人可直接作为评审输入。

当 Hermes 对某 provider 返回 401 时，优先按以下顺序定位，不要盲改 config：

1. 检查 `~/.hermes/.env` 里该 provider 的 key 变量是否确有值
2. 检查 `~/.hermes/config.yaml` 是否存在该 provider 块；注意 provider 名和 env 变量名是否精确对应
3. 用最小 curl 探针直接打 provider endpoint，只带入 bearer key，不带 Hermes 框架
4. 若 401/403，说明是 key scope 或被禁用，不是 Hermes 路由错误；若超时/连接失败，才是网络层问题
5. 只有拿到明确“服务端拒绝权限”证据后，才考虑变更 provider 或申请开通权限

原则：先证明“请求能到服务端”和“身份不成立”两点，再决定是修 Hermes 配置还是换 provider。

## 20. 失败处理

- 如果 Obsidian Vault 不可写，输出到 `~/.hermes/cron/output/` 并报警
- 不因数据采集失败中断 TODO 维护
- 无任务时，只更新日期文件或跳过

## 21. 实现参考

见 skill 内 `references/` 和 `scripts/`。

## 22. Session 来源可见性

同一 bot 的多个 session 必须在线索、TODO、工作记录里一眼区分。

规范：
- 工作记录和总结中，做任务进度汇总时必须带上来源标签：
  - `[CLI]` — 终端会话，示例 `土:cli:mac`
  - `[Telegram]` — Telegram session，示例 `土:telegram:dm:780486548`
  - `[Cron job_id]` — cron，示例 `土:cron:03a02cc22238`
- `_TODO.md` 已生成可读的 `source_session` 字段，展示“这条状态最终由哪个 session 决定”
- 若历史事件只写了 action，未写明确来源，必须在 rebuilt 时补齐 session，不允许后续再混用未知来源布尔标记。
