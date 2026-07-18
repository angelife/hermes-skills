# 通过 OpenBridge CDP 控制远程 AI Agent（QwenPaw）

> 本参考与 `web-ai-cdp-bridge` 核心技能共用 OpenBridge CDP 工具栈，但用途不同：
> 原始技能是「问 ChatGPT/Claude」，这里是「指挥远程 AI Agent（木同学）」

## 场景

土同学（Hermes）需要向远程 AI Agent（木同学，QwenPaw 平台）下发指令并取回回复。木同学跑在浏览器端的 QwenPaw Console 聊天界面，没有原生 API 可用（或 API 令牌过期）。

## 架构

```
mu CLI (/Users/macos/.local/bin/mu)
  ↓ HTTP POST
OpenBridge daemon (:10088)
  ↓ CDP
已登录 Chrome 标签页（QwenPaw Web Console）
  ↓
木同学 AI Agent
```

## mu CLI 设计思路

### 两条路径，先 REST 再回退

1. **首选：云端 REST API** — `/api/console/chat` POST（本地 localhost 免 token）
   - 格式：SSE 流式响应
   - 请求字段：`session_id`, `user_id`, `channel`, `input`（OpenAI 消息格式）
   - 响应为 `data: {...}` 事件流，status 含 `created/in_progress/completed/failed`
   - 需同源或 localhost，remote 需 X-Agent-Id + Authorization

2. **回退：OpenBridge CDP**（浏览器已登录时）
   - `browser_type` 向输入框写消息
   - `browser_evaluate` 触发提交（dispatch KeyboardEvent Enter）
   - 轮询 `document.body.innerText` 等回复出现

### 实现要点

#### 消息发送（browser_type + JS 提交）

```python
# 1. 找输入框（browser_snapshot 或 browser_evaluate）
ref = 'editable-ref'  # 从 snapshot 拿到
cmd('browser_type', {'tabId': tabId, 'ref': ref, 'text': text})

# 2. 用 JS 触发发送（browser_press 不可用）
cmd('browser_evaluate', {
    'tabId': tabId,
    'expression': '''
const ta = document.querySelector('textarea, [contenteditable="true"]');
if (ta) {
  ta.dispatchEvent(new KeyboardEvent('keydown', {
    key: 'Enter', code: 'Enter', keyCode: 13, which: 13,
    bubbles: true, cancelable: true
  }));
  ta.dispatchEvent(new KeyboardEvent('keyup', {
    key: 'Enter', code: 'Enter', keyCode: 13, which: 13,
    bubbles: true, cancelable: true
  }));
}
'''
})
```

#### 等回复（轮询文本变化）

```python
import time, json
for i in range(30):
    time.sleep(3)
    res = cmd('browser_evaluate', {
        'tabId': tabId,
        'expression': 'JSON.stringify({len: document.body.innerText.length, last: document.body.innerText.slice(-500)})'
    })
    # 看最新消息是否含预期的回复前缀
```

### 已知陷阱

| 陷阱 | 正确做法 |
|------|---------|
| 同一标签页已有 context 累计过多 | `/new` 开新会话页后继续操作 |
| 免费模型 429 MODEL_QUOTA_EXCEEDED | 换模型/等额度恢复，不影响 CLI 通道本身 |
| 标签页未登录（跳登录页） | 先检查 tab url 是否含 chat/ 路径，必要时 navigation |
| REST API 401（token 过期） | 回退 OpenBridge CDP 路径，不等修 token |
| 提交后等不到回复 | 增大轮询超时（默认 90s），或检查模型是否重度限流 |

## 配置步骤

```bash
mkdir -p ~/.config/mu
cat > ~/.config/mu/config.json <<'EOF'
{
  "openbridge_port": 10088,
  "chat_url": "https://<workspace>.qwenpaw.platform.agentscope.io/chat/<session>",
  "prefix": "[土同学] ",
  "wait_seconds": 90,
  "agent_id": "default"
}
EOF

# 身份写入（只需要一次）
mu send "你从现在起是木同学。身份：五行舰队云端常驻执行节点。上级：土同学。..."
```

## REST API 直连（local 免 token）

QwenPaw API 文档关键点：
- 端点：`POST http://localhost:8088/api/console/chat`
- 头部：`X-Agent-Id: default`
- localhost 请求自动免认证
- 请求体格式（OpenAI 风格）：

```json
{
  "input": [{"role": "user", "content": [{"type": "text", "text": "..."}]}],
  "session_id": "unique-session",
  "user_id": "tu-classmate",
  "channel": "console"
}
```

- 响应为 SSE 流，解析 `data:` 行，找 status=completed 的 output