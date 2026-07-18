# Decision Taxonomy for Handover

When closing a session with mixed-status items, classify each decision explicitly. Use this taxonomy verbatim in the closing line so the user can scan in one second.

## Class A — Technical decision

**Definition:** Decision can be answered by reading, querying, or zero-cost verification. Has a single right answer or a clearly dominant trade-off. Angelife may not even need to weigh in — but they might want to confirm direction.

**Examples:**
- "改 config.yaml 还是改 provider 代码？"
- "先修 watchdog cron 还是先删？"
- "方案 A vs 方案 B，哪个风险更小？"

**Handover behavior:** Express the trade-off + current best recommendation. If user picks A → execute immediately. If user picks B → execute immediately. **Don't delay.**

**Closing line template:**
> A 类（技术性、零基础已搭好框架）：方案 1 / 方案 2 - 倾向 1 因为 [reason]。你点头即动。

## Class B — Pure judgment / value preference

**Definition:** No factual basis can resolve it. Has to be Angelife's own value weight. Examples: "你更看重 X 还是 Y？", "你想要这个风格还是那个风格？", "你想保留这个 fallback 还是相信新流程足够？"

**Examples:**
- "你主要靠常驻自动发现还是手动？"
- "这个 workflow 你愿意保留还是删？"
- "这种 catch 上要不要继续堆防？"

**Handover behavior:** Ask. Wait. Don't push. B-class may require Angelife to think across sessions, not just this session.

**Closing line template:**
> B 类（纯判断，需你想清楚）：我等你，不催。

## Class C — Habit anchor / future-state preference

**Definition:** Angelife's long-term preferences, often uncovered through prior corrections. Examples: "你更喜欢 A 还是 B 的汇报结构", "你下次希望 X 还是 Y", "这个 error 模式你要归档还\只是本轮提一下？".

**Examples:**
- "Skill 收录标准：进 skill 还是只进 memory？"
- "这个失败模式：是当 skill 还是当 pitfall？"

**Handover behavior:** Treat same as B. Wait. Don't push.

**Closing line template:**
> C 类（习惯锚点）：同 B。

## Class D — None / resolved / N/A

**Definition:** Already done by Hermes, no user decision needed. Mention only as confirmation.

**Closing line template:**
> D: 已 done — [evidence]. 自查完成。

## Anti-patterns

### B-class disguised as A-class

If a question **looks** technical but really needs Angelife's value weight, do not pretend it's A. Sometimes the technical answer is obvious (方案 1 wins on paper), but Angelife may have a non-technical reason to prefer 方案 2. **Default to B if any doubt exists.**

### A-class disguised as B-class

If a question **looks** like preference but actually has a defensible right answer (e.g. "rsync --delete 几乎 = 数据丢失, 几乎总应该排除 governance") then it's A. Don't manufacture paralysis.

### All-class decision tree ready?

When the report closes with "3 decisions left", ensure:
- [ ] Each decision is classified A/B/C
- [ ] A-class has a discernible 倾向 (approach with one trade-off)
- [ ] B/C are **explicitly labeled 我等你，不催**
- [ ] No pressure to respond in this turn

## Closing-line template (canonical)

```
我能继续做的（不依赖你拍板）：
- [item 1] — [mini-budget: ~X 分钟]
- [item 2]

等你拍板的（A/B/C 都注明）：
- A: [item, with 倾向]
- B: [item]
- C: [item]

我等你。
```
