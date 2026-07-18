# 遇卡点先问 ChatGPT

## 规则（来自用户习惯）

遇到任何不确定的技术问题、反复报错的操作、或者尝试超过2次还没成功的任务，
**先停下来用 OpenBridge 问 ChatGPT，不要自己硬试。**

用户明确说过多次：「让你问你就问 别自己做主」「自己解决不了的问题 就丢给ChatGPT」
「问题先问问完之后呢 你再根据这个问题再搜」「怎么和老年痴呆一样的」——如果问AI的通道
暂时不通，应当告知用户并给出已知结论，而不是循环尝试不同方案。

## ChatGPT 的工作流（OpenBridge）

```bash
# 0. 先确保在 ChatGPT 标签页
curl -s http://127.0.0.1:10088/command -X POST \
  -H "Content-Type: application/json" \
  -d '{"toolName":"browser_list_tabs","args":{}}' \
  | python3 -c "import sys,json; [print(f'id={t[\"tabId\"]} active={t[\"active\"]} title={t.get(\"title\",\"\")}') for t in json.load(sys.stdin).get('data',{}).get('tabs',[])]"

# 1. 选中 ChatGPT 标签页（tabId 来自上一步）
curl -s http://127.0.0.1:10088/command -X POST \
  -H "Content-Type: application/json" \
  -d '{"toolName":"browser_select_tab","args":{"tabId":<id>}}'

# 2. 获取页面快照找输入框
curl -s http://127.0.0.1:10088/command -X POST \
  -H "Content-Type: application/json" \
  -d '{"toolName":"browser_snapshot","args":{}}'

# 找 role=textbox, name 包含"与 ChatGPT 聊天"的 ref

# 3. 打字（已知可用的 ref: backend-678）
curl -s http://127.0.0.1:10088/command -X POST \
  -H "Content-Type: application/json" \
  -d '{"toolName":"browser_type","args":{"ref":"backend-678","text":"你的完整问题"}}'

# 4. 发送（Enter 键）
curl -s http://127.0.0.1:10088/command -X POST \
  -H "Content-Type: application/json" \
  -d '{"toolName":"browser_send_keys","args":{"keys":"Enter"}}'

# 5. 等待 15-30 秒，读回复（找 StaticText 节点，name>30 字符的内容）
curl -s http://127.0.0.1:10088/command -X POST \
  -H "Content-Type: application/json" \
  -d '{"toolName":"browser_snapshot","args":{}}'
```

## Claude 的工作流（OpenBridge）

```bash
# 0. 找/开 Claude 标签页
# 输入框 ref 通常为 backend-585 (role=textbox, name="Write your prompt to Claude")

# 1. 打字
curl -s http://127.0.0.1:10088/command -X POST \
  -H "Content-Type: application/json" \
  -d '{"toolName":"browser_type","args":{"ref":"backend-585","text":"你的完整问题"}}'

# 2. 发送
curl -s http://127.0.0.1:10088/command -X POST \
  -H "Content-Type: application/json" \
  -d '{"toolName":"browser_send_keys","args":{"keys":"Enter"}}'

# 3. 等待响应后读回复
sleep 25
curl -s http://127.0.0.1:10088/command -X POST \
  -H "Content-Type: application/json" \
  -d '{"toolName":"browser_snapshot","args":{}}'
```

## 如何写好问题

用户会批评写得不好的问题（"什么鸟问题啊？你自己看看你问的什么东西？"）。

好的问题格式：
1. **环境**：OS 版本、Kodi 版本、插件版本、启动方式
2. **症状**：精确的日志行、错误信息、UI 表现
3. **已尝试**：具体执行了什么命令、结果（含报错）
4. **具体问题**：编号列出，每个问题明确

推荐先写到文件 `/tmp/question.md`，检查完再发。不要发"Kodi stuck, how fix"这种一行问。

## 后备方案（OpenBridge 不可用时）

当 OpenBridge 报 `NOT_PAIRED`（Chrome 扩展未连接）时，尝试：

### 方案 A：直接告知用户

如果所有 AI 通道都不可用，直接说：
"AI暂时连不上，据我查到的已知结论：..."

并给出从 GitHub issue / Arch Wiki 搜到的结果。不要循环尝试4种以上方案。

### 方案 B：ask.js + CDP

```bash
# 启动 headless Chrome（需要显示器或 xvfb）
# 注意：在 lid-closed / headless macOS 上可能失败
/Applications/Google\\ Chrome.app/Contents/MacOS/Google\\ Chrome \\

当 OpenBridge 报 `NOT_PAIRED`（Chrome 扩展未连接）时，尝试：

### 方案 B：ask.js + CDP

```bash
# 启动 headless Chrome（需要显示器或 xvfb）
# 注意：在 lid-closed / headless macOS 上可能失败
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome \
  --headless --no-sandbox --disable-gpu --remote-debugging-port=9222 \
  --user-data-dir=/tmp/chrome-headless-data https://chatgpt.com

# 然后用 ask.js
node scripts/ask.js chatgpt "你的问题"
```

**已知陷阱：**
- Headless Chrome 在 macOS 上可能 SSL handshake 失败 → 改用 OpenBridge
- `--disable-gpu` 可能不够，尝试 `--disable-software-rasterizer`
- ChatGPT 可能被 Cloudflare 拦截 headless 浏览器
- `ask.js` 连接 `127.0.0.1:9222`，端口需空闲
- Mac 笔记本合盖后：computer_use 不可用（list_apps 空）、CDP 可能 SSL 失败

### 方案 C：直接搜 GitHub Issues

如果 ChatGPT 不可用（Cloudflare 拦截 / CDP 连不上 / OpenBridge 未配对），
用 `web_search` + 关键词 `GitHub Issues <项目名> <错误信息>` 搜已知 bug，
这是次优但可靠的替代。

## 经验教训

- **之前在无头 Chrome 中打开 ChatGPT 会被 Cloudflare 拦截**
- **OpenBridge (端口 10088) 复用用户已有 Chrome 登录会话，无检测风险**
- **不要先试2小时再问，用户明确要求：先问清再动手**
- **问之前先总结清楚问题背景、已尝试的操作和报错信息**
- **问之后等回复再动手，不要边猜边干**
- **Mac 笔记本合盖后：** computer_use 不可用（list_apps 空）、CDP 可能 SSL 失败。
  此时只能通过 OpenBridge（需预配 Chrome 扩展）或 web_search 替代。
- **ask.js 依赖：** `/Applications/Google Chrome.app` 路径写死在脚本中。
