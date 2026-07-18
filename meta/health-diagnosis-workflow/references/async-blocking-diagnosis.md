# Async-Blocking Diagnosis in Python Event-Loop Systems

## When to Use This Reference

The bot/gateway reports `connected` but doesn't respond. Gateway state says `running`, logs show incoming messages arriving, but no replies go out. The event loop may be blocked by a **synchronous** (`def`, not `async def`) operation that hogs the single thread.

This reference documents the technique the user calls "压缩是不是阻塞式实现" — is compression (or any other operation) blocking the event loop?

## The Three-Grep Pipeline

### Step 1: Locate the relevant files

```bash
grep -rn "<operation-name>" ~/.hermes/ --include="*.py" -l
```

For compression:
```bash
grep -rn "compress" ~/.hermes/ --include="*.py" -l
```

Key files to look for:
- `agent/conversation_compression.py` — orchestration
- `agent/context_compressor.py` — actual engine
- `agent/auxiliary_client.py` — LLM call
- `agent/turn_context.py` — trigger/preflight check

### Step 2: Check the function signature

```bash
grep -n "def <operation>\|async def <operation>" <file>.py
```

- `async def` → likely non-blocking (awaits properly)
- `def` (no `async`) → synchronous, blocks the event loop

For compression:
```bash
grep -n "def compress\|async def compress" agent/conversation_compression.py agent/context_compressor.py
```

### Step 3: Trace the call chain for `await`

```bash
grep -n -B5 "call_llm\|compress(" <file>.py | grep -E "await|async def|def "
```

If the chain is all `def` (no `async def`) and calls are directly invoked (no `await`), the operation is synchronously blocking.

Bonus: check the imported function's actual definition:
```bash
grep -n "def call_llm\|async def call_llm" agent/auxiliary_client.py
```

## Example: Hermes Compression (diagnosed in real session)

The chain found:

```
turn_context.py:387 — agent._compress_context(...)          # NO await
  → conversation_compression.py:314 — def compress_context(...)  # def, not async def
    → context_compressor.py:2372 — def compress(...)             # def, not async def
      → context_compressor.py:1668 — call_llm(**call_kwargs)     # NO await
        → auxiliary_client.py:5622 — def call_llm(...)           # def, not async def
```

Every link is synchronous. When compression runs (~103k tokens, 20–30s), the asyncio event loop freezes: no get_updates, no sendMessage, no heartbeat.

## How to Verify Without Source Access

If you can't read source files (user has no filesystem access):

1. **Timestamp-gap analysis** — Compare log times:
   - `inbound message` at T
   - `Preflight compression` at T+0.1s
   - `context compression started` at T+0.2s
   - `context compression done` at T+20s
   - `conversation turn` at T+21s
   
   The gap between "started" and "done" with NO other log lines = event loop was blocked.

2. **Look for `awaiting_real_usage_after_compression`** — This flag signals compression completed but real token usage hasn't arrived yet. Not a blocking indicator per se, but confirms compression ran synchronously.

## Quick Threshold Check (Hermes-specific)

```bash
grep -n "compression_threshold" ~/.hermes/hermes-agent/agent/agent_init.py
# Typical: threshold = 0.50 → 50% of model context window
```

If `approx_tokens >= threshold_tokens` triggers preflight compression, and threshold is 50% of context window (e.g. 200k × 50% = 100k), every conversation beyond ~100k tokens will experience the blocking delay.

## General Principle (applies to any asyncio system)

1. Any `def` function called from an `async` context without `await asyncio.to_thread()` blocks the event loop
2. Heavy operations to check: LLM calls, file I/O, network calls, compression, serialization
3. Telltale sign: no log lines between start and end of the operation
4. Workaround if code can't change: let it finish (it will), or kill the process and restart
