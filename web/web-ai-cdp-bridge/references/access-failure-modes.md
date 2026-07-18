# 访问 AI 助手的已知失败模式

## 当前可用的 AI 访问路径

| 路径 | 脚本 | 依赖 | 状态 |
|------|------|------|------|
| ask.js + users Chrome | `node scripts/ask.js <provider> "<prompt>"` | Chrome 带 --remote-debugging-port=9222 | ❌ Chrome 需专门启动 |
| ask-chatgpt-direct.js | `node scripts/ask-chatgpt-direct.js` | 已有 ChatGPT 标签页 + CDP 9222 | ❌ 同需 CDP |
| ask-openbridge.js | `node scripts/ask-openbridge.js "<prompt>"` | OpenBridge 守护 + Chrome 扩展配对 | ⚠️ 扩展常断连 |

## 各失败模式及处理

### 1. Cloudflare 拦截（通病）

**现象：** 浏览器工具打开 ChatGPT/Claude 时出现 Cloudflare 验证页面。
**原因：** 无头 Chrome 或 Browserbase 无住宅代理。
**处理：**
- `ask.js` 连接的 headless Chrome 100% 被拦截，除非使用用户真实 Chrome 配置文件
- 因此不能直接 browser_navigate → browser_type 手动操作 ChatGPT 页面
- 兜底：web_search 搜已知 issue，读 issue 内容找解决方案

### 2. CDP 端口未开

**现象：** `ask.js` 报 `connect ECONNREFUSED 127.0.0.1:9222`
**原因：** Chrome 实例启动时未加 `--remote-debugging-port=9222`
**处理：**
- 可以后台启动一个 headless Chrome 带 CDP：
  ```
  /Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome \
    --headless --no-sandbox --disable-gpu --remote-debugging-port=9222 \
    --user-data-dir=/tmp/chrome-headless-data https://chatgpt.com
  ```
- ⚠️ 不能用用户的 Chrome 配置文件（`--user-data-dir` 指向实际用户目录），会冲突
- 独立的 `--user-data-dir` 实例没有登录 session → Cloudflare 拦截
- 两难：有登录 session 的不能同时开 CDP，能开 CDP 的没有登录 session

### 3. OpenBridge 未配对

**现象：** `NOT_PAIRED` 错误
**原因：** Chrome 扩展未连接或未启动
**处理：**
- 检查 daemon 状态：`cd ~/.openbridge/repo && node packages/daemon/dist/cli/index.js status`
- 需要用户手动在 Chrome 中连接扩展

### 4. 用户 Mac 合盖 / 锁屏

**现象：** `computer_use` capture 返回 0x0 或无元素
**原因：** macOS 合盖后显示器关闭，CUA 驱动无法捕获画面
**处理：**
- 无法调试、无法看画面、无法通过计算机视觉操作
- 只能通过 `terminal` 执行远程命令
- 避免任何需要视觉确认的操作

## 结论：什么情况下能问 AI

| 条件 | 能问 | 兜底 |
|------|------|------|
| 已有 ChatGPT/CDP 实例运行 | ✅ 直接 ask.js | web_search 搜已知 bug |
| OpenBridge 扩展已配对 | ✅ 直接 ask-openbridge.js | web_search |
| 用户 Mac 开盖 + Chrome 登录中 | ⚠️ 需用 computer_use 操控 | web_search + 终端 |
| 以上全不满足 | ❌ | 只靠 web_search + 已知知识 |
