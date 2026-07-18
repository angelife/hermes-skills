# OpenBridge browser_evaluate — 替代 browser_press 的操作模式

## 背景

OpenBridge daemon（端口 10088）禁用了 `browser_press` 工具。  
因此通过 OpenBridge 提交表单（比如在 ChatGPT 输入框按 Enter）不能直接用 `browser_press`。

## 可用操作

| 操作 | 方法 | 说明 |
|------|------|------|
| 列举标签页 | `browser_list_tabs` | 无参数 |
| 选择标签页 | `browser_select_tab` | 需 tabId |
| 执行 JS | `browser_evaluate` | **核心替代方案** |
| 截图 | `browser_snapshot` | 返回无障碍树节点 |
| 点击 | `browser_click` | 需 ref ID |
| 输入 | `browser_type` | 需 ref ID |

## 向 ChatGPT 提交问题的完整流程

```python
import json, urllib.request, time

base = "http://127.0.0.1:10088/command"
headers = {"Content-Type": "application/json"}

def cmd(tool, args={}):
    data = json.dumps({"toolName": tool, "args": args}).encode()
    req = urllib.request.Request(base, data=data, headers=headers)
    return json.loads(urllib.request.urlopen(req, timeout=10).read())

# 1. 选择 ChatGPT tab
cmd("browser_select_tab", {"tabId": 1629832109})

# 2. 激活编辑器
cmd("browser_evaluate", {
    "tabId": 1629832109,
    "expression": """
let editor = document.querySelector('[contenteditable="true"]');
if (editor) { editor.focus(); 'focused'; } else { 'not-found'; }
"""
})

# 3. 点击输入框
cmd("browser_click", {"ref": "backend-674"})
time.sleep(0.5)

# 4. 输入问题
cmd("browser_type", {"ref": "backend-674", "text": "你的问题"})
time.sleep(1)

# 5. 用 JS 模拟 Enter 提交（browser_press 的替代方案）
cmd("browser_evaluate", {
    "tabId": 1629832109,
    "expression": """
document.querySelector('[contenteditable="true"]')?.dispatchEvent(
    new KeyboardEvent('keydown', {
        key:'Enter', code:'Enter', keyCode:13, which:13, bubbles:true
    })
);
'sent';
"""
})

# 6. 等待回复（轮询检查 main 内容）
for i in range(15):
    result = cmd("browser_evaluate", {
        "tabId": 1629832109,
        "expression": "document.querySelector('main')?.innerText?.substring(0,200) || ''"
    })
    text = result.get('data', {}).get('result', '')
    if len(text) > 50:
        print("回复:", text)
        break
    time.sleep(1)
```

## 从 ChatGPT 提取完整回复

```python
result = cmd("browser_evaluate", {
    "tabId": 1629832109,
    "expression": "document.querySelector('main')?.innerText || ''"
})
text = result.get('data', {}).get('result', '')
parts = text.split('\n\n', 1)
if len(parts) > 1:
    response = parts[1]  # AI 回复部分
```

## 注意事项

- `browser_evaluate` 返回复杂对象时可能 HTTP 400 → 简化返回值，用 `.substring(0,300)` 而非完整内容
- ChatGPT 页面使用 Shadow DOM，某些元素可能不在无障碍树中
- `browser_snapshot` 无法覆盖 Shadow DOM 中的文本内容
- 但 `browser_evaluate` 可以通过 JS 直接访问 Shadow DOM（`element.shadowRoot`）
