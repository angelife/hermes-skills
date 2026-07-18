# Claude Desktop code execution browser-class limitation
Date: 2026-07-06

## Verified externally
- `anthropics/claude-code#71152`: "Bash commands to localhost / network endpoints are blocked by the harness-level sandbox in Claude Desktop."
- `anthropics/claude-code#22542`: Desktop MCP tool call is unreliable above ~30–60s; 60s+ commonly returns "No result received."
- `anthropics/claude-code#59989`: Desktop Local Agent Mode can crash around ~5 minutes wall-clock with exit 143.
- `anthropics/claude-code#46869` / `#58201`: Desktop and terminal Claude Code register competing native messaging hosts; desktop-side registration can preference or block the other client.
- Desktop docs (`code.claude.com/docs/en/desktop`): Chat / Cowork / Code tabs exist; MCP configured in managed config is loaded by the app.

## Session finding
- OpenCLI `weixin download` succeeds in host terminal, fails in Claude Desktop Code tab.
- OpenCLI `browser state` also times out under Claude execution environments, indicating the issue is not Desktop-only; browser-extension commands are unreliable from Claude's execution harness.
- Combined model: `status`-class commands can succeed because they are short and may not need extension browser state; browser-class commands fail because the harness path to extension-driven browser state is restricted or unstable.

## Decision rule
When a task needs OpenCLI browser/extension/download behavior, do not attempt it from Claude Desktop or Claude Code execution harnesses. Run it from the host terminal / Hermes.
