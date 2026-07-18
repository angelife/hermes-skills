---
name: qq-agent-mail
description: Tencent QQ Agent Mail 配置工作流 — 给 AI Agent 配专属邮箱（agently-cli）。覆盖安装、OAuth 授权、平台二进制补装、oh-my-zsh PTY 绕过。适合给 Hermes 舰队的同学（土/金/水/火/木）逐个开邮箱。
version: 1.0.0
author: Hermes Agent
tags: [qq-mail, agent-mail, tencent, email, oauth, agently]
---

# QQ Agent Mail — AI Agent 专属邮箱配置

## 概述

腾讯 QQ 邮箱推出的 Agent Mail 服务，为 AI Agent 提供独立邮箱。Agent 可以在安全隔离的环境中收发邮件、管理收件箱、写摘要，操作前有二次确认机制。

**限制（内测期）：**
- 每账户 2 个 AI 邮箱
- 每邮箱 50 封/天
- 每邮箱 1GB 容量

## 安装 CLI

```bash
# 安装主包
npm install -g @tencent-qqmail/agently-cli

# 安装平台二进制（macOS x86_64 / arm64 必须，否则 wrapper 找不到二进制报错）
# 检查架构：uname -m
npm install -g @tencent-qqmail/agently-cli-darwin-x64   # Intel Mac
npm install -g @tencent-qqmail/agently-cli-darwin-arm64  # Apple Silicon
```

验证：
```bash
agently-cli +me
# → {"ok": false, "error": {"type": "auth", "message": "authorization required"}}
# （未授权状态下返回此结果说明 CLI 已正常工作）
```

## OAuth 授权（核心难点）

`agently-cli auth login` 是交互式命令，在 PTY 中运行时会因 `oh-my-zsh` 更新提示阻塞。

### 绕过方法：Node.js execFile

```bash
node -e "
const { execFile } = require('child_process');
const bin = '/usr/local/lib/node_modules/@tencent-qqmail/agently-cli-darwin-x64/bin/agently-cli';
execFile(bin, ['auth', 'login'], {
  env: { ...process.env, SHELL: '/bin/sh', ZSH: '', DISABLE_AUTO_UPDATE: 'true' },
  timeout: 15000
}, (e, so, se) => {
  console.log('STDOUT:', so);
  console.log('STDERR:', se);
  if (e) console.log('ERROR:', e.message);
});
"
```

**输出示例（取 STDERR 中的 URL）：**
```
STDOUT: OK: 认证成功

STDERR:
请点击以下链接登录并授权邮箱：

https://agent.qq.com/page/oauth?oauth_type=device&user_code=uc_xxxxx
```

### 用户操作

将上一步得到的 URL 发给用户，让用户：
1. 在浏览器中打开该链接
2. 微信扫码登录
3. 授权 AI 邮箱

### 验证授权

```bash
agently-cli +me
# → {"ok": true, "email": "your_agent@qq.com", ...}
```

## 查看已注册邮箱

```bash
agently-cli +me
# 返回当前授权的邮箱地址
```

## 常用命令

```bash
# 查看收件箱（最近 10 封）
agently-cli message +list --limit 10

# 发邮件
agently-cli message +send --to bob@example.com --subject "Hi" --body "Hello"

# 读邮件
agently-cli message +read --id msg_001

# 搜索邮件
agently-cli message +search --q "keyword"

# 附加上传
agently-cli attachment +upload --file ./report.pdf

# 附件下载
agently-cli attachment +download --msg msg_001 --att att_001

# 收件监控（阻塞等待新邮件）
agently-cli message +watch
```

## 给舰队同学配置

### 方案：每个同学走独立 agently-cli 授权

1. 在 agent.qq.com 注册多个 QQ 账号（每账号 2 邮箱 × N 账号 = 全员）
2. 各同学的 config 中记录邮箱地址和授权状态
3. 对 Android 同学（金/火/水）：在 chroot 容器内 `npm install -g @tencent-qqmail/agently-cli`（各平台二进制需根据架构安装 linux-x64 或 linux-arm64）

## 常见陷阱

| 陷阱 | 原因 | 处理 |
|------|------|------|
| `agently-cli auth login` 卡在 oh-my-zsh 更新提示 | PTY 启动 zsh 然后加载 oh-my-zsh 初始化 | 用 Node.js execFile + `SHELL: /bin/sh` 绕过 |
| `Missing platform package` | npm 只装了主包，没装平台特定包 | `npm install -g @tencent-qqmail/agently-cli-darwin-$(uname -m)` |
| Authorization required 反复出现 | OAuth 未完成或 token 过期 | 重跑 auth login 流程 |
| 每账户只能开 2 个邮箱 | 内测限制 | 多注册 QQ 账号或等公测放宽 |

## 验证流程

```bash
# 1. CLI 是否可用
agently-cli --help

# 2. 是否已授权
agently-cli +me

# 3. 收件箱是否正常
agently-cli message +list --limit 3

# 4. 发件测试（先发给自己验证）
agently-cli message +send --to YOUR_OWN_EMAIL --subject "test from agent" --body "hello from AI agent"
```