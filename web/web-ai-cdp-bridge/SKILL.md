---
name: web-ai-cdp-bridge
title: "问AI — 先问ChatGPT/Claude再动手"
description: "任何技术问题卡住→立即停手→总结问题→通过OpenBridge问ChatGPT或Claude→等回复再执行。不自作主张硬试。"
category: web
triggers:
  - "问AI"
  - "问ChatGPT"
  - "问Claude"
  - "卡住了"
  - "不知道"
  - "问一下"
  - "你问问"
  - "去问"
  - "先问"
---

# 问AI — 先问ChatGPT/Claude再动手

> **本技能有两种用途：** OpenBridge CDP 桥不仅可以「问 AI」，也可以「指挥远程 AI Agent」。
> - 用途 A（原始）：向 ChatGPT/Claude 提交技术问题并取回复
> - 用途 B（拓展）：向远程 AI Agent（如木同学/QwenPaw）发送指令并等待执行结果
> 两者共用同一套浏览器 CDP 工具栈。用途 B 的详细实现见 `references/send-to-agent-cdp.md`。

## ⚠️ 正确优先级（2026-07-16 用户明确纠正）

**本技能是 SOUL.md「先问AI再动手」规则的执行器。** 正确流程（编码自 SOUL.md 和用户纠正）：

```
遇到问题卡住/不确定/尝试两次没成功：
  1. 立即停手
  2. 总结问题（环境版本 + 精确日志 + 已尝试操作）
  3. 通过 OpenBridge 同时问 ChatGPT 和 Claude
  4. 等回复再执行
```

用户在本会话中明确纠正：「让你走流程 不是问三ai么」——按 SOUL.md 流程走，先去问 AI。

**「问AI」和「读文档」是互补的：**
- 如果有相关 skill 覆盖 → 优先加载 skill
- 如果有历史经验 → session_search 查
- 如果两者都没有，自己试了 1-2 次失败 → **直接问 AI，不等第 3 次**

不要自作主张硬试超过 2 次。用户说「问题搞不定的话，就先读读原则」——原则就是先问 AI 再动手。

## 何时使用

当满足以下所有条件时：
1. 已读过官方说明书但仍不懂
2. 已尝试自己解决但失败了
3. 已搜索过社区讨论但没找到答案
4. 问题具体、可复现、有日志

## 三通道信息收集策略

遇到问题时不要只依赖浏览器。本技能有三条独立通道，互相备份：

| 通道 | 方法 | 条件 | 优先级 |
|------|------|------|--------|
| **A — OpenBridge 问 AI** | browser_evaluate/browser_type 输入提交 | OpenBridge 运行 + 浏览器已登录 | 最高 |
| **B — 搜索→NLM** | web_search → web_extract → NotebookLM | 任意网络 | 中（A 不通时的 Plan B） |
| **C — Grok API** | curl 直调 xhahlf.top/v1/chat | API Key 在 config | 次低（快速备用） |

**规则：** 通道 A 不通（CDP 故障 / Cloudflare / 标签页未登录）→ 立即切 B，不需要反复试 A。用户：「你可以用于搜索来收集资料，也可以用于提问来收集资料。」

### 通道 B：搜索收集资料 → NLM 消化

```bash
# 1. 搜索
web_search query="problem description" limit=10
# 2. 提取全文
web_extract urls=["url1","url2"]
# 3. 创建 NLM 笔记本喂资料
nlm create notebook "问题分析"
CONTENT=$(cat /tmp/search_results.md)
nlm add text <notebook_id> "$CONTENT" --title "搜索结果" --wait
# 4. 合成方案
nlm query notebook <notebook_id> "分析这些资料：根因是什么？优先级修复？"
```

### 通道 C：Grok API（快速备用）

```bash
API_KEY=$(grep 'api_key: sk-' ~/.hermes/config.yaml | head -1 | sed 's/.*api_key: //')
PAYLOAD=$(python3 -c "import json; print(json.dumps({'model':'grok-4.5','messages':[{'role':'user','content':open('/tmp/question.txt').read()}],'max_tokens':2000}))")
curl -s --max-time 120 -x http://127.0.0.1:10808 \
  https://api.xhahlf.top/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $API_KEY" \
  -d "$PAYLOAD" | python3 -c "import sys,json;d=json.load(sys.stdin);print(d.get('choices',[{}])[0].get('message',{}).get('content','ERROR'))"
```

注意：Grok API `/v1/models` 端点 403（token 不共享），`/v1/chat/completions` 正常。需通过 v2rayN 代理（10808）。

### 通道 D：让用户帮忙粘贴（仅当以上全都不通）

直接请求用户帮忙把问题贴进已打开的 ChatGPT/Claude。问题必须结构化（环境+日志+已尝试+约束），一次只问一个核心问题不超过 800 字。

## 操作流程（OpenBridge 可用时）

OpenBridge 的 `/command` API 提供了以下可用工具：
- ✅ `browser_select_tab` — 切换标签页
- ✅ `browser_snapshot` — 获取当前页面 DOM
- ✅ `browser_click` — 点击元素
- ✅ `browser_type` — 输入文字
- ✅ `browser_evaluate` — 在页面执行任意 JavaScript
- ✅ `browser_list_tabs` — 列出所有标签页
- ❌ `browser_press` — **不被允许**（不能按键盘）
- ❌ `browser_send_keys` — **不存在**
- ❌ `browser_new_tab` — 可以开标签页，但新手势需要用户登录

### 提交问题到 ChatGPT（正确方法）

```python
import json, urllib.request, time

def cmd(tool, args={}):
    data = json.dumps({"toolName": tool, "args": args}).encode()
    req = urllib.request.Request("http://127.0.0.1:10088/command", data=data,
        headers={"Content-Type": "application/json"})
    return json.loads(urllib.request.urlopen(req, timeout=10).read())

# 1. 确认 ChatGPT 标签页存在
tabs = cmd("browser_list_tabs")["data"]["tabs"]
chatgpt_tab = [t for t in tabs if "chatgpt" in t["url"].lower()][0]

# 2. 切换到 ChatGPT
cmd("browser_select_tab", {"tabId": chatgpt_tab["tabId"]})

# 3. 看点是否找到输入框
snap = cmd("browser_snapshot")
editors = [n["ref"] for n in snap["data"]["nodes"] if n.get("editable") and n.get("ref")]
ref = editors[0]  # 第一个可编辑元素

# 4. 聚焦+点击
cmd("browser_click", {"ref": ref})
time.sleep(1)

# 5. 输入问题（注意：长问题用 browser_evaluate 设 innerText 更稳）
cmd("browser_type", {"ref": ref, "text": "你的问题"})
time.sleep(2)

# 6. 使用 browser_evaluate 触发提交（替代不可用的 browser_press）
cmd("browser_evaluate", {
    "tabId": chatgpt_tab["tabId"],
    "expression": """
// 方案A：用send button
const btn = document.querySelector('[data-testid="send-button"]');
if (btn && !btn.disabled) { btn.click(); 'sent-via-btn'; }
// 方案B：用Enter键盘事件
else {
  document.querySelector('[contenteditable="true"]')?.dispatchEvent(
    new KeyboardEvent('keydown', {key:'Enter', code:'Enter', keyCode:13, which:13, bubbles:true})
  );
  'sent-via-enter';
}
"""
})

# 7. 等回复，通过 browser_evaluate 读取主区域内容
time.sleep(20)
result = cmd("browser_evaluate", {
    "tabId": chatgpt_tab["tabId"],
    "expression": "document.querySelector('main')?.innerText || document.body.innerText"
})
print(result["data"]["result"][:3000])  # ChatGPT 的回复
# 保存到文件
with open('/tmp/chatgpt_response.txt', 'w') as f:
    f.write(result["data"]["result"])
```

也可以用纯 Python 逐步骤操作。关键点：
- **提交用 `browser_evaluate`** 执行 JS，不要用 `browser_press`（不被允许）
- **提取回复也用 `browser_evaluate`** 读 innerText，不要用 snapshot（DOM 树太深时截取不到）
- `browser_type` 可能被 shell 转义破坏，长文本用 JS 的 `innerText = ...` 替代

### 检查标签页状态（问之前先看能不能问）

```bash
# 列所有标签页
curl -s http://127.0.0.1:10088/command -X POST \
  -H "Content-Type: application/json" \
  -d '{"toolName":"browser_list_tabs","args":{}}' | python3 -c "
import sys,json
d=json.load(sys.stdin)
for t in d.get('data',{}).get('tabs',[]):
    print(f\"  {t.get('tabId')} | {t.get('title','')[:40]} | {t.get('url','')[:40]}\")
"

## 致命陷阱（已犯过的）

| 陷阱 | 正确做法 |
|------|---------|
| 不先问AI，自己去GitHub搜 | ❌ 先问AI，等回复再搜 |
| 用browser_type传回显问题 | ✅ 写脚本用json.dumps，避免shell转义 |
| 忘了找文本框ref就直接type | ✅ 先browser_snapshot找输入框ref |
| 问题写得空泛模糊 | ✅ 按模板写：环境+日志+已试+编号问题 |
| 用户切好了标签页，自己又开新的 | ❌ 先查用户已有的标签页 |
| 问题提交后不等回复继续操作 | ❌ 等回复再执行下一步 |
| 无视"不要重启远程设备"还pkill | ❌ 停手，先问 |
| 用 browser_press 提交（OpenBridge 不允许） | ✅ 用 browser_evaluate 执行 JS 点击 send button 或 dispatch KeyboardEvent |
| 用 browser_send_keys 提交（工具不存在） | ✅ 用 browser_evaluate 执行 document.querySelector().click() |
| 浏览器全不可用就卡住不动 | ✅ 切通道 B（搜索→NLM）或通道 C（Grok API），不等浏览器修好 |
