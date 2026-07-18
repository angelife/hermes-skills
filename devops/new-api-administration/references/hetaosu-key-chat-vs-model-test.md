# hetaosu Key: /v1/models 200 ≠ chat/ completions 可用

## 问题

hetaosu 中转站的 API key，用 `GET /v1/models` 测试全部返回 HTTP 200，但实际调 `POST /v1/chat/completions`（如 `model=grok-4.5`）时部分 key 返回 **502**。

## 实测数据（2026-07-18，40 个 key）

| 测试接口 | 结果 |
|----------|------|
| `GET /v1/models` 批量 | 40/40 ✅ HTTP 200 |
| `POST /v1/chat/completions`（走 SOCKS5 代理） | 多数 ✅ 正常，少数 ❌ 502 |

5 个 key 的 chat 测试示例：

| Key 前缀 | /v1/models | chat/completions |
|-----------|-----------|------------------|
| sk-4Ep... | ✅ 200 | ❌ 502 |
| sk-WHY... | ✅ 200 | ❌ 502 |
| sk-U9U... | ✅ 200 | ✅ 正常回复 |
| sk-5vS... | ✅ 200 | ✅ 正常回复 |
| sk-MQ9... | ✅ 200 | ✅ 正常回复 |

## 原因推测

- 部分 key 的 x.ai 上游额度/配额已耗尽，但 hetaosu 网关仍在 v1/models 端点上返回该 key
- hetaosu 对 models 端点和 chat 端点的鉴权/路由逻辑不同
- 502 来自 hetaosu 的 upstream（x.ai）而非 hetaosu 本身

## 正确测试方法

**不能只用 `/v1/models` 测 key。必须用实际的 chat 请求验证：**

```bash
# 正确：测 chat 接口
curl -sS -m15 https://gy.hetaosu.xyz/v1/chat/completions \
  -H "Authorization: Bearer $KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"grok-4.5","messages":[{"role":"user","content":"hi"}],"max_tokens":10}'
```

## New API 渠道配置注意事项

- 单 key 模式：选一个 chat 接口能过的 key 单独用
- 多 key 池化模式：如果 `\n` 分隔的多 key blob 导致 Go HTTP 报 `invalid header field value for Authorization`，先排查是否有空行/回车/前后空格；如果仍有问题，退化到单 key
- 换 key 后重启容器：`docker rm -f new-api && docker run ...`
