---
name: browser-provider
description: "Hermes 浏览器执行后端抽象层 — 三层架构（BrowserProvider / ChallengeHandler / HumanAssist），可插拔 CDP / Playwright / BrowserAct 后端"
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos]
metadata:
  hermes:
    tags: [Browser, CDP, CAPTCHA, Web-AI, Automation]
---

# Browser Provider — 三层抽象架构

## Trigger

当需要让 AI Agent 与 Web 版浏览器交互（Gemini Web、ChatGPT Web、Claude Web）时，使用本架构。

## 架构原则

不要把所有能力塞进一个大接口。拆成三层：

```
Layer 1: BrowserProvider   — navigate / click / input / screenshot
Layer 2: ChallengeHandler  — detect / solve / escalate (captcha, login)
Layer 3: HumanAssist       — request / wait / resume (manual override)
```

## 实现位置

`~/.hermes/skills/web-ai-cdp-bridge/provider/`

### 文件清单

- `interface.py` — 三层抽象接口 + 数据类（PageState, ImageData, ChallengeInfo 等）
- `cdp_provider.py` — CDP 后端实现，包裹现有 Node.js 脚本
- `challenge.py` — CAPTCHA 状态机（DETECTED → AUTO_SOLVING → HUMAN_REQUESTED → RESOLVED）
- `human_assist.py` — ConsoleHumanAssist / TelegramHumanAssist

### 使用方式

```python
from provider import create_provider
from provider.challenge import ChallengeStateMachine

p = create_provider("cdp")
result = await p.ask("prompt", "gemini")
```

## 迁移路线（按优先级排序）

| Phase | 内容 | 理由 |
|-------|------|------|
| 1 | BrowserProvider 抽象层 | 已完成，降低耦合 |
| 2 | **OpenBridge 后端**（端口 10088） | 当前偏好，替代 CDP |
| 3 | Playwright persistent context + stealth patches | Intel Mac 可用，改动小 |
| 4 | ChallengeHandler 自动解验证码 | 依赖 BrowserAct 或自建 |
| 5 | HumanAssist 人工接管标准化 | 状态机 + 截图 + 通知 |
| 6 | API Provider fallback | 长期稳定兜底 |

### OpenBridge 操作（2026-07-16 已验证，当前主力）

OpenBridge daemon 运行在 `127.0.0.1:10088`，支持以下 browser 操作：

| 操作 | 方法 | 注意事项 |
|------|------|---------|
| 列举标签页 | `browser_list_tabs` | 无参数 |
| 选择标签页 | `browser_select_tab` | 需 tabId |
| 执行JS | `browser_evaluate` | **替代 browser_press**（后者被 daemon 禁用） |
| 截图 | `browser_snapshot` | 返回无障碍树节点 |
| 点击 | `browser_click` | 需 ref ID |
| 输入 | `browser_type` | 需 ref ID |

**关键技巧：**
- `browser_press` 已被 daemon 禁用 → 用 `browser_evaluate` 执行 JavaScript 模拟键盘事件
- ChatGPT/Gemini 标签页登录状态持久保持（daemon 重启前不丢失）
- 提交问题到 ChatGPT 流程：`browser_click(输入框)` → `browser_type(输入框, 问题)` → `browser_evaluate(JS触发回车)`

### 后端切换

| 后端 | 状态 | 入口 |
|------|------|------|
| CDP (旧) | ❌ 已弃用 | `ask.js` |
| OpenBridge | ✅ 当前使用 | `ask-openbridge.js`，端口 10088 |

## Pitfalls

- **不要**用 undetected-chromedriver — 它是 Selenium 生态，换它等于重写所有交互逻辑
- **不要**把 BrowserAct 当"CAPTCHA 解决器" — 它只是浏览器基础设施增强器，能降频但不能消除
- **不要**期待 stealth = CAPTCHA 消失 — Google 风控综合判断（IP信誉、Cookie历史、行为模式），不是单一指纹检测
- **不要**在 Provider 接口里直接暴露 DOM 操作 — 复杂交互走 ask.js 封装好的 Node.js 脚本
- **不要**在 Provider 接口里包含验证码解决逻辑 — 那是 ChallengeHandler 的职责
- **OpenBridge 支持 Gemini 和 ChatGPT（2026-07-16 验证）** — 通过 `browser_evaluate` 提交问题到 ChatGPT（替代被 daemon 禁用的 `browser_press`）。Gemini 和 ChatGPT 标签页的登录状态持久保持。Claude 标签页尚未测试。

## Complementary Tools

### Browser-BC (Journey Forge Local) — 录制操作蒸馏技能

`~/Browser-BC/` — 端口 8099

Record browser operations → auto-distill into SKILL.md for reuse. The output is a skill package (SKILL.md + TRACE_GUIDE.md + meta.json + evidence.jsonl) that an agent reads before executing via OpenBridge.

**Workflow:**
1. Chrome extension records your clicks/inputs
2. Server segments → classifies → buckets → distills into SKILL.md
3. Agent reads SKILL.md, executes steps via OpenBridge (port 10088)

**Pitfalls:**
- `SF_LLM_BASE` must NOT include `/v1` suffix — the harness code appends `/v1/chat/completions` automatically
- `.env.local` must be exported into environment before starting server: `export $(grep -v '^#' .env.local | xargs) && python3 server/server.py`
- DeepSeek balance insufficient → use NVIDIA API: `https://integrate.api.nvidia.com/v1` with `meta/llama-3.3-70b-instruct` for distillation

### NanoBrowser — 一次性浏览器自动化

Chrome Web Store extension, 13k+ stars. Multi-agent (Planner + Navigator) runs browser tasks from natural language. Supports OpenAI-compatible providers including NVIDIA API.

**Configuration:**
- API Base URL: `https://integrate.api.nvidia.com/v1`
- Planner model: `meta/llama-3.3-70b-instruct`
- Navigator model: `meta/llama-3.1-8b-instruct`
- API Key: any NVIDIA nvapi key

**When to use which:**
| Tool | Best for |
|------|---------|
| Browser-BC | Fixed workflows repeated often (login, data entry, crawl) |
| NanoBrowser | One-shot exploratory tasks (research, comparison, data gathering) |

## Operational Guide

`references/cdp-operational-gaps.md` — macOS 上 ask.js/CDP 的实际操作坑与 Workaround（node_modules 缺失、Chrome CDP 端口绑定失败、Cloudflare 拦截时的 fallback）。

**关键顺序：**
1. 先检查 `scripts/node_modules/` 是否存在 → 没有就 `npm install`
2. Chrome CDP 起不来 → `pkill -f "Google Chrome"` + `--user-data-dir=/tmp/chrome_cdp_$$` + `--remote-debugging-port=9222`
3. 全失败了 → 用 `references/cdp-operational-gaps.md` 方案C（API 直调）作为 fallback

## Related

- `hermes-gemini-web` — Gemini 专用技能（基于此架构）
- `web-ai-cdp-bridge` — 现有 CDP 桥接实现
