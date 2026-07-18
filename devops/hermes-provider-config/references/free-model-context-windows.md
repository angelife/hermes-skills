# Free Model Context Windows (实测)

通过 opencode-zen API 可用的免费模型及其上下文窗口大小。模型主动报告的值，非官方文档推测。

## 实测结果

| 模型 | 上下文 | 厂商/路由 | 实测特点 |
|------|:------:|:---------:|---------|
| **mimo-v2.5-free** | **1M tokens** | MiniMax (opencode-zen) | **最大上下文**。适合长对话/长文分析，回复质量尚可 |
| **deepseek-v4-flash-free** | 128K | DeepSeek (opencode-zen) | **默认主力**。稳定，支持 tool calling，回复质量好 |
| **nemotron-3-ultra-free** | 128K | NVIDIA (opencode-zen) | 质量高，辅助 vision 也在用。上下文与 deepseek 相同 |
| **hy3-free** | ? | 腾讯 hy3 (via Novita) | **推理模型**。有 reasoning tokens，但 content 返回 null，tool calling 可能不兼容 |
| **north-mini-code-free** | ? | ? | **推理模型**，同上。content 为 null，适合纯推理场景 |

## 用户模型偏好

- **"有deepseek 优先deepseek"** — 当 deepseek 可用时优先选 deepseek
- 不要列选项表让用户选模型，直接换（见 angelife-minimal-execution-style M47）
- 100 万上下文虽然大，但免费版有限速可能，实际体验不一定优于 128K deepseek

## 探测方法

```bash
curl -s --max-time 20 https://opencode.ai/zen/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $KEY" \
  -d '{"model":"<model-id>","messages":[{"role":"user","content":"用一句话告诉我你的上下文窗口大小是多少"}],"max_tokens":100,"stream":false}'
```

模型通常会如实回答。deepseek/nemotron 报告了 128K，mimo 报告了 1M。

## GLM 模型

通过 opencode-zen 可以看到：**glm-5.2 / glm-5.1 / glm-5**，但需要付费（`CreditsError: No payment method`）。
另外 zhipu（智谱）的 API key 也已在 config 中配置，`glm-4v` 用作辅助 vision 模型。

## 注意事项

- **免费限流** — mimo-v2.5-free 1M 上下文消耗 tokens 更快，更容易触发 burst limit
- **opencode-zen paid 模型**（deepseek-v4-pro, deepseek-v4-flash, gpt-5.x等）返回 `CreditsError: No payment method` — 当前 key 无余额，不可用
- **NVIDIA 免费模型**（nemotron-3-ultra-free 等）通过 opencode-zen 路由有效，直接通过 NVIDIA API 也有效
- **agnes/freellm-api** (localhost:3001) 可能不在线，fallback 链中应排在最后
- **推理模型**（hy3-free, north-mini-code-free）content 为 null，可能不支持 tool calling，不适合用作 Hermes 主力模型

## 模型切换步骤

1. 修改 `~/.hermes/config.yaml` 中的 `model.default:` 为目标模型
2. 清理 fallback 链（去重、顺序合理）
3. 重启 gateway：
   ```bash
   hermes gateway restart
   ```
   ⚠️ **不能从 gateway 进程内重启**（会被 SIGTERM 杀掉）。需在单独终端窗口执行。
