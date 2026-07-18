---
name: telegram-gateway
description: Deploy, operate, and troubleshoot Hermes Telegram gateway — connection pool management, TCP keepalive, proxy configuration, watchdog, periodic client refresh, and connection pool timeout root cause analysis
category: devops
---

# Telegram Gateway Operations

Operate the Hermes Telegram gateway (python-telegram-bot over HTTPX/SOCKS5 proxy). Covers pool timeout diagnosis, TCP keepalive tuning, code-level connection pool parameters, periodic client refresh, and launchd/plist env persistence.

## Trigger

Use this skill when:
- Telegram bot stops responding, gateway process still alive
- Logs show "Pool timeout: All connections in the connection pool are occupied"
- User reports bot not replying on Telegram/Discord/SMS/Signal channel
- Setting up or tuning gateway resilience on macOS (launchd-managed)
- Diagnosing proxy-related connection issues (xray/v2ray/sing-box)
- Bot can receive messages but not reply (upstream model API rate limited)

## Common Bot-Not-Responding Scenarios (not all are gateway issues)

### Triage Rule — Break the Restart Loop

**When you see pool timeout → restart → works ~7 min → pool timeout again → user asks again → restart again: STOP the cycle after the FIRST recurrence.**

If the gateway was restarted within the last 15 minutes and is already silent again with `Pool timeout` or `connection pool may be wedged` in logs, **do NOT restart a second time**. [...]

### Triage Rule — Break the Model Change Cycle

When the bot is connected (polling OK) but upstream model calls fail with 429 across multiple providers, do NOT restart the gateway — the gateway is fine. The fix is model-level, not process-level.

**Recognize the pattern** (don't waste time re-diagnosing each recurrence):
- Same aggregator (OmniRoute `localhost:20128`), same model (`ddgw/gpt-5-mini` → 429), same fallback chain (opencode-zen connection errors, nvidia 429)
- Previous session already identified the fix: switch to `wuxing-free` or `auto/best-free`
- Check `session_search(query="ddgw.*429 OR model.*rate.limit OmniRoute", limit=1)` BEFORE starting fresh diagnostics

**Short-circuit to fix:**
```bash
# When you've seen this before, skip the full triage
sed -i '' 's/^  default: .*/  default: wuxing-free/' ~/.hermes/config.yaml
launchctl stop ai.hermes.gateway && sleep 3 && launchctl start ai.hermes.gateway
```

**Known gap (维修机器人 wishlist):** This pattern recurs every few days when OmniRoute's `ddgw/*` models hit per-key rate limits. A future improvement would be a self-healing cron that detects `model=ddgw/* + 429 in gateway.error.log` and auto-switches to a working model on the same aggregator, logging the change. For now, the fix is manual but fast (~30s) once recognized.

1. Check NO_PROXY state: `grep -i "^no_proxy\|^NO_PROXY" ~/.hermes/.env`
2. If missing → add `NO_PROXY=api.telegram.org,localhost,127.0.0.1` to `.env`
3. THEN restart once
4. Verify result is stable (>30 min without pool timeout)

This rule also protects the user experience: each unnecessary restart delays the real fix by ~30 seconds of downtime + the minutes until the next recurrence, and frustrates the user who has to repeat the same question.

Before deep-diving into pool/proxy issues, check the actual failure layer:

0. **OmniRoute down** — Bot receives messages but never replies. `gateway.error.log` shows upstream provider errors (429 / timeout / connection-error) across ALL configured providers simultaneously. Root cause: Hermes `fallback_providers` points directly at upstream APIs (opencode-zen, nvidia) instead of routing through OmniRoute (`localhost:20128`). When OmniRoute is not running, there's no auto-fallback layer. Fix: start OmniRoute, then reconfigure Hermes to route through it. See `references/omniroute-down-bot-silent-2026-07-12.md`.
1. **Telegram API 429**: Bot can't poll or send. gateway.log shows Telegram-level 429s. Fix: wait it out or restart to reset counter.
2a. **Model-specific 429 on aggregator (OmniRoute ddgw/oc models)**: Bot receives messages but AI never responds. `gateway.error.log` shows 429 on `ddgw/gpt-5-mini` or `oc/*` models via OmniRoute (base_url http://localhost:20128/v1). **Key distinction** from generic "all providers exhausted": the aggregator itself is healthy — other models on the same OmniRoute work fine. The agent exhausts the fallback providers (opencode-zen, nvidia — which may be independently dead) and never tries a different model on the same aggregator. Fix: switch `model.default` to a different model on OmniRoute (e.g. `wuxing-free` or `auto/best-free`) and restart gateway. See `references/ddgw-model-429-on-omniroute-2026-07-14.md` for full diagnostic sequence.

2b. **Model provider 429 / API errors (generic)**: Bot receives messages (polling works) but AI responses fail. gateway.error.log shows upstream provider errors (e.g. nvidia RateLimitError, xunfei InvalidParams). Fix: check provider status, consider model fallback, or restart to reset rate limit counters.
3. **Pool timeout**: Classic pattern covered below. Gateway process alive but connections stuck.
4. **Proxy down**: No messages in or out. Check xray/sing-box process separately.
5. **NO_PROXY bypass blocking proxy routing**: Gateway logs show `Proxy detected` but connecting to fallback IPs (149.154.166.110, 149.154.167.220) times out.
   Root cause: `no_proxy=api.telegram.org,...` in `.env` forces Telegram traffic to bypass the proxy entirely.
   → If direct connection to `api.telegram.org` times out (GFW) but the proxy works for other HTTPS sites (`curl -x socks5://127.0.0.1:10808 https://httpbin.org/ip`), the NO_PROXY entry needs to be removed (see "Lifecycle: NO_PROXY Bypass Can Become the Blockage" in the macOS proxy section below).

6. **All upstream providers exhausted → response timeout**. Bot receives messages but responses arrive too late.
   `gateway.log` shows `Send failed: Not connected` or `Pool timeout: All connections in the connection pool are occupied` with timestamps 15–30 minutes AFTER the last inbound message.
   `gateway.error.log` shows every provider in the fallback chain returning 429/503/ResourceExhausted (OmniRoute free tier rate limited, all NVIDIA keys at 48/48 workers, etc.).
   The chain: agent receives message → tries primary provider (429) → tries all fallbacks (each returns exhausted) → retries entire chain 3x → 15–30 minutes pass → agent finally produces a response → Telegram connection has already timed out → `Send failed: Not connected`.
   Fix: switch the default model in `config.yaml` to a different model on the same aggregator (e.g. from `oc/deepseek-v4-flash-free` to `ddgw/gpt-5-mini` on OmniRoute), then restart gateway. The gateway itself is fine — the upstream is the bottleneck. See `references/all-providers-exhausted-2026-07-14.md`.

Quick diagnostic:
1. `cat gateway_state.json` — check `active_agents`. If >0 and bot is silent, an agent session is probably holding connections (pool saturation signal).
2. `tail -50 gateway.log | grep -E "429|Error|pool|Connected|refresh"` — polling health and error clusters.
- `tail -20 gateway.error.log` — Hermes-level errors (model API failures, timeouts).
4. **Advanced: lsof TCP count** — count actual OS-level connections to Telegram API vs SOCKS5 proxy (see `references/pool-timeout-dual-pool-2026-07-01.md` for zombie interpretation):
   ```bash
   gw_pid=$(cat gateway_state.json | python3 -c "import sys,json; print(json.load(sys.stdin)['pid'])")
   echo "To Telegram API: $(lsof -p $gw_pid -iTCP -sTCP:ESTABLISHED | grep -c '104.19.149.161')"
   echo "To SOCKS5 proxy: $(lsof -p $gw_pid -iTCP -sTCP:ESTABLISHED | grep -c ':10808')"
   ```

## Architecture Overview

User Telegram App -> api.telegram.org(443) -> Hermes Gateway -> SOCKS5 proxy(127.0.0.1:10808) -> xray/sing-box -> Cloudflare -> VLESS remote server

The gateway runs two HTTPXRequest instances:
- _request[0]: polling (getUpdates) — drained by _drain_polling_connections on reconnect
- _request[1]: general (send, edit, etc.) — drained by _periodic_client_refresh

## Verified Root Cause (2026-06-30, code+log dual evidence)

The actual fault propagation chain is NOT pool exhaustion itself — pool exhaustion is
the trigger, the real amplifier is a single boolean flag. Trace:

1. SOCKS5 link jitter / packet loss → PTB long-poll heartbeat times out
2. PTB error_callback fires `adapter.py:_handle_polling_network_error`
3. First line of that handler: `self._send_path_degraded = True` (adapter.py:1727)
4. `send()` checks the flag FIRST (adapter.py:2955) and short-circuits:
   `return SendResult(success=False, error="send_path_degraded", retryable=True)`
   — no connection acquired, no pool slot occupied, just a hard refuse.
5. Sleep 5/10/20/40/60s, then `_drain_polling_connections` rebuilds `_request[0]`,
   then `start_polling()` succeeds → `self._send_path_degraded = False` (adapter.py:1776).

So the SAME flag couples two physically-isolated pools (polling vs general). When
polling has trouble, **all sends are refused**, even though `_request[1]` may be
perfectly healthy. The dispatch failure pattern looks like pool timeouts because
PTB also has its own retry ladder on top, but the proximate cause is the boolean.

**Three retries stack on top of each other (open follow-up):**
- Hermes `agent.conversation_loop` retry: upstream model 429 → 2s/5s exponential
- `_handle_polling_network_error` retry: 5s/10s/20s/40s/60s exponential
- Gateway layer `attempt 1/2 retrying in 2.8s` on `send_path_degraded`

Whether these amplify each other (e.g. conversation_loop blocking on the upstream
while degraded) was NOT measured. Note as follow-up.

## Failed Hypotheses Worth Remembering

- "SOCKS5 swallows RST → dead connections occupying pool forever" — NOT proven.
  tcpdump data did not confirm.
- "Coroutine-awaited send blocks polling task" — NOT the mechanism. PTB 22.x has
  `_request[0]` and `_request[1]` as separate httpx.AsyncClient instances; the
  coupling is the shared `_send_path_degraded` boolean, not a coroutine hang.
- Retry-inside-httpx-connection (direction 1) — NOT the case. Hermes retry is in
  `conversation_loop`, exponential 2/5s, not transport-level.
- **"HTTP proxy returns 502 on upstream failure, SOCKS5 doesn't"** —
  **DISPROVEN by controlled test (2026-07-03).** A standalone xray ran both
  SOCKS5 (10812) and HTTP (10813) inbounds sharing the same broken VLESS outbound
  (Cloudflare IP with wrong path — real failure mode: tunnel establishes, then
  protocol hangs). **Result: both protocols behaved identically.** Tunnel
  established successfully (SOCKS5 0x00 / HTTP 200), TLS Client Hello sent, then
  hung at waiting for Server Hello, timed out at 20s with curl: (28).
  Reasoning: once a CONNECT tunnel is established, both protocols enter blind
  forwarding mode; the HTTP control layer ends at the CONNECT response. A 502
  would only occur if upstream fails BEFORE the tunnel completes (connection
  refused, TCP timeout on connect). Full test methodology in
  `references/http-vs-socks5-comparison-test-2026-07-03.md`.

**Partial survivor:** SOCKS5 link jitter IS still the trigger (polling heartbeat
watch), just not the "swallows RST" mechanism. Don't fully cross the proxy off
the suspect list — rephrase as "SOCKS5 link jitter" not "SOCKS5 RST swallow".

## What Actually Needs Fixing (vs. what we tried)

Instead of the direction-1/2/3 trio (which target retry semantics and pool
isolation, neither of which solve the upstream 429 → send refuses problem):

1. **Loosen the polling heartbeat threshold** — one jittered packet should not
   immediately set `_send_path_degraded`. Require N consecutive failures before
   setting the flag, or widen the heartbeat window.
2. **Make `_send_path_degraded` independently verifiable** — instead of trusting
   the polling-side judgment for the send pool, do a short-timeout probe of the
   send pool itself (`SendMessage ping` with ~1-2s budget) before refusing.
   Polling and send use physically separate pools; treating one pool's trouble
   as the other's failure is a design mistake.

Watchdog auto-restart remains as the final safety net.

## Architecture Overview

## Pool Timeout Root Cause

Pool timeout happens when httpcore connection pool slots are all occupied by connections that appear "in use" but are actually dead (the proxy or remote server closed them without notifying the client properly). SOCKS5 proxies can swallow TCP RSTs, so httpcore never learns the connection is dead.

### SSL Handshake Failure Canary (2026-07-02, empirical fill timing)

Observation across two independent pool exhaustion events (same gateway process, same day):

1. **SSL failures precede pool timeout by ~28 min** — `SSLV3_ALERT_HANDSHAKE_FAILURE` through
   SOCKS5 proxy (xray) is the earliest detectable signal in gateway.log. Each failure leaves a
   broken TCP connection that httpx's pool does not immediately drain (the proxy's TCP half
   enters CLOSE_WAIT while httpx considers the slot "in use").
2. **Accumulation rate at pool_size=512: ~18 connections/min** — at 512 max_connections, the
   pool exhausts in ~28 minutes from the first SSL failure. Measured empirically on 2026-07-02:
   - **First cycle:** 13:40 first SSL failure → 14:08 first pool timeout (**28 min**)
   - **Second cycle:** After restart at 14:13, SSL failures resume at 14:30 → 14:55 pool
     timeout (**25 min**, 11% faster — possibly residual connections from the restart)
3. **Dual amplifier** — two unrelated failures accelerate the same leak:
   - **Primary:** SSL handshake failures create zombie connections (proxy-level issue)
   - **Amplifier:** Slow model API responses (150–547s vs normal ~20s) hold active connections
     longer. During the second cycle, OpenCode Zen 429, Xunfei 10163, and Cloudflare 400
     errors co-occurred with the user conversation, driving response times to 2–9 minutes.
4. **Second fill is consistently faster** — 25 vs 28 min, observed twice. Hypothesis: the
   restart does not fully drain all connection states (TIME_WAIT from the old process lingers).

**Diagnostic heuristic:** If you see `SSLV3_ALERT_HANDSHAKE_FAILURE` or `ConnectError: [SSL:*]` in gateway.log, **expect pool timeout within the next 30 minutes**. This is the canary — not the root cause itself, but a reliable early indicator at the observable layer. When you see SSL errors, you have ~28 minutes before the pool freezes. This is actionable: you can schedule a preventive rolling restart, or use the window to probe the proxy chain before the bot goes silent.

**Compare with previous observation (2026-07-01, pool_size=64):** Earlier lsof data showed ~1 zombie/min and ~60 min to fill at pool_size=64. With the default pool_size=512, the fill rate is ~18 connections/min — faster in absolute terms because httpx has more room to accumulate dead connections before the pool-timeout backstop fires. The per-second SSL-failure arrival rate is the independent variable; the pool_size only determines the time-to-exhaustion.

### Code-Level Mechanism (verified 2026-07-02, source-tracing confirmed)

The leak is NOT in the httpx pool slot management (that is correct). The leak is a **TCP stream not closed on TLS handshake failure** inside `httpcore._async.socks_proxy.AsyncSocks5Connection.handle_async_request()`.

When `stream.start_tls()` (the TLS handshake through the SOCKS5 proxy) fails with `SSLV3_ALERT_HANDSHAKE_FAILURE`:
- The `except Exception` block correctly sets `self._connect_failed = True`
- But **does NOT call `await stream.aclose()`** before `raise exc`
- The `stream` (TCP connection to xray proxy at 127.0.0.1:10808) goes out of scope without being closed
- The httpx pool slot IS properly freed (`is_closed()` returns True → connection removed from pool)
- But the underlying TCP socket to xray leaks — accumulates as CLOSE_WAIT on the proxy side

Over time, leaked connections degrade xray's performance, making new connections slower → pool slots occupied longer → eventually pool exhaustion. Full code trace in `references/stream-leak-code-path-2026-07-02.md`.

**This mechanism is distinct from the `_send_path_degraded` boolean path** (2026-06-30 root cause). Both are fed by xray proxy instability, but:
- `_send_path_degraded`: polling heartbeat times out → boolean short-circuits all sends (seconds to minutes, no pool fill)
- TCP stream leak: SSL handshake failures leave TCP sockets open → proxy degrades → pool fills over ~28 min

They share the same unstable downstream dependency (xray) but have different leak mechanisms. List separately in reports — never merge into "same bug".

### Contrast with older root cause (`_send_path_degraded` boolean)

The 2026-06-30 analysis identified a different failure path: SOCKS5 jitter → polling heartbeat
timeout → `_send_path_degraded = True` → all sends short-circuited without touching the pool.
That mechanism is still valid for **transient disconnection** (seconds to minutes). The 2026-07-02
pattern is distinct: **no `_send_path_degraded` activation before pool timeout**. The SSL failures
gradually fill the connection pool over 25-28 minutes until polling itself can't get a slot.
These are two independent failure modes fed by the same root cause (proxy instability).

Three-layer defense:

### Layer 1: System TCP Keepalive (macOS)

Default macOS keepalive is 7200 seconds (2 hours). Set to seconds for fast dead-connection detection:

```bash
sudo sysctl -w net.inet.tcp.keepidle=30000
sudo sysctl -w net.inet.tcp.keepintvl=10000
sudo sysctl -w net.inet.tcp.keepinit=10000
```

Persist in /etc/sysctl.conf:
```
net.inet.tcp.keepidle=30000
net.inet.tcp.keepintvl=10000
net.inet.tcp.keepinit=10000
```

On macOS without sudo, use osascript:
```
osascript -e 'do shell script "...command..." with administrator privileges'
```

### Layer 2: httpx Connection Pool Parameters

Add to telegram.py connect() method, both proxy and non-proxy paths:

```python
import httpx
_pool_size = int(os.getenv("HERMES_TELEGRAM_HTTP_POOL_SIZE", "512"))
_httpx_limits = httpx.Limits(
    max_connections=_pool_size,
    max_keepalive_connections=int(os.getenv("HERMES_TELEGRAM_HTTP_MAX_KEEPALIVE", "16")),
    keepalive_expiry=float(os.getenv("HERMES_TELEGRAM_HTTP_KEEPALIVE_EXPIRY", "30.0")),
)
_httpx_kwargs = {"limits": _httpx_limits}
request = HTTPXRequest(**request_kwargs, proxy=proxy_url, httpx_kwargs=_httpx_kwargs)
```

PTB's HTTPXRequest merges httpx_kwargs LAST in the client_init call, so httpx_kwargs overrides
the internally-created Limits. This is the correct way to set keepalive_expiry/max_keepalive.

### Layer 3: Periodic Client Refresh

Add _periodic_client_refresh method and schedule it via asyncio.ensure_future right
before return True in connect(). Rebuilds _request[1] (general) every 300s.
_request[0] (polling) is handled by existing _drain_polling_connections.

Pattern in _periodic_client_refresh:
1. Read current env vars for pool config
2. Build new HTTPXRequest with same config
3. await new_general.initialize()
4. Swap atomically: self._app.bot._request = (old_req[0], new_general)
5. await old_general.shutdown()
6. Never interrupt polling request (_request[0])

### Diagnosing "Bot Silent / No Reply"

Bot stops replying but polling appears healthy (`Connected to Telegram` in logs).
Two distinct root causes — check BOTH logs:

**Upstream Model Provider 429** — `gateway.error.log` shows:
  `API call failed: RateLimitError 429 provider=nvidia base_url=https://integrate.api.nvidia.com`
  → The AI model backend (NVIDIA, OpenCode, etc.) is rate limiting. Bot receives
    the message and tries to respond but the model call fails. Each failed attempt
    holds a connection in the pool while retrying; multiple concurrent sessions
    can exhaust the pool before retries complete. This is the **#1 root cause**
    of pool timeout in practice. Fix: add a circuit breaker / retry queue at the
    Hermes agent layer so 429 responses return the connection immediately rather
    than holding it through exponential backoff.

**Telegram API 429** — `gateway.log` shows:
  `Error code: 429 - Too Many Requests` from `api.telegram.org`
  → Telegram's own bot API is rate limited. Restart clears the pool. Less common
    than model 429 for pool exhaustion.

**Always check gateway.error.log first** when the bot is silent — it contains
Hermes agent-level errors (model API failures, unclosed sessions, config
warnings) that do NOT appear in gateway.log.

**Always verify root cause before prescribing config changes.** Pool timeout has multiple possible triggers. Apply the diagnostics in order — do not assume proxy/SOCKS5 is the cause until you have checked upstream 429s first.

**Never label unsourced config values as "verified in production."** If you cite numbers (pool size, keepalive expiry, timeout values) that come from skill text, external research, or inference — say exactly where they come from. Do NOT write "生产验证过" or "已在生产环境验证" unless you personally ran the exact values on this machine and can name the date. False provenance makes the numbers look authoritative when they may be untested approximations. Correct phrasing: "来自 httpx/httpcore 官方文档建议值" or "skill 内记录值，建议先用保守值验证" or "本机实测于 2026-06-30 Hermes环境".

**Never claim a mechanism is confirmed without logging evidence.** If you theorize "SOCKS5吞RST导致死连接" or similar, you must verify with actual observation (netstat ESTABLISHED count, tcpdump, gateway.error.log timestamp correlation) before presenting it as fact. A mechanism that sounds plausible from first principles is still a hypothesis until verified on the specific chain in use.

### Diagnostic Discipline (2026-07-04 session rule)

These are mandatory for any gateway fix or verification task. Do not downgrade them with phrases like "看起来通过" or "应该没问题".

1. **No evidence = not verified**, not "probably fine".  
   - Logs without timestamps are insufficient for time-window proof.
   - Missing request_id / monotonic timestamp in `gateway.error.log` means fallback and routing investigations are blocked until Hermes logging is improved.
2. **Code change != runtime verification**.  
   - "Config value updated" is necessary but not sufficient. You need a real traffic path exercising the changed code path.
3. **Warmup vs real traffic is a hard distinction**.  
   - `ps -p` or `launchctl list` saying the process is alive is not acceptance criteria for Telegram reply, model fallback, or watchdog behavior.
4. **Existing mechanism != already-verified**.  
   - If `run --replace` or a runtime lock exists on disk but you have not tested the duplicate-start and stop-cleanup paths end-to-end, treat it as "code exists, unverified".
5. **No double-negative acceptance**.  
   - "No new Pool timeout in 30 minutes" is acceptable only if there was also positive traffic during that window. Silence with no traffic is not evidence.
6. **Provider-side evidence preferred over tool-side silence**.  
   - For fallback verification, prefer service-side request count / access log / metrics over absence of errors in Hermes logs.
7. **Parallel-start test must also preserve the first instance**.  
   - Accept only if: second start is rejected, first instance PID unchanged, and no process gets killed by the second call’s cleanup logic.
8. **Revise conclusions when the evidence shape changes**.  
   - If logs show no timestamps, do not keep asserting a time-window match. Downgrade to: "verifiable only after logging improvement".
9. **Observation record keeping**.  
   - Every verification must record: exact command, exact output, exact timestamp, exact PID/state. Past inferences without these artifacts do not count as validation history.
10. **Highest-risk statement wins the label**.  
    - When reporting gateway state, use the stricter description among: "running", "alive but degraded", "unverified". Do not promote a weak signal to "running".

### Watchdog Hardening (agent path removal)

Preferred pattern: `no_agent` cron using a deterministic script (bash/python). Verify function, not exit code alone:

- Inject a known-bad keyword into `gateway.error.log`
- Run the script
- Confirm behavior changes from the baseline run
- Check the runner’s own logs for the changed output

This is the same evidence pattern used for STEP 3.5: not "script returned 0", but "script reacted to input".

### Watchdog (cronjob fallback)

If pool timeout still occurs, deploy a 5-minute cron that checks gateway.log
for 3+ pool timeouts in the last 10 minutes and restarts:

```
*/5 * * * * bash ~/.hermes/scripts/watchdog_no_agent.sh
```

**Preferred pattern: no_agent script.** A watchdog should be a deterministic
bash/python script, NOT an LLM-agent cron job. Rationale: health checks are
rule-based (process alive, log keyword count, threshold comparison) and do not
require semantic generation. Using an agent path introduces avoidable failure
modes: prompt assembly cost, context compression, model-specific limits like
`max_tokens=65536 > 32768`, and context-length crashes (`Context length exceeded`)
that can themselves break the cron job even when the gateway is fine.

Watchdog no-agent script structure:
- read `~/.hermes/gateway.pid`, parse pid field, `kill -0 $PID` for process liveness
- grep recent `gateway.error.log` for `Pool timeout|403|polling conflict` in last N minutes
- fixed branch logic: `if dead -> restart + alert; elif errors>=threshold -> alert; else ignore`

If you must keep an agent-based watchdog for semantic log analysis, split it:
core liveness/threshold checks stay in a no_agent script, and only the anomaly-
classification step runs as a separate low-frequency LLM task. Never let the
entire watchdog depend on LLM inference.

**Pitfall — watchdog cron model must support tools.** If the watchdog is an LLM-agent cron job (not a no-agent script), its model MUST support function calling/tools. Xunfei does NOT — the API rejects the `tools` param with 10163. Always override the cron job's model (`hermes cron update <job-id> --model provider/model-id`) to one that supports tools, e.g. `cloudflare-workers-ai/@cf/qwen/qwen3-30b-a3b-fp8` or `opencode-zen-free/deepseek-v4-flash-free`.

To verify: check `hermes cron list` — if the job shows `error: RuntimeError` with 10163, it's a model mismatch, not a gateway issue.

**Relation to max_tokens hardening (STEP 3 + STEP 3.5).**
- STEP 3 = global safety net: keep provider-level `default_max_tokens` capped
  (recommended 28000 for free Cloudflare Workers models with 32768 context).
- STEP 3.5 = root-cause fix for watchdog: convert the watchdog cron to no_agent
  so it no longer enters any LLM path. Both should be present; they are layered
  defenses, not alternatives.

### launchd plist env persistence

All HERMES_TELEGRAM_HTTP_* env vars must live in the plist
~/Library/LaunchAgents/ai.hermes.gateway.plist under EnvironmentVariables key,
because launchd clears the environment when starting a daemon.

Current recommended values:
  HERMES_TELEGRAM_HTTP_POOL_SIZE=256
  HERMES_TELEGRAM_HTTP_POOL_TIMEOUT=30
  HERMES_TELEGRAM_HTTP_CONNECT_TIMEOUT=15
  HERMES_TELEGRAM_HTTP_READ_TIMEOUT=30
  HERMES_TELEGRAM_HTTP_WRITE_TIMEOUT=30
  HERMES_TELEGRAM_HTTP_MAX_KEEPALIVE=16
  HERMES_TELEGRAM_HTTP_KEEPALIVE_EXPIRY=30
  HERMES_TELEGRAM_HTTP_REFRESH_INTERVAL=300

## Deploying Changes

After editing telegram.py or the plist:

1. launchctl unload ~/Library/LaunchAgents/ai.hermes.gateway.plist
2. wait 3 seconds for graceful shutdown
3. launchctl load ~/Library/LaunchAgents/ai.hermes.gateway.plist
4. Wait 8-10 seconds for connection
5. Verify: grep "Connected to Telegram" /Users/macos/.hermes/logs/gateway.log | tail -1

## Other "Bot Not Responding" Root Causes

Pool timeout is the classic cause, but the bot can also appear dead when the **upstream LLM provider** is rate-limited or erroring. Symptoms:

- Gateway process alive
- Polling works (inbound messages appear in log)
- No "Pool timeout" in logs
- But: `RateLimitError [HTTP 429]` or provider-specific errors in gateway.error.log
- Bot receives messages but never generates a reply (agent loop fails on API call)

Diagnosis: check gateway.error.log, not just gateway.log. If you see repeated 429s or provider errors, the fix is:
1. Wait for rate limit window to expire (usually minutes)
2. Or: switch default model in config to an unthrottled provider
3. Restart gateway to clear any accumulated bad state (but this alone doesn't fix rate limits)

Also seen: Xunfei provider returning `RequestParamsError:Invalid Params` (code 10163). Root cause: Xunfei does **not** support the `tools`/function calling parameter. When the watchdog cron job (or any agent needing tool access) uses Xunfei as its model, the API rejects the `tools` param with 10163. Fix: override the cron job's model to one that supports function calling (e.g. `@cf/qwen/qwen3-30b-a3b-fp8`). Direct curl without `tools` works fine — this is a capability gap, not a config error.

### All Providers Exhausted — Response Timeout

A distinct failure mode where the gateway is healthy, polling works, but **every provider in the fallback chain returns 429 or 503 simultaneously**. The agent spends 15–30 minutes retrying through the entire chain (3 retries × N providers), and by the time a response is finally produced, the Telegram long-poll connection has expired.

**Signs:**
- `gateway.log`: `Send failed: Not connected` (plain-text fallback also fails)
- `gateway.error.log`: all providers show `429 Rate limit exceeded`, `503 ResourceExhausted: Worker local total request limit reached (48/48)`, or `ResourceExhausted: All workers are busy`
- Timestamp delta between `inbound message` log and `Send failed` log is 15–30 minutes
- `gateway_state.json` shows `connected`, polling is fine
- Gateway auto-restart may occur mid-crisis but doesn't fix the upstream

**Root cause:** This is NOT a gateway problem. The free-tier model on the aggregator is rate-limited AND the fallback chain (NVIDIA with multiple keys) is also fully exhausted. Nothing in the config can generate a response.

**Fix (not gateway restart):**
1. Identify a working model on the aggregator: `curl http://localhost:20128/v1/models | python3 -c "import sys,json; [print(m['id']) for m in json.load(sys.stdin)['data'] if m.get('capabilities',{}).get('tool_calling')]"` to list models with tool support
2. Switch default model: `hermes config set model.default <working-model-id>`
3. Restart gateway: `launchctl stop ai.hermes.gateway && sleep 3 && launchctl start ai.hermes.gateway`
4. Verify: send a test message to the bot

**Differentiation from other silent-bot modes:**
| Symptom | vs pool timeout | vs one-provider 429 |
|---------|----------------|---------------------|
| `Send failed: Not connected` | ❌ (pool timeout shows pool errors) | ❌ (single 429 eventually falls through) |
| `gateway.error.log` pattern | SSL failures + single 429 | one provider 429, others work | ✅ ALL providers exhausted |
| Response time | <1min | <2min | ✅ 15-30min |
| Fix | pool tuning / watchdog | wait or switch model | ✅ switch to different model on same aggregator |

## HTTP Proxy Solution (方案①: SOCKS5 → HTTP) — DISPROVEN

**TESTED 2026-07-03 — hypothesis NOT confirmed.** See
`references/http-vs-socks5-comparison-test-2026-07-03.md` for full methodology.

### Hypothesized Rationale (disproven)

SOCKS5 protocol swallows connection failures at the socket level. The theory was
that HTTP CONNECT proxy would make failures explicit (502/504), letting httpx
release the connection immediately instead of leaving zombie connections.

**Controlled test showed identical behavior:** both SOCKS5 and HTTP proxy
establish the tunnel successfully, then BOTH hang identically at TLS handshake
through the tunnel when the upstream is stuck. The reason is architectural:
once a CONNECT tunnel is established, the proxy enters blind byte-forwarding
mode. The HTTP control layer ends at the CONNECT response. A 502 can only
occur if the upstream connection fails BEFORE the tunnel completes (connection
refused, TCP timeout on connect), which is NOT the typical failure mode in
this environment.

### Post-Test Verdict

The Discovery Gate ranking from the user's analysis (2026-07-03) was correct in
structure but needs a post-test revision:

| # | Solution | 根治度 | 工作量 | Post-Test Verdict |
|---|----------|--------|--------|-------------------|
| ③ | Watchdog restart / pool_size tuning | Low | Low | Stop — palliative, delays but doesn't cure |
| ~~①~~ | ~~HTTP proxy instead of SOCKS5~~ | ~~High~~ | ~~Low~~ | **DISPROVEN** — test showed no behavior difference |
| ② | Decouple polling/send degraded flags | Medium | Medium | Re-evaluate — now the only remaining high-ROI option |
| ④ | Replace proxy protocol entirely | High | High | Defer — revisit if ② is insufficient |

Key implication: since ① is disproven as a mechanism-level fix, the root causes
(swallowed failure signal, boolean path coupling, TCP stream leak) remain open.
方案② (decouple polling/send degraded flags) and the already-fixed pool size &
watchdog are now the only active defenses.

**Symptom:** `Proxy detected; passing explicitly to HTTPXRequest: socks5://<stale-ip>:10808` in gateway.log, followed by connect timeout. Direct curl from the same runtime with a shell-exported proxy works. Root cause: the `.env` file still contains the old proxy while shell exports point to a working one.

**Fix:** update `.env` proxy vars to the working address, restart gateway, then confirm the proxy line in the log. Verification heuristic: compare `grep -i proxy ~/.hermes/.env` against the `Proxy detected` line in gateway.log after restart.

## macOS System Proxy Auto-Detection & Bypass (2026-07-06)

Hermes Gateway uses `resolve_proxy_url()` (`gateway/platforms/base.py`) to detect
proxies with this priority order:
0. Platform-specific env var (e.g. `TELEGRAM_PROXY`) — highest
1. `HTTPS_PROXY` / `HTTP_PROXY` / `ALL_PROXY` env vars
2. macOS system proxy via `scutil --proxy` (auto-detected)

Step 2 is the trap: if the macOS system proxy is set to ClashX/v2ray/xray on
`127.0.0.1:10808` (common for users in GFW regions), it silently routes Telegram
traffic through the proxy even when no env var is set. When the proxy chain is
unstable (SSL handshake failures, pool saturation), Telegram connections degrade.

**Fix:** Bypass the macOS proxy for Telegram API by adding to `~/.hermes/.env`:
```
no_proxy=api.telegram.org,149.154.166.110,149.154.167.220
NO_PROXY=api.telegram.org,149.154.166.110,149.154.167.220
```

`should_bypass_proxy(target_hosts)` in `base.py` checks these before returning
the detected proxy URL. Fully verified on this machine — SSL handshake failures
dropped from 181/day to 0 after the change (2026-07-06).

### Lifecycle: NO_PROXY Bypass Can Become the Blockage

The NO_PROXY bypass is a **conditional fix**, not a permanent setting. When the network environment changes (especially proxy stability), the bypass itself can become the root cause of bot silence.

**When to add the bypass:**
- The proxy chain is unstable (SSL handshake failures, pool timeouts)
- Direct `curl https://api.telegram.org/bot<token>/getMe` works within 5s (no GFW blocking)
- The bypass resolves the problem (SSL failures drop to 0)

**When to REMOVE the bypass:**
- Direct `curl https://api.telegram.org/bot<token>/getMe` times out (>10s, GFW blocking Telegram IPs)
- But `curl -x socks5://127.0.0.1:10808 https://api.telegram.org/bot<token>/getMe` succeeds
- The proxy is otherwise healthy (`curl -x socks5://127.0.0.1:10808 https://httpbin.org/ip` returns quickly, xray process running)

**CRITICAL testing pitfall (2026-07-10):** `source ~/.hermes/.env` loads `no_proxy`/`NO_PROXY` into the current shell, which overrides curl's `-x` flag even with `--noproxy '*'` (that flag only works for HTTP proxy, not SOCKS5). Always `unset no_proxy NO_PROXY` before testing proxy connectivity to Telegram API:
```bash
unset http_proxy HTTP_PROXY https_proxy HTTPS_PROXY no_proxy NO_PROXY all_proxy ALL_PROXY
curl -s --max-time 10 -x socks5://127.0.0.1:10808 "https://api.telegram.org/bot${TOKEN}/getMe"
```

**Diagnostic sequence for "retrying" state + API timeout (verified 2026-07-10):**
1. Check gateway state: `cat ~/.hermes/gateway_state.json` → look for `telegram.state = "retrying"` and fallback IP failures in gateway.log
2. Check for NO_PROXY: `grep -i "^no_proxy\|^NO_PROXY" ~/.hermes/.env` — if `api.telegram.org` appears, the bypass may be the blockage
3. Test proxy health (clean env): `unset no_proxy NO_PROXY; curl -s --max-time 10 -x socks5://127.0.0.1:10808 "https://httpbin.org/ip"`
4. Test Telegram via proxy (clean env): `unset no_proxy NO_PROXY; curl -s --max-time 10 -x socks5://127.0.0.1:10808 "https://api.telegram.org/bot${TOKEN}/getMe"`
5. If proxy works and direct fails → remove NO_PROXY bypass

**Fix:**
```bash
sed -i '' '/^no_proxy=api\.telegram\.org/d; /^NO_PROXY=api\.telegram\.org/d' ~/.hermes/.env
launchctl stop ai.hermes.gateway && sleep 3 && launchctl start ai.hermes.gateway
```

**Root cause of the environment flip:** Proxy stability is the independent variable. When the proxy recovers, the bypass becomes harmful because direct Telegram connectivity from behind the GFW remains inherently unreliable. The fix has a natural lifecycle tied to proxy health — not set-and-forget.

### Location Change: Stale Proxy from Network Migration

When the user's Mac moves between network environments (home ↔ library ↔ café), the macOS system proxy (`scutil --proxy`) remains set to the original SOCKS5 address, but the actual proxy service (xray/ClashX) may not be available in the new location. The gateway auto-detects the stale proxy → all Telegram connections fail with empty `ConnectError: ` (no SSL alert, just a dead endpoint).

**Signs of stale-proxy-from-location-change:**
- `ConnectError: ` (empty error message, no `[SSL:*]` prefix) in gateway.log — the proxy endpoint is unreachable, not just unstable
- `scutil --proxy` shows SOCKS5 127.0.0.1:10808, but `curl -x socks5://127.0.0.1:10808 https://httpbin.org/ip` fails or times out
- `curl -s --max-time 10 https://api.telegram.org/bot<TOKEN>/getMe` succeeds from the new network
- Gateway state says `"connected"` but `updated_at` is from hours ago (stale timestamp from old location)
- **Contrast with SSL-failure pattern** (same-location proxy instability): SSL failures show `SSLV3_ALERT_HANDSHAKE_FAILURE` with `[SSL:*]` prefix. Empty `ConnectError: ` means the proxy itself is not reachable.

**Fix:**
Add NO_PROXY bypass for Telegram API (direct access works from the new network): 
```bash
echo 'no_proxy=api.telegram.org,149.154.166.110,149.154.167.220
NO_PROXY=api.telegram.org,149.154.166.110,149.154.167.220' >> ~/.hermes/.env
```
Then restart gateway: `launchctl stop ai.hermes.gateway && sleep 3 && launchctl start ai.hermes.gateway`

**Pitfall — NO_PROXY bypass can be lost during .env maintenance:**
If `.env` gets rewritten (scp template, sed replacement, user edits, or an earlier fix that removed it), the no_proxy lines may be silently dropped. Always verify after any .env change:
```bash
grep -i "^no_proxy\|^NO_PROXY" ~/.hermes/.env
```
If missing and direct Telegram access works, re-add the bypass.

**When direct Telegram does NOT work from the new network:**
If `curl -s --max-time 10 https://api.telegram.org/bot<TOKEN>/getMe` fails (connection timeout), the new network may fully block Telegram (GFW). In that case:
1. Check if a working proxy is available in the new location (curl -x socks5://127.0.0.1:10808 --max-time 10 https://httpbin.org/ip)
2. If proxy works → remove NO_PROXY bypass if set, keep using the proxy
3. If no working proxy at all → gateway cannot function from this location

**Diagnostic sequence for location-change bot silence:**
1. User says "地址换掉了" or similar → immediately rescan network: `ifconfig` for IP, `netstat -rn` for gateway, `scutil --proxy` for proxy settings
2. Test direct Telegram connectivity: `curl -s --max-time 10 https://api.telegram.org/bot<TOKEN>/getMe`
3. Test proxy health: `curl -s --max-time 10 -x socks5://127.0.0.1:10808 https://httpbin.org/ip`
4. Check NO_PROXY state: `grep -i "^no_proxy\|^NO_PROXY" ~/.hermes/.env`
5. Branch: direct works + proxy dead → add NO_PROXY bypass; direct dead + proxy works → remove NO_PROXY bypass; both dead → location has no Telegram path

### Location Change: Stale Proxy from Network Migration

When the user's Mac moves between network environments (home ↔ library ↔ café), the macOS system proxy (`scutil --proxy`) remains set to the original SOCKS5 address, but the actual proxy service (xray/ClashX) may not be available in the new location. The gateway auto-detects the stale proxy → all Telegram connections fail with empty `ConnectError: ` (no SSL alert, just a dead endpoint).

**Signs of stale-proxy-from-location-change:**
- `ConnectError: ` (empty error message, no `[SSL:*]` prefix) in gateway.log — the proxy endpoint is unreachable, not just unstable
- `scutil --proxy` shows SOCKS5 127.0.0.1:10808, but `curl -x socks5://127.0.0.1:10808 https://httpbin.org/ip` fails or times out
- `curl -s --max-time 10 https://api.telegram.org/bot<TOKEN>/getMe` succeeds from the new network
- Gateway state says `"connected"` but `updated_at` is from hours ago (stale timestamp from old location)
- **Contrast with SSL-failure pattern** (same-location proxy instability): SSL failures show `SSLV3_ALERT_HANDSHAKE_FAILURE` with `[SSL:*]` prefix. Empty `ConnectError: ` means the proxy itself is not reachable.

**Fix:**
Add NO_PROXY bypass for Telegram API (direct access works from the new network):
```bash
echo 'no_proxy=api.telegram.org,149.154.166.110,149.154.167.220
NO_PROXY=api.telegram.org,149.154.166.110,149.154.167.220' >> ~/.hermes/.env
```
Then restart gateway: `launchctl stop ai.hermes.gateway && sleep 3 && launchctl start ai.hermes.gateway`

**Pitfall — NO_PROXY bypass can be lost during .env maintenance:**
If `.env` gets rewritten (scp template, sed replacement, user edits, or an earlier fix that removed it), the no_proxy lines may be silently dropped. Always verify after any .env change:
```bash
grep -i "^no_proxy\|^NO_PROXY" ~/.hermes/.env
```
If missing and direct Telegram access works, re-add the bypass.

**When direct Telegram does NOT work from the new network:**
If `curl -s --max-time 10 https://api.telegram.org/bot<TOKEN>/getMe` fails (connection timeout), the new network may fully block Telegram (GFW). In that case:
1. Check if a working proxy is available in the new location (`curl -x socks5://127.0.0.1:10808 --max-time 10 https://httpbin.org/ip`)
2. If proxy works → remove NO_PROXY bypass if set, keep using the proxy
3. If no working proxy at all → gateway cannot function from this location

**Diagnostic sequence for bot silence when user reports location change:**
1. User says "地址换掉了" or similar → immediately rescan network: `ifconfig` for IP, `netstat -rn` for gateway, `scutil --proxy` for proxy settings
2. Test direct Telegram connectivity: `curl -s --max-time 10 https://api.telegram.org/bot<TOKEN>/getMe`
3. Test proxy health: `curl -s --max-time 10 -x socks5://127.0.0.1:10808 https://httpbin.org/ip`
4. Check NO_PROXY state: `grep -i "^no_proxy\|^NO_PROXY" ~/.hermes/.env`
5. Branch: direct works + proxy dead → add NO_PROXY bypass; direct dead + proxy works → remove NO_PROXY bypass; both dead → location has no Telegram path

### Residual issue: RemoteProtocolError after NO_PROXY removal

After removing the bypass, `RemoteProtocolError: Server disconnected without sending a response` may appear. This is a DIFFERENT mechanism — Telegram server closes the HTTP connection between polls (likely GFW/ISP NAT dropping idle long-poll connections). The gateway auto-recovers within ~4–13 seconds each time via PTB's built-in polling reconnect. Do not merge with SSL/proxy issues in reports.

## xray IPv6-Only Binding Pitfall (macOS)
   Then point remote devices to `192.168.1.8:10809`.

2. **v2rayN config** — edit inbound to listen on `0.0.0.0` instead of `::`:
   - Change `"listen": "::"` to `"listen": "0.0.0.0"` in the inbound config
   - Or add a separate IPv4 inbound on a different port

3. **IPv6 direct** — use the Mac's link-local IPv6 address from the remote device:
   ```bash
   ifconfig en0 | grep inet6 | grep fe80
   ```

**Impact:** This affects any remote Hermes agent (Mi6/Mi8/other bots) that uses the Mac as a proxy gateway. The Mac itself is unaffected (localhost connections work). Fixing this restores Telegram proxy connectivity for remote agents.

## Verification

- tail -f /Users/macos/.hermes/logs/gateway.log | grep -E "Pool timeout|client refreshed|Connected"
- No "Pool timeout" lines after restart = clean
- "General HTTP client refreshed" every refresh_interval seconds = periodic refresh working
- launchctl print gui/501/ai.hermes.gateway to verify env vars are loaded

## References

- references/api-server-browser-extension.md: Hermes Gateway API Server setup + hermes-browser-extension Chrome侧边栏集成（共用同一 gateway 进程，独立端口 8642，CORS 配置，构建/加载步骤）
- references/pool-timeout-dual-pool-2026-07-01.md: Dual-pool architecture (aiohttp vs httpx) confirmed — aiohttp always 1 connection, httpx pool is the one that fills up. Real-time pool snapshot technique via log deque lines. Historical statistics (4217/599/220). Open questions for deeper diagnosis.
- references/telegram-pool-timeout-2026-06-30.md: Full session log — verified root cause (upstream model 429, not SOCKS5 RST), code-level diagnostics (PTB pool separation already done), three fix directions assessed against actual code, watchdog provider fix
- references/xunfei-10163-tools-incompatibility.md: Xunfei API does not support tools/function calling — watchdog cron model mismatch diagnosis and fix
- references/sysctl-tcp-keepalive.md: macOS TCP keepalive parameter reference
- references/bot-not-responding-diagnosis-2026-06-26.md: Session log — upstream NVIDIA 429 causing bot silence; error.log vs gateway.log distinction
- references/all-providers-exhausted-2026-07-14.md: All upstream providers exhausted simultaneously — OmniRoute free model 429 + all 3 NVIDIA keys at capacity. Key diagnostic: timestamp delta >10min between inbound message and Send failed. Fix: switch model, not restart.
- references/telegram-send-test-2026-06-29.md: Quick test of hermes send command and verification steps

- references/telegram-status-check.md: Quick status check commands and style note
- references/telegram-send-file-via-bot-api.md: Send file attachments to Telegram groups/DMs via Bot API `sendDocument` endpoint. Use when user asks "把文件发到群里" or "作为附件".
- references/bot-not-responding-three-layer-diagnosis-2026-07-01.md: 三步诊断法精确定位"不回话"根因 — event loop → 线程池 → HTTP 连接池。含本环境实测数据（51次pool timeout、4次gateway重启、压缩与pool timeout的相关性分析）
- references/ssl-canary-pool-fill-2026-07-02.md: SSL handshake failure as pool timeout canary — empirical fill timing (~28 min at pool_size=512), dual-cycle measurement, cron amplification data, and upstream model 429 correlation
- references/stream-leak-code-path-2026-07-02.md: Code-level root cause — TCP stream not closed on TLS failure in httpcore AsyncSocks5Connection. Full call stack, leak point at line 294-295, pool-slot vs TCP distinction, cascade path from leaked socket to PoolTimeout, and fix proposal.
- references/omniroute-down-bot-silent-2026-07-12.md: OmniRoute not running + direct provider config = bot silent when all providers fail simultaneously. Diagnostic flow: lsof :20128 → error.log → fix.
- references/restart-loop-no-proxy-fix-2026-07-14.md: Pool timeout restart loop pattern — when repeated restarts waste time and NO_PROXY bypass is the real fix. Contains the 3-cycle diagnostic pattern from 2026-07-14.
- scripts/http_to_socks_proxy.py: Standalone HTTP→SOCKS5 bridge proxy (asyncio). Listens on 10809, forwards to xray SOCKS5 on 10808. Translates SOCKS5 failures to HTTP 502.inction, cascade path from leaked socket to PoolTimeout, and fix proposal.: OmniRoute not running + direct provider config = bot silent when all providers fail simultaneously. Diagnostic flow: lsof :20128 → error.log → fix.
- scripts/http_to_socks_proxy.py: Standalone HTTP→SOCKS5 bridge proxy (asyncio). Listens on 10809, forwards to xray SOCKS5 on 10808. Translates SOCKS5 failures to HTTP 502.