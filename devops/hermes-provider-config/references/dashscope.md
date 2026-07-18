# 阿里云 DashScope（通义千问）

## Overview

DashScope is Alibaba Cloud's model-as-a-service platform, providing access to the Qwen (通义千问) family of LLMs through an **OpenAI-compatible REST API**. This makes it a drop-in provider for any tool that supports OpenAI `/chat/completions` format — including Hermes Agent.

## Base URL

```
https://dashscope.aliyuncs.com/compatible-mode/v1
```

This endpoint accepts standard OpenAI-format requests. Append `/chat/completions` for chat calls.

## API Key

- Format: `sk-...` (starts with `sk-`)
- Get it from: https://dashscope.aliyun.com/ → API-KEY 管理 → Create API Key
- Auth: `Authorization: Bearer sk-...` (standard OpenAI Bearer token)

## Free Tier Models

| Model ID | Quota | Best For |
|---|---|---|
| `qwen-turbo` | 1M tokens/month | General chat, classification, light summarization |
| `qwen-long` | 1M tokens/month | Long documents (>100K context) |
| `qwen-plus` | 1M tokens/month | Better quality reasoning (higher cost over-quota) |

Quota refreshes monthly (~33K tokens/day). Exceeding quota → automatic pay-as-you-go billing (set budget cap in console to avoid surprise charges).

## Model Capabilities

| Feature | qwen-turbo | qwen-plus | qwen-max |
|---|---|---|---|
| Tool calls | ✅ | ✅ | ✅ |
| Streaming | ✅ | ✅ | ✅ |
| Vision | ❌ | ❌ | ✅ (qwen-vl-max) |
| Function calling | ✅ | ✅ | ✅ |
| Context window | 128K | 128K | 32K |

## Hermes Config

```bash
hermes config set providers.dashscope.base_url https://dashscope.aliyuncs.com/compatible-mode/v1
hermes config set providers.dashscope.api_key "sk-your-key-here"
hermes config set providers.dashscope.timeout 120
hermes config set providers.dashscope.max_tokens 16384
hermes config set model.default qwen-turbo
hermes config set model.provider dashscope
```

## Network (China domestic)

- ✅ Reachable from all mainland Chinese cloud platforms (Huawei Cloud, Tencent Cloud, Alibaba Cloud itself)
- ✅ Reachable from Chinese home networks (China Unicom/Telecom/Mobile)
- ✅ HTTPS works without proxy
- ❌ May have elevated latency from outside China (~200-500ms)
- **Not blocked by the Great Firewall** — Alibaba is a domestic company

## Cost Management

- Free tier is per Alibaba Cloud account, not per API key
- Default: pay-as-you-go after free quota exhausted
- Set spending limit: DashScope console → Quota Management → Budget Alert
- Pricing: qwen-turbo ~0.3元/1M tokens after exhaustion (cheap for light use)

## Verified Working (2026-07-02)

| Model | Test Result |
|---|---|
| `qwen-turbo` | ✅ Works with Hermes, standard OpenAI format |
| `qwen-plus` | ✅ Works (tested via curl) |

## moa-reference 兼容性

DashScope 支持 tool calling 和标准的 OpenAI `/chat/completions` 接口，可以同时作为 MoA 的：
- **reference model** ✅（不需要 tools 时，纯文本即可）
- **aggregator** ✅（支持 tool calling，Hermes 可以正常传 tools 参数）
