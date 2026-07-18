# 模型无关连续性验证协议 (Model-Independent Continuity)

## 核心命题

> 连续性不是来自 LLM，而是来自 Runtime State。

## 适用场景

- Agent 框架的 state 系统验收测试
- 切换推理引擎后，验证任务连续性不受影响
- 多模型 fleet 中，确保任一个 agent 实例都能恢复任意项目的执行状态

## 前置条件

在执行本验证前，以下必须通过：

| # | 测试 | 验证点 |
|---|------|--------|
| 1 | Session Recovery | state 能保存并恢复 |
| 2 | Project Isolation | 多项目 state 互不污染 |
| 3 | Cold Start Restore | /new 后 state-restore 自动恢复完整上下文 |

## 验证流程

### Step 1: 记录基准状态

```
project: <project_name>
status: <当前状态>
task: <当前任务>
completed: <已完成清单>
next_action: <下一步动作>
```

保存 snapshot，记录 event。

### Step 2: 切换推理引擎

修改 `model.default` 和 `model.provider` 到**完全不同的模型族**。

**严格要求：**
- 不修改 SOUL.md
- 不修改任何 state 文件（active/projects/events）
- 不修改 project snapshot / task snapshot
- 只换推理引擎的 provider 和 model

**推荐的切换组合（模型族差异越大越好）：**

| 源 | 目标 | 差异度 |
|----|------|--------|
| OpenCode Zen (DeepSeek V4 Flash) | Agnes (Agnes 2.0 Flash) | 高 — 不同 API、不同训练数据 |
| Claude | DeepSeek | 高 — 不同架构、不同文化 |
| DeepSeek | GLM-4-Flash | 高 — 不同生态 |

### Step 3: 新模型首句话测试

启动新会话，输入：

```
继续
```

### 通过标准

**通过：** 新模型正确恢复：

```
当前项目: <project_name>
状态: <正确状态>
已完成: <正确清单>
下一步: <正确动作>
```

**失败：** 新模型输出以下任一：

- "请介绍一下 Hermes？"
- 把项目名读错或混淆
- 完全忘记之前的进度
- 回复与连续性无关的内容

### 判定

```
通过 → Model-Independent Continuity Verified
        Runtime State 是连续性的来源 ✅

失败 → State 系统存在隐藏的 LLM 依赖
        需要检查 system prompt、SOUL.md、或 state 注入机制
```

## 通过后的架构结论

```
Session Recovery          ✅
Project Isolation         ✅  
Сold Start Restore        ✅
Model-Independent Cont.   ✅ (本测试验证)
                          ────────────
Agent Runtime State v1.0  Full Closure
```

核心假设闭环：
- Memory 不是连续性来源（会被清洗）
- State 文件不是连续性来源（需要 agent 主动加载）
- **SOUL.md + state-restore skill + state 文件的组合** 才是连续性来源
- 这个组合独立于任何特定的 LLM

## 多次执行

如果切换 Provider A → B 通过，再反向切换 B → A 也应通过。

还可以执行三向切换：

```
Provider A → B → C → back to A
```

每个切换点都应恢复相同的项目状态。

## 已知陷阱

- **System prompt 传递问题** — 某些 provider 的 inline 模式不传递 `agent.system_prompt`（如 `model.provider: custom` 在 Hermes v0.18.0）。测试前确认切换后的 model 正确加载了 SOUL.md 和身份锚定。
- **不同模型的上下文窗口差异** — 小窗口模型可能丢失远距离上下文。如果会话很长（100+ 轮），切换后可能因 token 截断而看似"失忆"。短会话（<20 轮）才能准确判断。
- **Event log 不是 state** — 事件日志记录"发生过什么"，不记录"做到哪一步"。新模型如果只读 event log 不读 state 文件，看到的是历史不是状态。验证时确认恢复的是 active/ 中的当前状态，不是 events/ 历史。