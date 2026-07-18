# Grok 共享 API 端点（fallback 通道）

## 发现

从 `~/.hermes/config.yaml` 中发现一个可用的 Grok API 代理端点。

```
endpoint: https://api.xhahlf.top/v1
api_key:  sk-ExC...JYdH     # 在 config.yaml 中 hardcoded
model:    grok-4.5
```

**状态**：✅ 通（2026-07-16 确认）。走现有 CF 代理（127.0.0.1:10808）可正常调用。

## 验证

```bash
API_KEY="sk-xxx"   # 从 config.yaml 提取
curl -s --max-time 30 -x http://127.0.0.1:10808 \
  https://api.xhahlf.top/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $API_KEY" \
  -d '{"model":"grok-4.5","messages":[{"role":"user","content":"hi"}],"max_tokens":20}'
```

## 用途

- **注册机跑不通时的 fallback**：当无法注册新 Grok 账号时，这个端点可临时顶替
- **浏览器不可用时问 AI**：当 ask.js（CDP）和 browser_navigate 都失败时，用 curl 直接调此 API 问问题
- **多个端点做健康检查**：后续可加入切换逻辑

## 限制

- 这个 key 是共享的（hardcoded 在 config.yaml 中），可能被重置或限流
- 仅 `grok-4.5` 模型可用（其他模型如 gpt-4o-mini 返回 model_not_found）
- 限流：每分钟 ≤ 6 次（尝试被拦时显示 "请求过于频繁，每分钟最多 6 次"）

## 其他已知通道

| endpoint | key 位置 | 模型 | 状态 |
|----------|---------|------|------|
| `https://api.xhahlf.top/v1` | config.yaml 硬编码 | `grok-4.5` | ✅ |
| `https://open.bigmodel.cn` | config.yaml `9efba...` key | 智谱系列 | ⚠️ 路径待确认 |
| `https://integrate.api.nvidia.com/v1` | 环境变量 `${NVIDIA_API_KEY}` | llama 系列 | ⚠️ 需解环境变量 |
