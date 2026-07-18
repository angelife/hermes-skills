# Zhihu Open Platform — API Reference

**Date:** 2026-06-29

## Products & Endpoints

| 产品 | 端点 | 用途 |
|---|---|---|
| 知乎搜索 | `/api/v1/content/zhihu_search` | 知乎站内搜索 |
| 全网搜索 | `/api/v1/content/global_search` | 全网搜索 |
| **直答 API** | **`/v1/chat/completions`** | LLM 对话 |
| 热榜 | `/api/v1/content/hot_list` | 实时热榜 |

Base URL: `https://developer.zhihu.com`

## Authentication (非标准 OpenAI)

所有请求必须带两个 Header：

| Header | 值 | 说明 |
|---|---|---|
| `Authorization` | `Bearer <access_secret>` | Bearer 鉴权 |
| `X-Request-Timestamp` | `date +%s` | **必须动态生成**，静态值 5 分钟前即失效 |
| `Content-Type` | `application/json` | JSON 接口 |

**注意：** `X-Request-Timestamp` 必须是动态生成的 Unix 秒级时间戳，每次请求都要刷新。5 分钟前的 timestamp 会导致连接失败（HTTP 000）。

## 直答 API — 完整 curl 验证

```bash
TS=$(date +%s)
ZHIHU_KEY='你的access_secret'

curl -s -w "\nHTTP:%{http_code}" \
  "https://developer.zhihu.com/v1/chat/completions" \
  -H "Authorization: Bearer $ZHIHU_KEY" \
  -H "X-Request-Timestamp: $TS" \
  -H "Content-Type: application/json" \
  -d '{"model":"zhida-thinking-1p5","messages":[{"role":"user","content":"hi"}],"max_tokens":10}' \
  --max-time 15
```

## Available Models

| Model ID | 说明 | 响应格式 |
|---|---|---|
| `zhida-thinking-1p5` | 推理模型（推荐） | `content` + `reasoning_content` |
| `zhida-fast-1p5` | 快速回答 | `content` |
| `zhida-agent` | Agent 模式 | `content` |

## 局限性

- **无 `/v1/models` 列表端点** — 无法自动发现模型，需要查文档
- **Hermes 静态配置无法注入动态 timestamp** — 无法作为标准 provider 或 MoA 参考模型使用
- **API Key 一次性可见** — 申请后立即显示，过期不显示，需要自己保存
