# FreeLLM-API + Hermes /model 数据流参考

本会话（2026-07-01）现场考证的 hermes /model 下拉、freellmapi provider、model metadata 形态快照。

## FreeLLM-API `/v1/models` 返回结构

```
{
  "data": [
    {"id": "deepseek-v4-pro",       "object": "model", "created": 0,
     "owned_by": "freellmapi", "name": "DeepSeek V4 Pro",
     "context_window": 131072, "context_length": 131072,
     "available": true,        "unavailable_reason": null},
    ...
  ]
}
```

- **TOTAL: 65 模型**（不是 70+；以实证为准）
- 全部 `owned_by=freellmapi`
- **无 `free` / `price` / `quota` 字段** — 只有 `available: bool`
- `available=true` ≠ `free`：仅代表 FreeLLM-API 当前路由可达，不代表上游分文不收
- `context_window` 与 `context_length` 是同一值的两种别名

## Hermes 怎么拿到这个列表（数据流）

```
hermes /model 命令
  └─ model_switch.py: get_authenticated_provider_slugs() / list_provider_models()
       ├─ PROVIDER_TO_MODELS_DEV  → fetch_models_dev()
       │   └─ https://models.dev/api.json（磁盘缓存 + 内存缓存 TTL 1h）
       │   └─ 若失败 → 上次磁盘缓存 fallback
       │
       └─ _PROVIDER_MODELS[provider] 静态分支合并（line 175 起 in hermes_cli/models.py）
           └─ 当前 provider=freellmapi → 该字段在源码中**不存在**
            → 实际绪论：/model 实际拉取走的是 FreeLLM-API /v1/models 直接动
```

## freellmapi 这名在 hermes 处理顺序

```
Container 里注册顺序：
  config.yaml:
    providers:                             (1) builtin PROVIDER_REGISTRY 候选
      freellmapi:
        base_url: http://192.168.1.8:3001            ← adb 对 host LAN IP
        api_key: freellmapi-*****
    custom_providers:                       (2) fallback — 同样会被识到 (runtime_provider.py:657)
      (一般不在这里同样名)

金同学 = Mi8 dipper, config.yaml 里只有 providers.freellmapi, 不走 custom_providers 路径
```

## 在该实例上常见包者/被接合处

| 现象 | 现场报告 |
|---|---|
| title_generation 拿 HTML 不是 JSON | deepseek-v4-flash 邀过 (在 agent.log: TIMESTAMP FreeLLM-API 返回 `<!doctype HTML>`) |
| /v1/chat/completions 返 200 但 是 HTML 不是 JSON | (provider 路由偶尔倒车返回 default web UI 而不是 API) |
| 金同学发送会话能力 与送 Telegram payload 之间 | 在嗌聊中"INFO Sending response" 只是尝试送出 (未验证 Telegram 回 200回执)。不要当 "送达" 看 |

## 起步隐藏鬼

- memory 中的"65个"可能是初期快照，未核实现在一致状态
- 现名现证以后，下次遇到 /model 下拉序列可以快速检索本文是否记录了过 IP/list
