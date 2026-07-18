---
name: tool-relevance-evaluation
description: "Evaluate third-party AI tools, frameworks, and articles against the user's personal infrastructure — Hermes agent fleet, Hindsight shared memory, network topology, and preferences. Give direct useful/useless verdict first, not theoretical possibilities."
category: meta
---

# Tool/Article Relevance Evaluation

> **Trigger**: User sends a link (WeChat article, GitHub repo, blog post) and asks some variant of "这个有用么" or "看看这个".
> **Core rule**: Answer for THIS user's stack, not generic AI capability. Direct verdict first, then brief reasoning.

## Methodology

### Step 1: Extract
- Use `web_extract` to get the content
- Identify: what problem does it solve? What's the core mechanism?

### Step 2: Map Against User's Stack

Ask in order:

5. **Stack match**: Does this work WITH or REPLACE the user's existing tools?
   - Hermes Agent (土/金/水/火 fleet)
   - Hindsight shared memory (192.168.1.8:8888)
   - Kanban (local SQLite, per-machine)
   - Existing cron jobs + Python scripts
   - China GFW environment (SOCKS5 proxy)

6. **Native capability check (mandatory)**: Before proposing to install a new system,
   check if Hermes already has a native adapter/plugin/channel for that capability.
   Hermes supports 15+ messaging platforms (Telegram, WhatsApp, Signal, WeChat/Weixin,
   WeCom, DingTalk, Feishu, QQ, LINE, etc.), each with documented setup at
   `docs/user-guide/messaging/`. Running dual Agent frameworks creates
   config/complexity debt — always prefer the Hermes-native path first.
   Cases where running a separate system is justified: Hermes lacks the capability,
   or the external system provides a significantly better implementation that cannot
   be replicated via SDK/API.

- **Overlap resolution**: If the tool overlaps with Hermes in most areas but has ONE unique capability Hermes lacks, extract that capability (plugin/config/reference) rather than running dual systems. Example: CowAgent → only WeChat channel was needed, not the whole Agent framework.

3. **Deployment scope**: Can it run on ALL fleet agents (Mac + Android Termux chroots) or only some?

4. **Network reality**: Does it need public internet, or works behind GFW?

### Step 3: Recommend Next Action

After the verdict, the user expects a clear next step:
- "装一个试试看" → install + configure right now
- "回家再试" → prepare package, leave instructions
- "不值得装" → explain why not
- The default should be installing and testing — the user is action-oriented

### Step 4: Demonstrate — Prove It Works

After installing/configuring, the user expects to **see** the tool working, not just be told:

1. **Run a real action** on the tool's target system
2. **Show concrete output** — terminal output, API responses, produced files
3. **Cross-machine proof** — if the tool spans multiple agents, show each machine's participation with verifiable evidence (different CPUs, different uptimes, produced artifacts)
4. **User interaction** — let the user trigger actions (`hermes kanban list`, `curl /health`) to verify themselves

The user will call out if they can't see the proof ("我没看到火同学参与"). Always include concrete, machine-readable evidence.

### Step 5: Deliver Verdict

### 核心原则：不吹

- 说工具能省什么，别吹到"够用"级别。省 token 就说省 token，不说是"解决 token 问题"
- **「有用」跟「够用」是两回事。** 10-20% 的优化不叫格局改变
- 用户会直接反问「帮助也是极其有限对吧」——说明你吹过了
- 诚实量化：说「省 10-20%」，不说「大幅提升」
- 下结论前先反问自己：这个改变能提升用户说的痛点吗？如果不能，就是改善不是解决

### 先查已有基础设施，不要另起炉灶

在推荐/构建任何新系统前，先问：
1. **现有系统能不能做？** Hindsight、Federation Hub、Hermes 本身是否已有此能力？
2. **已经有 skill 覆盖了吗？** `skill_view` 或 `skills_list` 查一下
3. **用户明明已有方案，你是不是忽略了？** 用户说「怎么变成XX了 不是YY么」= 犯了预设缺失

⚠️ **关键陷阱：不要凭印象否定现有系统。** 如果新工具可能 REPLACE 现有组件，先 `hindsight_recall` + `session_search` 确认现有组件的实际设计范围——不要靠记忆做假设。用户已反复纠正此行为。hindsight 从一开始就是为多 bot 共享记忆设计的，不是单机本地记忆。

已有基础设施清单：Hindsight(共享记忆, 多 bot 指向同一 server), Federation Hub(28081, 任务协调), Kanban(本地任务), Hermes Gateway(通信), FAL(生图), Minimax M3(多模态), rtk-hermes(token压缩)

### 设备命名纪律

- **不装 Hermes Agent = 不配叫同学。** 一台机器只跑服务（如 OpenViking server、数据库、反向代理）不叫金/木/水/火/土。只有装了 Hermes Agent、接入了联邦舰队的，才能得代号。
- 命名前确认该设备有独立的 agent 进程（gateway 或 runtime），能接收指令、返回结果、参与调度。
- 纯服务端 → 叫「XX机」「XX盒」，不是同学。


### 文章链接不属于记忆

- 微信群里的外部文章链接 → **不进 Hindsight，不进任何记忆系统**
- Hindsight 是为个人经验/观察/知识沉淀设计的，不是外部链接仓库
- 正确做法：挑出跟用户项目相关的文章，问「要不要看看」，用户要看才读
- 读后有价值的洞察才提炼成记忆/事实
- 自动把文章链接灌进记忆 = 浪费 token + 污染语义检索

### User Preferences

- Direct "有用/没用" verdict FIRST — do not lead with theoretical possibilities
- If useful only under conditions, state the condition clearly: "If you use X, then Y"
- If not useful, say so plainly — the user will say "那就卸载" when something doesn't fit
- Brief reasoning, not long analysis
- Rules of thumb: if it would REPLACE a working system, user prefers to stay

## Sample Verdicts

```
**有用** — 和你现有的 Hermes + Kanban 栈直接互补，不冲突。
**没用** — 只解决单机问题，你的共享记忆已经是更好的方案。
**有条件** — 如果你用 n8n 就有用，但你目前走的是 Python CLI 路线。
```
