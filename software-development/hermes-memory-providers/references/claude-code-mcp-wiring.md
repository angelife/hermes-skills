# Claude Code CLI + Hindsight MCP wiring

## 结论
Claude Code CLI 的共享记忆比 Desktop 更容易接，因为它的 MCP 配置是本地 JSON，没有 managed config / UI 分裂。

## 已知可行前提
- Hindsight 服务可读：`http://127.0.0.1:8888/mcp` 至少返回 SSE / JSON-RPC
- 已有 `--mcp-config` / `.mcp.json` 配置入口
- 当前版本下未找到官方 `hindsight-local-mcp` stdio 命令；优先走 HTTP MCP 或 Hermes 自带 MCP 工具

## 推荐方案
1. 继续用 Hermes 作为 Claude Code 的“外部记忆客户端”
2. 在需要 retain/recall 时，Hermes 直接调 hindsight API
3. 不要把 Desktop 的管理员托管配置模式套到 CLI

## 待确认
- Claude Code CLI 是否接受本地 JSON MCP 文件并持久注入 hindsight tools
- 是否有官方/社区 hindsight MCP stdio wrapper 可直接配到 `.mcp.json`
