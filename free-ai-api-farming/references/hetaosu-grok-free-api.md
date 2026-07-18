# 河涛 Grok API · 公益免费中转站

## 基本信息
- 站点：https://gy.hetaosu.xyz
- Base URL：`https://gy.hetaosu.xyz/v1`
- 全部模型免费，无需充值

## 可用模型
- `grok-4.5` — 推荐（主力）
- `grok-4` — 高性能
- `grok-3` — 通用
- `grok-3-mini` — 轻量

## 验证
```bash
curl https://gy.hetaosu.xyz/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer sk-xxx" \
  -d '{"model":"grok-4.5","messages":[{"role":"user","content":"hi"}]}'
```

## 注意事项
- 中转站性质：上游通道取决于是否有可用的 x.ai 账号池
- 所有模型显示"无可用通道"时，说明上游账号全部离线/超额
- 需要先在网站注册 → 创建 API Key
- API Key 可以在 Hermes config.yaml 中配置为 provider
- 支持 20 个 API Key 轮换（fallback 链）

## Hermes 配置方式
```yaml
providers:
  grok-angelife-xxx:
    api_key: sk-xxx
    base_url: https://gy.hetaosu.xyz/v1
    models:
      - grok-4.5
```

2026-07-17 已验证：grok-4.5 通过 API key 可正常响应（部分 key 有权限问题）。
