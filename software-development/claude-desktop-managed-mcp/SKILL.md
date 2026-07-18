---
name: claude-desktop-managed-mcp
description: 在 Claude Desktop 的 3P/managed 模式下接入自定义 MCP server。覆盖 managed config 路径、managedMcpServers schema、桥接方式、以及 Desktop UI/runtime 分叉的排查。
tags:
  - claude-desktop
  - mcp
  - 3p
  - managed-config
---

# Claude Desktop Managed MCP

## When to Use
Claude Desktop App 在第三方托管/企业配置模式下（3P / CC Switch / cowork mode），用户自定义 MCP 需要写入 managed config，而不是标准用户 config。

## Hard Rules

### 1. Config path
- 标准模式：`~/Library/Application Support/Claude/claude_desktop_config.json`
- 3P managed 模式：`~/Library/Application Support/Claude-3p/configLibrary/<managed-id>.json`
- `Claude-3p/claude_desktop_config.json` 不是 Desktop App 实际读取的 managed config
- Desktop 的 runtime 日志目录：macOS 上优先看 `~/Library/Logs/Claude-3p/main.log`

### 2. Field name
- 标准模式：顶层 `mcpServers` object/map
- 3P managed 模式：顶层 `managedMcpServers` **array**
- `mcpServers` 在 3P 模式下会被静默忽略

### 3. Array entry schema
每个 entry 至少需要：
- `name`: server name
- `transport`: `stdio` 或 `http` / `sse`
- stdio 时：`command` + `args`
- http 时：`url` / `headers` / `oauth` 等

### 4. Bridge choice
- Desktop App 只支持 STDIO transport
- HTTP-only Hindsight 或其他 HTTP MCP 要通过 `npx -y mcp-remote <url> --transport http-only` 桥接
- 桥接命令写在 `command` / `args` 里，不是 `url`

### 5. UI vs runtime split
- Desktop 的可用工具列表/runtime tool-call 会读 `managedMcpServers`
- Desktop 的 UI registry 可能不展示 managed entry
- 不要用 UI 可见性判断是否接入成功；以实际 `mcp__<name>__<tool>` 可调用为准

## Verification
- 服务端探活：`curl -sS http://127.0.0.1:8888/mcp/hermes/` 返回 200
- 服务端工具数：服务端 `tools/list` 数量是上限；Desktop 实际暴露数量以 runtime 可调用为准
- Desktop 侧：看 `~/Library/Logs/Claude-3p/main.log` 是否有 `tool permission request` / `Turn succeeded`
- 运行态：`pgrep -fl 'Claude'` 应能看到主进程和 helper 进程
- 真实验证：在 Desktop 会话里直接问“你现在能看到的 hindsight 工具有哪些”。不要只看第一次只调用到 `get_bank` 就下“被裁剪 29→1”的结论（常见误判）

## Pitfalls
- `managedMcpServers` 写错成 object → `Failed to parse managed config`
- 把条目写到 `Claude-3p/configLibrary/_meta.json` → 只会更新元数据，不会注册 server
- 在非生效 managed-id 的文件里写配置 → 不会加载
- 改完配置后只关窗口不完全退出 Desktop → 进程缓存 config，不会 reload
- 用 `localhost` 而不是 `127.0.0.1` → IPv6 解析可能绕到代理，Bridge 行为不一致
- 期望 UI “Connectors” 立刻显示 managed entry → 3P managed 注入通常不走 UI registry 展示层
- **Desktop 的 code execution 不能可靠跑 browser/extension 类 CLI。** `opencli status` 能成功，不表示 OpenCLI 在 Desktop 里完整可用。GitHub #71152 表明 Desktop 的 harness-level sandbox 会 block localhost/network endpoints；#22542 表明 Desktop MCP tool call 在约 30–60s 区间不可靠，60s+ 经常报 "No result received"；#59989 表明 Desktop Local Agent Mode 存在约 5 分钟 wall-clock cycle limit 导致 exit 143。需要浏览器扩展链路的 OpenCLI 命令应回本机终端/Hermes 执行，不要继续在 Desktop 里测。See `references/claude-desktop-code-execution-limits-2026-07-06.md` for detail.