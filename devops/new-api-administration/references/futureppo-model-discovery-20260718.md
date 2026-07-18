# FuturePPO Tokyo API Gateway — 模型发现笔记

## 站点信息
- Base URL: `https://api.futureppo.top/v1`
- 管理面板：`https://api.futureppo.top/`（New API）
- 模型状态：`https://api.futureppo.top/model-status`
- 模型数量：60 个总，40 Normal / 20 Warning/Abnormal
- 请求总量：~200K，成功率 83.2%

## 用户组与模型（2026-07-18）

| 组名 | 类型 | 可用模型 |
|------|------|---------|
| GrokHeavy逆向 | 自有 | grok-4.5（66K 请求，95.5% 成功）|
| 91普通用户 | distributor | openrouter/free, glm-4.5-flash, deepseek-v3.2, doubao-seed-2-0-pro, cerebras/gemma-4-31b, gemini-3.1-flash-lite-preview, qwen3-embedding-8b, gpt-oss-120b |
| Codex | distributor | gpt-5.5 → gpt-5.6-sol, gpt-5.6-terra |
| 高并发渠道 | distributor | qwen3-reranker-8b, qwen3-embedding-8b |
| nvidia | — | step-3.7-flash（32.9% 成功，Abnormal）|

## Key 分发情况

| 批次 | 对应组 | Key 数 | 状态 |
|------|--------|--------|------|
| test-ATg81b 等 | 未知（已过期） | 10 | ❌ 全部 Invalid token |
| test-LuSvqJ 等 | ClaudeCode-V4 | 10 | ✅ Key 有效，openrouter/free 可用 |
| test2-xxx | Codex | 10 | ✅ gpt-5.5 → gpt-5.6-sol |
| angelife-xxx | 91普通用户 | 10 | ✅ 多个模型可用 |

## 发现技巧

1. `/v1/models` 返回空列表时 Key **有效**——仅该组无渠道
2. Playground 配置 JSON 导出是找正确模型名的最快方法
3. `model_not_found` 错误信息会显示组名（distributor）
4. 不同组模型名差异大——不要猜标准名
