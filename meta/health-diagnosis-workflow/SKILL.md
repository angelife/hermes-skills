---
name: health-diagnosis-workflow
description: Use when the user asks "is X working / what is X doing / what's the status of <robot|service|agent>" — or when you find pinged/recurring errors in logs, cron, providers, or gateway state and need to diagnose. Covers the meta-workflow of separating "the thing is fine" from "peripheral failures", prioritising low-cost verification (grep/read 30 lines of code), and avoiding premature causal grouping across heterogeneous errors. NOT for fixing the actual Hermes gateway/bot itself — that's hermes-troubleshooting.
disable-model-invocation: true
---

# Health Diagnosis Workflow

When the user asks "is X ok / what's X doing / status check", treat it as a structured diagnosis, not a summary dump. The output is a triage: what is fine, what is broken, what is uncertain, what to do next.

## The Four-Question Triage (mandatory first response)

Before naming any root cause, separate into four buckets:

1. **本体正常 / thing itself is fine** — the system the user mostly cares about. Verify with one obvious liveness probe (gateway status / process list / health endpoint).
2. **周边故障 / peripheral failures** — cron jobs, watchdog scripts, secondary monitoring loops. These look like "the bot is broken" but are not the bot. State clearly which side each error lives on so the user doesn't conflate them.
3. **不确定 / uncertain** — correlations you cannot prove (e.g. "two errors happened in the same week — might be same root cause, might not"). Label `待证`, not `已证`.
4. **下一步 / next move** — cheap path first.

Wrong shape: "everything is broken / everything is fine" — both are usually wrong.

## Cost-Ordered Investigation Rule (HARD)

When two paths could explain a symptom, ALWAYS:

1. Do the cheapest first (grep, read 30 lines of existing code, inspect config).
2. Mark the expensive path as "low-priority pending verification", NOT a parallel candidate.
3. Only escalate to the expensive path once the cheap one gave an answer or was exhausted.

This is the user's #1 repeated correction. Examples:
- "Look at the script before asking the user what it does" — don't bounce the question back to the user when 30s of grep would show them in the file.
- "Check existing logs before hitting the network" — the past event already left a trace; finding it is free, retrying online may be costly (rate-limit, quota burn, side-effects on a degraded account).
- "Don't curl to verify a 402 — grep the response body that was already logged."

Pitfall: bouncing questions back to the user is a HIGH-COST path masquerading as a low-cost path. It transfers cognitive load AND burns the user's trust. Refuse to do it when grep would answer.

## Evidence-Strength Rule (HARD)

Weak evidence → weak claim. Strong claim requires strong evidence.

Bad pattern (corrected by user mid-session):
> "Insufficient Balance (402) recently + Cloudflare route 7003 recently → these are all the same upstream change → fix one to fix all three."

This was a "可能同期" masquerading as "应合并处理". Two unrelated vendors (Xunfei vs Cloudflare), two unrelated accounts, zero shared root cause. The 402 had its own evidence (`title_generator` comment explicitly named `OpenRouter 402 exhausting the fallback chain` — a third unrelated vendor!). Premature grouping would have wasted hours chasing a non-existent consensus cause.

Rules:
- "时间接近" is NOT evidence of "同一根因".
- "都报 HTTP 4xx" is NOT evidence of "同一账户问题".
- Only state "同源" when you can name the SHARED mechanism (same provider/account/library/version).
- When uncertain, write `独立处理，待 X 修完后复检` — never `与 X 同源`.

## Decision: when to actually touch the network / make changes

Don't run the same request twice when the first response was already logged. If you already have:
- a 402 response body in `~/.hermes/logs/*.log` — read it, don't curl.
- a config file showing the wrong URL — grep the script that uses it, don't probe live.
- an API error in source comments (e.g. `agent/title_generator.py:17` documents fallback chain exhaustion) — cite it, don't rediscover.

The exception: when the existing signal is genuinely insufficient (truncated body, missing context, ambiguous error code), THEN probe live — but pick the lowest-risk probe (e.g. `GET /v1/models` over `POST /chat/completions`, since the former is rarely counted as a billable request).

## Reporting the Diagnosis

Final report format that this user prefers:

1. `【正常部分】` — concrete liveness evidence, not vague "looks fine".
2. `【有问题的部分】` — numbered list, each with: (a) what fails, (b) what we know, (c) what we don't, (d) recommended fix scope.
3. `【结论】` — one sentence: the user's primary concern (the thing itself) is or is not ok.
4. `【下一步建议】` — cheap steps first, expensive pending, order matters.

Avoid:
- Hedging everywhere ("might be X, could be Y, possibly Z") — pick the most supported, label uncertainty honestly but don't drown the user.
- Speculating about user intent ("do you want this to run 24/7?") when 30s of grep would show the runtime expectation in the script itself.

## When "Connected" But Silent: Event-Loop Blocking Check

When gateway_state says `running` + `telegram: connected` but the bot isn't replying, there's a deeper layer: the event loop may be blocked by a **synchronous** (non-`async`) operation. This is different from "the system is down" — the process is alive, Telegram is connected, but nothing can be received or sent because the single event-loop thread is occupied.

### Diagnosis steps (cheap first):

1. **Check active_agents** — `gateway_state.json` shows `active_agents: N`. If N > 0, an agent is processing. But "processing" doesn't mean "will respond" — if it's stuck in a synchronous call, it blocks the loop.

2. **Check agent.log for long-running sync operations** — grep for `Preflight compression` or `context compression started`. If compression is running and the timestamp is > 5 seconds ago with no `compression done` line after it, the event loop is blocked.

3. **Verify the compression code path is synchronous** — run the three-grep pipeline:

   Step A — locate compress-related files:
   ```bash
   grep -rn "compress" ~/.hermes/ --include="*.py" -l
   ```

   Step B — check function signature (`def` vs `async def`):
   ```bash
   grep -n "def compress\|async def compress\|def.*compress\|async def.*compress" <match-file>.py
   ```

   Step C — trace the call chain for `await`:
   ```bash
   grep -n -B5 "call_llm\|compress(" <match-file>.py | grep -E "await|async def|def "
   ```

   If the entire chain uses `def` not `async def` and calls are synchronous (no `await`) → the event loop is blocked. The user's precise term: "压缩是不是阻塞式实现".

4. **Confirm by timestamp gap** — If user sent a message at T, and the first log `inbound message` appears at T+5s, and the next `conversation turn` log at T+15s, the gap is the sync compression.

### Common Hermes sync-blocking chains found in the wild:

```
turn_context: Preflight compression (sync)
  → conversation_compression.compress_context() (sync)
    → ContextCompressor.compress() (sync)
      → auxiliary_client.call_llm() (sync, def not async def)
```

The gateway's asyncio event loop is frozen for the duration. No polling, no sendMessage, no heartbeat — until compression completes.

### Quick palliative fix:

Restart gateway: `kill -9 <gateway_pid>`. Gateway will auto-restart with `--replace`. This clears:
- Any in-progress synchronous operation
- The dead connection pool
- Degraded-path state

The root cause (sync blocking) needs code changes — this is a `hermes-troubleshooting` concern, not a `health-diagnosis-workflow` fix.

> **Reference**: `references/async-blocking-diagnosis.md` — full three-grep pipeline, example call chain for Hermes compression, and generalization to any asyncio system.
> **Reference**: `references/agent-self-check.md` — multi-level health check when the user asks "你自检一下" / "check yourself" (agent turning diagnosis inward). Covers agent core, host system, dependent services, and root-cause drill-down.

## Out of Scope (do NOT use this skill for)

- Fixing the actual Hermes gateway / agent runtime — use `hermes-troubleshooting`.
- Android system crashes / battery diagnostics — use `android-system-diagnostics`.
- MoA analysis aggregation — see memory rule on MoA v2 pitfalls.
- Provider quota/key rotation — that's a `hermes-provider-config` concern, not a status check.

## Investigate vs Motive: don't cross the line

`health-diagnosis-workflow` ends where the question stops being about the system and starts being about **what the user actually wants**. Common boundary cases:

- "Is X working?" → investigate-able, stay in skill.
- "Should X be 24/7?" → user-intent question, do NOT script-chase. Throw it back verbatim, with the script-derived evidence ("the script assumes daily; it's not designed to handle disconnect as graceful") so the user can decide.
- "Should I do Y or Z?" → decision-question. Surface the cost/benefit split, list the choices, leave selection to user. Do not pre-pick; do not reframe as investigation.

The skill's job is to **separate fact from motive** — once you find yourself filling in motive ("yeah, the user probably wants this fixed permanently"), you've crossed the line. Step back and put the question back to the user with the factual basis already assembled.

This pairs with the "report-writing" hygiene below: clean motive-free facts let the user make a clean decision.

## When the User Says "Test": Execute, Don't Pre-Diagnose

**Trigger:** User says "测试X的来回", "test X", "试一下X" — a request to test/verify something.

**Rule: TEST FIRST. Diagnose only after test proves something is broken.**

Wrong pattern (from 2026-07-02 session, repeated 5x):
```
User: 测试土同学的来回
Agent: [long analysis of gateway state, proxy health, log patterns...]
User: 测试土同学的来回
Agent: [more analysis, send test, but still verbose report...]
User: 测试土同学的来回
```

The user wanted a **test execution**, not a diagnosis. Every round of analysis before a test is a waste — the test itself is the cheapest probe.

**Correct flow:**

1. **Execute** — send the test message / run the probe immediately. No preface, no state analysis.
2. **Report result concisely** — `sent (message_id=X)` or `failed: Y`. One line.
3. **Only then, if the test failed**, enter diagnosis mode (use the four-question triage above).

**Key distinction:**
- TEST = execute the operation + report result (cheap path, do first)
- DIAGNOSE = investigate what's wrong (expensive path, do only after test fails)

When the user repeats the same short test request twice, they are NOT adding context — they are telling you your response format is wrong. Stop analyzing, execute the test.

This rule is an extension of the "Cost-Ordered Investigation Rule": the test itself is the cheapest probe. Running it is not optional — it is step 1.

## Pitfall Catalogue (update as you discover more)

- [P1] 抛问题给用户比 grep 贵：用户纠正过"应该自己 grep 看脚本，不要把'需要确认'的问题甩回来让用户回答"。
- [P2] 时间近 = 同源：两个错误都在同一周报不算"同根因"——必须能说出共享机制（同一 provider / 同一账户 / 同一库 / 同一版本）。无机制即独立处理。
- [P3] 把 402 / 路由错 / 限流当 URL 错：先 grep 响应体，看是 `insufficient_quota` 还是 `no_route` 还是 `auth_failed`——这三个修法完全不同。
- [P4] 把 watchdog 误判当真实故障：`device not found` → "Gateway not running" 这类把"探测工具找不到目标"误读成"目标宕了"的逻辑，应当改成先查探测工具本身可用性。
- [P5] 在 memory 里记"故障 X = 账户欠费"快于查证：错误码 402 在本会话日志里有真实证据，memory 里旧条目可参考但不能直接当结论引用。
- [P6] 把决策问题重新包装成事实问题：当 grep/读代码能回答的，问用户就是转移负担；当事实核验已经穷尽且答案不是来自事实而是来自"你想要什么"时，再问用户就不是浪费。把 *重量均匀的 3 选 1*（做不做、范围、来源在哪）原样抛回，不掺入"时机"等细节子问题——核心问题先决定，锦上添花的细节下轮再问，否则决策负担被堆重，用户拍板会更慢。
- [P7] "打算 X 完之后顺手补" 即规则违反：mint 新规则时如果发现自己接下来要做的事恰好是规则的反面（"这条规则适用于以后，这次先斩后奏"），立刻停下来，要么 (a) 把规则应用到当前步骤要么 (b) 显式声明过渡期例外从下一份起严格执行，不要在"正常推进"的措辞里悄悄开特例。
