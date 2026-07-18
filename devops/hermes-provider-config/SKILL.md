---
name: hermes-provider-config
description: "Configure, verify, and manage inference providers in Hermes Agent — chat providers, image_gen providers, fallback chains, and env var key management."
---

# Hermes Provider Configuration

## 核心原则

- `providers:` → Chat models，出现在 `/model` 中
- `custom_providers:` → 前缀访问（`@my-provider`），**不在** `/model` 中
- `image_gen:` → 图像生成，由 `image_generate` tool 使用
- 以上三个命名空间**独立**，一个 provider 可能同时实现 chat 和 image

## 两步添加 Provider

### Step 1: 写入 `.env`

```bash
echo 'export MY_PROVIDER_KEY=sk-xxx' >> ~/.hermes/.env
```

### Step 2: 添加 Provider 条目

**Mode A：出现在 `/model`**
```yaml
providers:
  my-provider:
    base_url: https://api.example.com/v1
    api_key: ${MY_PROVIDER_KEY}
    timeout: 120
    max_tokens: 16384
```

**Mode B：前缀访问（`@my-provider`）**
```yaml
custom_providers:
  my-provider:
    type: openai-api
    base_url: https://api.example.com/v1
    api_key: ${MY_PROVIDER_KEY}
```

需要两种模式就两处都加。

### CLI 快捷方式
```bash
hermes config set providers.my-provider.base_url https://api.example.com/v1
hermes config set providers.my-provider.api_key \$MY_KEY
# 注：API key 用 hermes config set 写成本文，不会渲染 ${VAR}
# 正确做法：写入 .env 后用 ${VAR} 引用
```

## 关键坑（Pitfalls）

### P1: 第二个 `providers:` 块会覆盖第一个
追加在文件末尾的第二个 `providers:` 块**覆盖**第一个，丢失所有原始 providers。始终插入已有 `providers:` 块内。

### P2: `model.provider: custom` inline 格式不会传 `agent.system_prompt`
Hermes v0.18.0: `model.base_url` + `model.api_key` inline 格式绕过 named-provider 机制，`agent.system_prompt` 静默忽略。
**修复**：始终用 named provider：
```yaml
# ✅ 正确
providers:
  agnes:
    base_url: https://...
    api_key: ${KEY}
model:
  default: agnes-2.0-flash
  provider: agnes
```

### P3: `custom_providers` 和 `providers` 同名条目会不同步
opencode-zen-free 在两个命名空间都有条目，`max_tokens` 必须保持一致。

### P4: 同一 config 两处同名子项（providers.X + custom_providers.X）
修改必须两处都改。`hermes config set` 只改一处。

### P5: `hermes config set` 写 key 不渲染 `${VAR}`
API key 必须通过 `.env` 注入，不能在 `config set` 中写原文。

### P6: 移除 provider 必须清三处
config.yaml（providers block + custom_providers block）+ .env 对应的 VAR。移除了但没清 .env 会导致 next session 加载时 config check 告警。

### P7: 配置顺序——先配 Provider 再配 Model
必须先有 `providers.X`，才能 `model.default: X/model-id`，才能 `model.provider: X`。顺序错则 `hermes config check` 报 "provider X not found"。

### P8: `.env` 污染
不同 profile 的 `.env` 可能冲突。全局 `~/.hermes/.env` 会被所有 profile 加载，profile 级 `.env` 覆盖全局。

### P10: `auxiliary.vision.api_key: ''` 不继承 provider key（2026-07-15）
Hermes `auxiliary.vision` 中设 `api_key: ''` **不会**从 `providers.X` 继承，而是传空值给上游，导致 `401 ModelNotSupported`。

**修复：** 删掉 `api_key` 行或用 `${ENV_VAR}` 引用。
**排查：** `grep -A5 'vision:' ~/.hermes/config.yaml` → 若 `api_key: ''` 就是坏的。
Docker 内无法读 `~/.hermes/.env`，必须用 `docker compose exec` 或 `--env-file`。

## 验证命令

```bash
# 综合验证
hermes config check

# 查看已配置 provider 列表
hermes config list

# 测试具体 provider 可用性
curl -s -X POST $BASE_URL/chat/completions \
  -H "Authorization: Bearer $KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"test-model","messages":[{"role":"user","content":"hi"}]}'

# 查看所有可用 model 列表
hermes model list-provider-models <provider>
```

## 高阶

### Image Gen Provider
```yaml
image_gen:
  provider: fal  # 或 agnes / openai
  api_key: ${FAL_KEY}
```

### Fallback 链
```yaml
model:
  default: gpt-4
  provider: openai
  fallback_providers:
    - agnes
    - opencode-zen
```

### Provider 独立配置（覆盖全局）
```yaml
providers:
  my-provider:
    base_url: https://...
    model:
      default: custom-model
      max_tokens: 4096
    agent:
      system_prompt: "你是..."
```

### Multi-profile 配置
不同 profile 有独立 `config.yaml` 和 `.env`，可配不同 provider 组合。详见 `~/.hermes/profiles/`。

## 参考
- references/custom-provider-config.md — 自定义 provider 完整示例
- references/provider-fallback-examples.md — Fallback 链配置案例
- references/docker-key-management.md — Docker 环境 key 管理
- references/free-model-context-windows.md — 免费模型上下文窗口实测值（mimo 1M / deepseek 128K）
