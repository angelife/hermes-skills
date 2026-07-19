---
name: vision_helper
description: >
  让不支持多模态的木同学（主模型 hy3:free）也能"看图"。通过调用 OpenRouter 上的免费多模态模型
  （google/gemini-flash 系）把图片识别为文字描述，回传给木同学本体。适用于：用户发来截图/照片/
  图片文件，木同学需要理解图中内容时触发。木同学本体模型不变，vision 模型仅作"外挂眼睛"。
version: 1.0.0
author: 木同学 (QwenPaw cloud agent)
tags: [vision, 多模态, 看图, openrouter, gemini, 免费模型]
---

# Vision Helper — 木同学的免费看图外挂

木同学主模型（tencent/hy3:free）不支持图像输入。本技能用 **OpenRouter 免费多模态模型**
（Gemini Flash 系）把图片转成文字，回传给木同学，使木同学具备"看图"能力而**不改变本体模型**。

## 何时用

- 用户上传图片 / 发来截图 / 指着某图问"这是什么"
- 图片路径已知（如 media/ 目录下），或用户提供了本地路径
- 木同学需要理解图中文字、界面、图表、错误日志等

## 前置条件

- OpenRouter API key（免费额度即可），存于 `/tmp/.orkey` 或环境变量 `OPENROUTER_API_KEY`
- key 不在 MEMORY.md / Hindsight / 任何公开处落明文
- 网络可访问 `https://openrouter.ai/api/v1`

## 用法

```bash
python3 <skill-dir>/scripts/vision_see.py <图片路径> ["可选: 你的问题"]
```

脚本会：
1. 读 key（/tmp/.orkey 或 env）
2. base64 编码图片
3. 调用 OpenRouter `chat/completions`，模型依次尝试 `google/gemini-3.1-flash-lite` 等免费多模态 id
4. 输出模型对图片的文字描述（中文）

木同学拿到描述后，结合上下文回答用户。

## 注意

- **本体模型不变**：这只是 subprocess 调用外部 API，木同学仍是 hy3:free，记忆/风格/上下文全在。
- **免费模型限制**：Gemini 免费档有速率/额度限制；偶发 429 时换模型 id 或稍后重试。
- **图片隐私**：图片经 OpenRouter 发给 Google 模型识别，不含密钥的普通截图可用；敏感图谨慎。
- 模型 id 可能随 OpenRouter 更新变化，脚本里 `MODELS` 列表可随时调整。

## 实测（2026-07-19）

成功识别 Telegram 任务组截图，读出群名、置顶文章链接、木同学发言、截断半句现象等，
证明"免费模型外挂眼睛"路径可行，且木同学本体未变。
