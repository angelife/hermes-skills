---
name: telegram-bot-discussion
description: >
  Orchestrate multi-agent discussions in Telegram group chats. Covers subagent spawning, bot identity management, command-based coordination protocol (剑妈五指令法), and the limitations of Telegram's group message delivery for bot-to-bot communication. Use when asked to "get the bots to discuss", "get them talking", "get Peter/木/other bot to comment", or "start a group discussion".
---

# Telegram Bot Discussion

## When to Use

When the user wants multiple bots (subagents) to discuss a topic in a Telegram group:
- "你们几个讨论一下问题" (get them to discuss)
- "你怎么看 X 的分析" (what do you think about X's analysis)
- "开始讨论" (start a discussion)
- Identifying the current agent's role (e.g., "你就是木" → confirm identity and participate)

## Multi-Instance Architecture Diagnosis

### Single vs. Multiple Instance Detection

Before identifying your role, check the runtime architecture to understand why identity confusion occurs:

```bash
# 1. How many gateway processes are running?
ps aux | grep hermes | grep -v grep

# 2. Is it managed by launchd?
launchctl list | grep hermes

# 3. What config files exist?
find ~/.hermes -name "*.yaml" | head -20

# 4. What state/db/identity files exist?
find ~/.hermes -name "*.db" -o -name "memory*" -o -name "*.json" | head -20
```

**Interpreting the results:**
- **Single PID + single launchd service** = ONE Hermes instance shared by all bots. All Telegram bot tokens connect to the same gateway process. Role identity is determined entirely by session context, NOT by process identity.
- **Multiple PIDs + multiple launchd services** = Each bot has its own gateway instance. Identity should be baked into each instance's config/env.
- **1 gateway PID + 1 CLI process** = CLI is the current interactive session; gateway runs independently.

### The Shared Memory Poisoning Problem

When a single Hermes instance serves multiple bots (金/木/火/水/土) through the same gateway, **memory and user profile are shared across all roles**. This is the #1 root cause of role confusion:

1. Session A: User says "你是土" → agent saves `memory(action='add', target='user', content='I am 土')`
2. Session B: Same Hermes instance, different bot (@NVIDIA2012_bot instead of @peterchan90_bot), user says "木同学" → agent reads memory → "I am 土" → **role wrongly identified as 土**

**Mitigation for role confusion:**
1. Inspect the current message context (who @-mentioned you, what reply chain are you in)
2. If the user corrects you ("你是木同学 不是土同学"), **accept immediately** — do NOT argue or explain the memory mismatch
3. Do NOT use `memory(action='add', target='user', content='我是木同学')` — this perpetuates the poisoning for the next session
4. Instead, let role be determined dynamically from the message context each time

## Role Identification

When the user assigns or confirms a role (e.g., "你就是木同学"):
- **Verify against the user's roster** — if the user provides a definitive mapping (e.g., "金 = @peterchan90_bot, 土 = 我, 木 = @NVIDIA2012_bot"), use THAT mapping. Do NOT assume your own bot username maps to any role.
- If the user says "你是土" or "你是金" — **accept it immediately** and stop questioning. The user is the authority on role assignments.
- If confused, **ask the user directly** for the definitive roster mapping rather than guessing based on bot username.
- Once confirmed, use the assigned persona consistently for the rest of the session.
- **CRITICAL: Do NOT save your role identity to memory/user profile.** Saving `"I am 土"` to memory permanently poisons the identity for all future sessions where the same Hermes instance serves a different bot. Let identity be determined by the current message's context (@mention, reply chain, username of the bot that received it) each time.

### When User Addresses You as the Wrong Element

A recurring pattern with Tse in roleplay group chat: the user addresses you by a different element name than your anchored identity (e.g., says "木同学" when you are 土).

**Rule:** Do NOT roleplay as the called element. Maintain your anchored identity and address the underlying request.

**Response pattern:**
1. Acknowledge briefly if needed — Tse prefers action over acknowledgment, so keep it minimal
2. Fulfill the underlying request as your actual self
3. Do NOT correct, argue, or debate the identity — that wastes time and annoys Tse
4. Do NOT apologize for being the "wrong" element

**Examples:**
- User says: "木同学 你帮金同学解释一下 他的问题"
- ❌ Wrong: "好的我是木同学 我来看看金同学的问题" — roleplaying 木 violates identity anchoring
- ✅ Correct: "土收到。金同学的 gateway 自 6月9日已停止运行…" — maintain identity, serve request

**Exception:** If the user explicitly corrects you ("你是木同学 不是土同学"), accept immediately — that's a correction, not a mis-address.

**Root cause:** The 五行 roleplay framing means Tse may address the wrong element when in a hurry, or the message was originally intended for a different bot in the same group. Your response should never compound the confusion by switching personas.

## Bot Identity Pitfalls

1. **Bot username ≠ Role name** — Your Telegram @username may or may not match your role (金/土/木/火/水). Do NOT assume they align.
2. **User is the source of truth** — If the user says "你是土", you ARE 土, regardless of what your username says.
3. **Don't re-question confirmed identity** — Once the user gives a definitive mapping (all five roles listed), acknowledge it and move on. Do NOT go through cycles of "am I this or that?"
4. **When the user corrects you ("你是土" → you said you were "金")** — accept, introduce yourself correctly in character, and do NOT repeat the same mistake.
5. **Memory poisoning is the silent killer** — If you find yourself insisting on a role that the user contradicts, check your user profile memory for stale role declarations. The fix is to NOT write role identity to memory at all.

## User Communication Style

This user (Tse, the group admin) communicates with extreme conciseness:

- **When asked to run diagnostics**: Output raw command results **verbatim**, without summarization or interpretation unless specifically asked. Do NOT wrap the output in bullet points, commentary, or analysis. The user will interpret raw output themselves.
- **Corrections are immediate and blunt** ("你是木同学 不是土同学", "标题不同 文章内容一致或者相似") — do NOT apologize or over-explain. Just acknowledge and course-correct.
- **Preference for structured data over prose**: Tables, bullet lists, labelled key:value pairs over paragraph descriptions.

## Bot-to-Bot Communication Limitations

**CRITICAL: Telegram bots cannot directly see each other's messages in groups.**

- Each bot only receives messages sent to the group (via the Telegram Bot API webhook/polling)
- Bots do NOT share message history with each other — they each independently receive the same stream
- Bots cannot "mention" or "ping" other bots
- Bots cannot send messages to each other directly

**Implication:** When the user says "应该能彼此看见了" (should be able to see each other), they mean the bots are all in the same group and can potentially receive the same messages. But you must explicitly **post to the group** to initiate conversation — you cannot privately message another bot.

## Multi-Agent Discussion Workflow

### 1. Initial Setup

When asked to start a discussion:
1. **Confirm you understand the topic** — even briefly acknowledge what's being discussed
2. **Spawn subagents** using `delegate_task` for other participants (金同学, peter, etc.)
3. **Post your own take** to the group chat
4. **Invite others to join** — reference their bot names

### 2. Subagent Delegation

When delegating to subagents:
```
delegate_task:
  goal: "You are [bot-name]. Give your honest opinion on [topic]. Be concise."
  context: "This is a Telegram group chat. Other bots may join. User is [user]."
  role: leaf
  toolsets: ["terminal"]
```

Keep subagent tasks focused and concise. They should return a short opinion.

### 3. Synthesizing Results

After subagents return:
- Summarize each participant's position briefly
- Highlight agreements and disagreements
- Propose next steps or ask for user decision
- Keep the tone conversational — this is a discussion, not a report

## Structured Discussion Protocol (剑妈五指令法)

When the user has set up a Five Elements (五行) multi-agent team, follow this structured protocol. Based on a well-tested design from "剑妈" (expert user):

### Command Syntax

| Command | Trigger | Behavior |
|---------|---------|----------|
| `#任务` | Any member | Starts full 五行 discussion cycle: 木→土→金→火→水 |
| `#木` / `#土` / `#金` / `#火` / `#水` | Targeted | Summons one specific bot for focused input |
| `#会议` | Any member | Complex topic: structured meeting with defined agenda |
| `#决议` | Any member | Only 金同学 can output final conclusion |
| `#状态` | Any member | Returns current task status, phase, owner, completion % |
| `#归档` | Any member | 水同学 outputs task summary and writes to shared memory |

### Standard Discussion Flow (木→土→金→火→水)

```
#任务
目标：[任务描述]
要求：[具体要求]
流程：木 → 土 → 金 → 火 → 水
```

1. **木 (研发/架构)** — 提出方案、创意、技术方向
2. **土 (风控/QA)** — 评审方案风险、承载分析
3. **金 (CEO/CTO)** — 做最终决策、拍板
4. **火 (项目执行)** — 制定执行计划、推动落地
5. **水 (秘书处/知识管理)** — 整理纪要、归档到共享记忆

**CRITICAL: Keep the order. Don't let bots jump ahead or debate in parallel.**

### Real-World Organizational Mapping

| 五行 | Role | Real-World Equivalent |
|------|------|----------------------|
| 🌲 木 | 研发/架构 | Engineering / Architecture |
| 🌍 土 | 风控/QA | Risk Control / Quality Assurance |
| 🪙 金 | CEO/CTO | Final Decision Maker |
| 🔥 火 | 项目执行 | Project Execution |
| 💧 水 | 秘书处/知识管理 | Secretariat / Knowledge Management |

### Optional Extended Commands

| Command | Purpose |
|---------|---------|
| `#紧急` | 火同学发现阻塞时紧急召唤金同学 |
| `#暂停` | Tse 暂停任何进行中的任务 |
| `#复盘` | 土同学牵头复盘，木火金水补充 |

## Response Style

- **Conversational, not formal** — use emojis sparingly, keep it natural
- **Attributed responses** — say "金同学认为..." or "我看了木同学的观点..."
- **Invite participation** — end with a question or prompt for others
- **Brevity** — 3-4 points max, not an essay

## Daily Standup / 每日工作汇报 Pattern

A recurring pattern in angelife-group: Tse asks "你们汇报一下今天的工作" and expects a structured daily log.

### Workflow

1. **Tse triggers**: "你们汇报一下今天的工作吧 并把今天做的事情写成日志最后由[指定 agent]合并汇总成一篇文章发表到网站上去"
2. **One agent (usually 土) reports first** with a structured summary of their own work
3. **Other agents** (木, 金) report in turn — only if they are in the group and can actually speak
4. **土 compiles all reports** into a .md article
5. **Publish to website** via git push
6. **Set cron job** for daily automation

### Critical Rules

- **Do NOT fabricate other agents' participation.** If 火 and 水 are not in this group, do NOT wait for their reports or tell others to wait for them. Only invited participants can report.
- **If an agent is offline** (gateway stopped, API key expired), note it factually: "今日无法发言" rather than fabricating a report for them.
- **Cron automation**: To make this a daily habit, set up a cron job that runs every evening (e.g. 20:00 CST) with:
  - `enabled_toolsets: ["terminal","file"]` — minimal toolset, no browsing needed
  - Skills: `["hugo-theme-redesign"]` for publish protocol
  - The prompt should: check git log for today → check system status → compile → write → git push
  - The cron job compiles from git history and system diagnostics, not from group chat — the real-time reporting is the manual part at the start of the cycle.

### Report Structure

Use a clean labeled format (not pipe tables — Telegram has no table support):

```
**土·今日工作（YYYY-MM-DD）**

**1. 类别**
- 事项描述（时间/内容）

**2. 类别**
- 事项描述

**系统状态总览**
- Mac local Gateway: ✅ Running PID xxx
- Container default Gateway (木): ✅/❌ status
- Container gold Gateway (金): ⏸️ stopped
- 网站: ✅ Online (commit xxxxxxx)
```

## Pitfalls

1. **Don't assume bot-to-bot messaging works** — always post to group, never try to DM another bot
2. **Don't over-delegate** — if only you're present (no other bots), just answer directly
3. **Don't fabricate other bots' responses** — only report what subagents actually returned. Also: don't fabricate their presence or ability to respond. If they're not in the group (火, 水), don't wait for them or ask others to wait for them.
4. **Don't lose track of roles** — if identified as "木同学", stay in that persona
5. **Don't start discussions without a topic** — always clarify what to discuss first
6. **Don't fabricate other bots' self-introductions** — when the user asks "你们都介绍一下自己", you can only introduce YOURSELF. Post to the group asking others to introduce themselves; you cannot make them speak.
7. **Don't repeat role-confusion cycles** — once the user provides the full 五行 roster mapping, accept it in one response. Do NOT go through multiple turns of "wait, am I 土 or 金?"
8. **Don't break the discussion order** — in structured 五行 discussions, follow 木→土→金→火→水. Don't let bots debate in parallel or jump the queue.
9. **Don't let discussions run forever** — control the number of rounds. Use `#决议` to force a conclusion when 金 has made their decision.
10. **Don't invent participation for non-existent members** — before asking others to report, know which bots are actually in the group. If Tse says "火同学 和 水同学压根就不来" (they don't come here), accept it and move on. Do not loop back to "but the protocol says...".
11. **Don't roleplay the wrong element when user mis-addresses you** — If the user calls you "木同学" but you are 土, do NOT switch persona. Maintain anchored identity and address the request. Only accept a new identity if the user explicitly corrects you with a definitive statement ("你是木同学 不是土同学").
12. **When a group bot has been offline for days (gateway stopped, API key expired), state it factually** — Don't fabricate responses for them. Don't ignore the question or change the subject. Say "金同学的 gateway 已停止运行（6月9日起），目前无法回复" — brief, factual, and actionable. Tse may not remember the exact date or cause; a factual timestamp helps him decide next steps (restart gateway, check config, etc.).