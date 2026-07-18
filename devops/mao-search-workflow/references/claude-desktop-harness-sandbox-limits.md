# Claude Desktop / Harness Sandbox Execution Limits

Observed/reported behavior useful when diagnosing local CLI vs browser/extension command failures in managed Claude runtimes.

## Confirmed signals
- `opencli status` may succeed (lightweight, no browser pipeline).
- `opencli weixin download` and similar browser-extension-dependent commands can fail even when daemon/extension are healthy on host.
- Host-shell background jobs can succeed while the same invocation fails inside a managed runtime.

## Sources
- GitHub `anthropics/claude-code` #71152: Desktop harness-level sandbox blocks bash commands to localhost/network endpoints.
- GitHub `anthropics/claude-code` #22542: Desktop MCP tool calls unstable in the 30–60s range; 60s+ often yields "No result received".
- GitHub `anthropics/claude-code` #59989: Desktop Local Agent Mode can terminate with exit 143 after several minutes of wall-clock time.
- GitHub `anthropics/claude-code` #46869 / #58201: Desktop vs terminal Claude Code compete for Chrome Native Messaging host registration.

## Diagnostic rule
Do not infer browser/extension reachability from lightweight local CLI probes. If the symptom only appears for extension-driven flows, test:
1. lightweight local CLI command
2. lightweight browser/extension command in same runtime
3. timing/long-running behavior in same runtime

Only after these three can you distinguish: host runtime success, timeout/cutoff, or real architecture boundary.

## Hard pitfall
A host-shell background job succeeding does **not** prove the same path is reachable inside a managed/sandboxed runtime. Do not use host background success to declare `A` true or `B` false. The only way to distinguish architecture boundary from timeout/cutoff is to trigger the command **from inside the exact runtime under test**, then observe whether the daemon/extension received the request and whether a detached process can complete.
