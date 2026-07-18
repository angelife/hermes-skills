# OpenBridge 问答工作流 (ask-openbridge.js)

## 概述

取代旧版 CDP `ask.js`，通过 OpenBridge Chrome 扩展桥接（端口 10088）与 Web AI 交互。
reuse 用户已有登录会话，无需每次重新登录。

## 架构

```
用户/Agent → ask-openbridge.js → OpenBridge API (127.0.0.1:10088) → Chrome 扩展 → AI 网页
```

## 文件

- `~/.hermes/skills/web-ai-cdp-bridge/scripts/ask-openbridge.js` — 主入口（仅 Gemini）
- `~/.hermes/skills/web-ai-cdp-bridge/scripts/ask.js` — 旧版（已弃用，仅 CDP fallback）

## 使用（Gemini — ask-openbridge.js）

```bash
node ~/.hermes/skills/web-ai-cdp-bridge/scripts/ask-openbridge.js "你的问题"
```

脚本自动查找/新建 Gemini 标签页，打字→提交→等回复→返回结果。

## 工作原理（ask-openbridge.js）

1. 查找已打开的 Gemini 标签页（`gemini.google.com/app`）
2. 没找到则新建标签页并等待加载
3. 通过 `browser_snapshot` 定位输入框
4. 用 `browser_type` 输入提示词
5. 用 `browser_send_keys` 按 Enter 发送
6. 每 3 秒轮询一次页面快照提取回复文本

## 通用 OpenBridge API 工作流（任意 AI 标签页）

`ask-openbridge.js` 只适配 Gemini，但底层 API 对 ChatGPT/Claude/Perplexity 等任意标签页通用。直接调用 OpenBridge API：

```bash
# 1. 列出所有标签页
curl -s http://127.0.0.1:10088/command -X POST \
  -H "Content-Type: application/json" \
  -d '{"toolName":"browser_list_tabs","args":{}}'

# 返回示例：各标签页的 tabId、url、title
```

```bash
# 2. 选中目标标签页
curl -s http://127.0.0.1:10088/command -X POST \
  -H "Content-Type: application/json" \
  -d '{"toolName":"browser_select_tab","args":{"tabId":<id>}}'
```

```bash
# 3. 打字到输入框
curl -s http://127.0.0.1:10088/command -X POST \
  -H "Content-Type: application/json" \
  -d '{"toolName":"browser_type","args":{"tabId":<id>,"text":"你的问题"}}'
```

```bash
# 4. 提交（快捷键因平台而异）
# ChatGPT: Enter
curl -s http://127.0.0.1:10088/command -X POST \
  -H "Content-Type: application/json" \
  -d '{"toolName":"browser_send_keys","args":{"tabId":<id>,"keys":"Enter"}}'
# Claude: Cmd+Enter
curl -s http://127.0.0.1:10088/command -X POST \
  -H "Content-Type: application/json" \
  -d '{"toolName":"browser_send_keys","args":{"tabId":<id>,"keys":"Meta+Enter"}}'
```

```bash
# 5. 等回复后读内容
curl -s http://127.0.0.1:10088/command -X POST \
  -H "Content-Type: application/json" \
  -d '{"toolName":"browser_snapshot","args":{"tabId":<id>}}'
```

### 注意事项

- **`browser_type` 只打字不提交** — 无论 `text` 末尾是否带 `\n`，都不会触发发送。必须单独调用 `browser_send_keys`
- **回复提取** — `browser_snapshot` 返回 Accessibility Tree。长回复可能被截断或分散在多个 `StaticText`/`InlineTextBox` 节点中
- **当前活跃标签页** — `browser_snapshot` 不传 tabId 返回当前选中标签页的内容

## 关键参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| 超时 | 180s | 在 `TIMEOUT` 常量中设置 |
| 轮询间隔 | 3s | `sleep(3000)` |
| API 端口 | 10088 | `OPENBRIDGE_PORT` env 可覆盖 |

## OpenBridge 状态检查

```bash
# 查看 daemon 状态
node ~/.openbridge/repo/packages/daemon/dist/cli/index.js status

# 预期输出（健康）：
# Daemon: Running (PID xxxxx)
# WebSocket: ws://127.0.0.1:10087/bridge
# Local API: http://127.0.0.1:10088
# Extension: Connected (2)
```

## 局限性

1. **`ask-openbridge.js` 脚本只适配 Gemini** — 脚本硬编码了 `gemini.google.com/app` URL 检测。但底层 OpenBridge API 对任意标签页通用
2. **不能处理 CAPTCHA** — OpenBridge 不做自动化 CAPTCHA 解决
3. **依赖 Chrome 保持打开** — 需要 Chrome 进程和 OpenBridge 扩展均存活
4. **回复提取基于页面文本** — 复杂排版时可能丢失部分内容
5. **不处理多轮对话** — 每次调用从当前标签页状态继续，不清历史

## 与 CDP 对比

| 维度 | CDP (ask.js) | OpenBridge (ask-openbridge.js) |
|------|-------------|-------------------------------|
| 检测率 | 高（Google 严格） | 低（复用已有会话） |
| 额外端口 | 9222 | 10088 |
| Chrome 启动方式 | 专用 debug 实例 | 使用用户现有 Chrome |
| 源保持 | 每次新实例 | 保持登录状态 |
| 状态 | 已弃用 | 当前使用 |
