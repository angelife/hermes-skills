---
name: ask-chatgpt
description: "通过 OpenBridge/CDP 向 ChatGPT Web 获取外部反馈 — 遇卡点时使用"
version: 1.0.0
author: 土同学
license: MIT
---

# ask-chatgpt — ChatGPT 外部智囊团

## Trigger

当 Hermes Agent **遇到卡点**（架构决策不确定、Bug 找不到根因、需要外部方案评审）且内部推理不足以解决时，使用此技能推给 ChatGPT Web 获取反馈。

## Workflow

### 1. 推送问题

```bash
python3 ~/.hermes/scripts/ask-chatgpt.py "你的技术问题/架构疑问/代码评审请求"
```

可选参数：
- `--save-img` — 同时保存 ChatGPT 返回的图片到 outputs/

### 2. 等待并提取回复

脚本自动：
1. 打开 ChatGPT Web (chatgpt.com)
2. 在文本框输入问题
3. 点击发送
4. 等待回复完成
5. 提取文本内容
6. 可选：保存生成图片

### 3. 理解反馈并执行

- 阅读 ChatGPT 回复 → 提取关键建议
- 按照建议调整方向
- 如不清晰 → 再次提问追问

## 基础设施

| 组件 | 位置 | 说明 |
|------|------|------|
| OpenBridge Daemon | PID 84730, :10088 | Chrome 扩展桥接，用于浏览器控制 |
| ask.js | `~/.hermes/skills/web-ai-cdp-bridge/scripts/ask.js` | CDP 方式浏览器控制 |
| ChatGPT 适配器 | `adapters/chatgpt.js` | 专用于 chatgpt.com 的 turn 检测和内容提取 |

## Pitfalls

- ChatGPT Web 可能要求登录 — OpenBridge 已配对，复用现有会话
- 回复可能包含代码块 — 适配器提取全部文本，代码块保含在内
- 长时间无回复 — 大概率是 ChatGPT 深度思考中，超时 180 秒
- 视觉模型切换后 `vision_analyze` 可能失败 — 检查 `config.yaml` 中 `vision.model` 是否为有效模型

## 与其他工具的关系

| 工具 | 何时用 |
|------|--------|
| `web_search` | 快速查文档、搜索已知信息 |
| `ask-chatgpt` | 需要外部推理、架构评审、方向建议 |
| OmniRoute | 日常 AI 推理路由，已有 344 模型池 |

## 参考

- `references/weixin-pairing-flow.md` — WeChat iLink Bot 配对流程（首次设置 ClawBot 时使用）
