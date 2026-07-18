# 多模型并行咨询工作流

通过 OpenBridge 同时咨询 ChatGPT、Gemini、Claude 并汇总的方案。

## 适用场景

- 技术排障需要多模型交叉验证
- 复杂问题需要多个视角
- 需要对比不同模型的回答质量

## 前置条件

- OpenBridge daemon 运行（端口 10088），Chrome 扩展已连接
- 三个 AI 平台均已登录（ChatGPT、Gemini、Claude）

## 工作流

### 1. 打开三个标签页

```bash
for url in "https://chat.openai.com" "https://gemini.google.com/app" "https://claude.ai/new"; do
  curl -s -X POST http://127.0.0.1:10088/command \
    -H "Content-Type: application/json" \
    -d "{\"toolName\":\"browser_new_tab\",\"args\":{\"url\":\"$url\"}}"
  sleep 3
done
```

### 2. 逐一输入问题

每个 tab 需要：`browser_select_tab` → `browser_snapshot`（找输入框 ref）→ `browser_type`（填问题）→ `browser_send_keys`（发送）

```bash
# 切换到 tab
curl -s -X POST http://127.0.0.1:10088/command \
  -H "Content-Type: application/json" \
  -d "{\"toolName\":\"browser_select_tab\",\"args\":{\"tabId\":$TAB_ID}}"
sleep 2

# 找到输入框 ref
curl -s -X POST http://127.0.0.1:10088/command \
  -H "Content-Type: application/json" \
  -d '{"toolName":"browser_snapshot"}'

# 填入问题
curl -s -X POST http://127.0.0.1:10088/command \
  -H "Content-Type: application/json" \
  -d "{\"toolName\":\"browser_type\",\"args\":{\"ref\":\"$REF\",\"text\":\"$QUESTION\"}}"
sleep 2

# 按 Enter 发送
curl -s -X POST http://127.0.0.1:10088/command \
  -H "Content-Type: application/json" \
  -d '{"toolName":"browser_send_keys","args":{"keys":"Enter"}}'
```

### 3. 等待回复

给模型足够的思考时间。复杂问题建议 30-60s：

```bash
sleep 45
```

### 4. 读取回复

```bash
curl -s -X POST http://127.0.0.1:10088/command \
  -H "Content-Type: application/json" \
  -d "{\"toolName\":\"browser_select_tab\",\"args\":{\"tabId\":$TAB_ID}}"
sleep 2

curl -s -X POST http://127.0.0.1:10088/command \
  -H "Content-Type: application/json" \
  -d '{"toolName":"browser_snapshot"}' | python3 -c "
import json,sys
d=json.load(sys.stdin)
nodes = d.get('data',{}).get('nodes',[])
texts = [n['name'] for n in nodes if n.get('role')=='StaticText' and n.get('name')]
print('\n---\n'.join(texts[-40:]))
"
```

## 各平台输入框特征

| 平台 | 输入框 name | 发送键 | 备注 |
|------|-----------|--------|------|
| ChatGPT | `与 ChatGPT 聊天` | Enter | 最稳定 |
| Gemini | `为 Gemini 输入提示` | Enter | 有时需要 `browser_click_ref` 先获得焦点 |
| Claude | `Write your prompt to Claude` | Meta+Enter | Claude 2-3 秒才开始输出 |

## 坑

1. **Tab ID 会变** — OpenBridge daemon 重启或 Chrome 重连后 tab ID 全部刷新，必须重新 `browser_list_tabs` 获取
2. **长问题超 120 字** — 个别表单可能有输入长度限制，分段输入或精简
3. **回复截断** — `browser_snapshot` 的 Accessibility Tree 对大段文本有截断，需要时用 `full:true` 参数
4. **模型回复中途中断** — `browser_snapshot` 取到的是当前可见内容，如果模型还在输出中，取到的是片段。增加等待时间或轮询直到内容稳定
5. **Gemini 中文屏蔽** — 某些中文安全相关查询可能被 Gemini 拒绝回答
