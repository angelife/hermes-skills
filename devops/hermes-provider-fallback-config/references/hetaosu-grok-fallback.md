# 河涛 Grok API 中转站 — 20 Key 容灾配置

## 背景
2026-07-17 配置了 20 个 Grok-4.5 API Key 全部指向 `gy.hetaosu.xyz/v1`。
每个 Key 在 config.yaml 中定义为独立 provider，通过 fallback_providers 链实现自动轮换。

## 配置模式
```yaml
providers:
  grok-angelife-hmjd1l:
    api_key: sk-xxx
    base_url: https://gy.hetaosu.xyz/v1
    models:
      - grok-4.5
  grok-angelife-3jujbz:
    api_key: sk-xxx
    base_url: https://gy.hetaosu.xyz/v1
    models:
      - grok-4.5
  # ... 继续添加更多 key

fallback_providers:
  - model: grok-4.5
    provider: grok-angelife-hmjd1l
  - model: grok-4.5
    provider: grok-angelife-3jujbz
  # ... 继续为每个 key 添加 fallback 条目
```

## 注意事项
- 中转站需要上游 x.ai 账号池有可用通道
- 如果所有模型都返回"No available channel"，说明上游全部离线
- 该服务为公益免费性质，不保证 SLA
- API Key 不要在公开文件中明文存储
