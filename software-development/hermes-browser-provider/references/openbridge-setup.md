# OpenBridge — Local Browser Bridge for AI Agents

安装和配置记录。

## Install

```bash
# 方案1: 安装脚本
curl -fsSL https://raw.githubusercontent.com/60ke/openBridge/master/install.sh | bash

# 方案2: 手动
git clone https://github.com/60ke/openBridge.git ~/.openbridge/repo
cd ~/.openbridge/repo
# 修改 pnpm-workspace.yaml 允许 esbuild 和 spawn-sync 编译
# allowBuilds: { esbuild: true, spawn-sync: true }
pnpm install && pnpm build
```

## Chrome Extension

两个装法：
1. Chrome Web Store: `mdoemfmcfdgoehpcnjiecocecjcmmblh`
2. 手动加载: `chrome://extensions` → 开发者模式 → 加载已解压的扩展 → `packages/extension/.output/chrome-mv3`

## 启动

```bash
cd ~/.openbridge/repo
node packages/daemon/dist/cli/index.js start
```

## 状态检查

```bash
node packages/daemon/dist/cli/index.js status
# Daemon: Running
# Extension: Connected (N)
```

## API （端口 10088）

```bash
# 列所有 tab
curl -s -X POST http://127.0.0.1:10088/command \
  -H 'Content-Type: application/json' \
  -d '{"toolName":"browser_list_tabs","args":{}}'

# 选 tab
curl -s -X POST http://127.0.0.1:10088/command \
  -H 'Content-Type: application/json' \
  -d '{"toolName":"browser_select_tab","args":{"tabId":<ID>}}'

# 输入文字
curl -s -X POST http://127.0.0.1:10088/command \
  -H 'Content-Type: application/json' \
  -d '{"toolName":"browser_type","args":{"ref":"<ACCESSIBILITY_REF>","text":"prompt"}}'

# 发送 Enter
curl -s -X POST http://127.0.0.1:10088/command \
  -H 'Content-Type: application/json' \
  -d '{"toolName":"browser_send_keys","args":{"keys":"Enter"}}'

# 读页面
curl -s -X POST http://127.0.0.1:10088/command \
  -H 'Content-Type: application/json' \
  -d '{"toolName":"browser_snapshot","args":{}}'

# 截图
curl -s -X POST http://127.0.0.1:10088/command \
  -H 'Content-Type: application/json' \
  -d '{"toolName":"browser_screenshot","args":{}}'
```

## ask-openbridge.js

路径: `~/.hermes/skills/web-ai-cdp-bridge/scripts/ask-openbridge.js`

```bash
node ask-openbridge.js "prompt"
```

自动找 Gemini tab → 打字 → 发送 → 读回复。无需 CAPTCHA，无 CDP 检测。

## vs CDP Bridge

| | CDP (ask.js) | OpenBridge (ask-openbridge.js) |
|---|---|---|
| 连接 | remote debugging port | Chrome 扩展 |
| 可检测性 | 高 | 极低（普通扩展流量） |
| CAPTCHA | 频繁触发 | 几乎不触发 |
| 登录态 | 需独立 profile | 直接用已有登录 |
| 代码量 | 500+行 | 143行 |
