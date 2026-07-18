# 河涛 Grok API 公益免费中转站

## 基本信息
- **站名**: 河涛 Grok API · 公益免费
- **Base URL**: `https://gy.hetaosu.xyz/v1`
- **费用**: 全部模型免费，无需充值
- **状态**: 上游通道需补充 x.ai 账号

## 可用模型
| 模型 | 说明 |
|------|------|
| `grok-4.5` | 推荐（最佳） |
| `grok-4` | 高性能 |
| `grok-3` | 通用 |
| `grok-3-mini` | 轻量 |

## 配置（Hermes config.yaml）

```yaml
providers:
  grok-hetaosu-01:
    api_key: sk-xxx
    base_url: https://gy.hetaosu.xyz/v1
    models:
      - grok-4.5
  # ... 更多 key 依次类推
```

## 20 key 容灾

已配置 20 个独立 provider（`grok-angelife-*`），每个有独立 API key。Hermes 的 `fallback_providers` 链依次尝试：第一个 key 用完/失败 → 自动切下一个。

## 限制
- 当前上游通道全空（"No available channel"），无 x.ai 账号时不可用
- 通道恢复后立即工作
- Grok 官方对单 key 有速率限制，多 key 轮转可缓解

## 验证
```bash
# 查询可用模型
curl -s https://gy.hetaosu.xyz/v1/models \
  -H "Authorization: Bearer sk-xxx"

# 测试对话
curl -s https://gy.hetaosu.xyz/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer sk-xxx" \
  -d '{"model":"grok-4.5","messages":[{"role":"user","content":"hi"}]}'
```

## 2026-07-17 记录
- 首批 20 个 key（angelife-* 命名空间）已配入 config.yaml
- 第一把 key（angelife-hmjd1l）报 Access denied，第二把起正常
- 作为 Grok provider 集群接入 Hermes，设为了默认模型
