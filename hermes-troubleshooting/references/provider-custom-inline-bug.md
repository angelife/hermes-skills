# Provider `custom` Inline Bug (Hermes v0.18.0)

## Symptom
Agent starts, connects to Telegram, receives messages, but responds with wrong identity — ignores `agent.system_prompt` and uses the model's default persona (e.g. "Agnes" instead of "金同学").

## Root Cause
In Hermes v0.18.0, the **inline `provider: custom` format** bypasses `agent.system_prompt`:

```yaml
# ❌ BROKEN — system_prompt silently ignored
model:
  default: agnes-2.0-flash
  provider: custom
  base_url: https://apihub.agnes-ai.com/v1
  api_key: ${AGNES_API_KEY}

agent:
  system_prompt: "你是金同学..."
```

When `provider: custom` is used with inline `base_url`/`api_key` in the `model:` block, the gateway resolves the provider but does NOT attach `agent.system_prompt` to the chat completion request. The model receives only user messages, not the system prompt.

## Fix
Always use a **named provider** defined in the `providers:` section:

```yaml
# ✅ WORKS — system_prompt is passed to the model
model:
  default: agnes-2.0-flash
  provider: agnes
providers:
  agnes:
    base_url: https://apihub.agnes-ai.com/v1
    api_key: ${AGNES_API_KEY}

agent:
  system_prompt: "你是金同学..."
```

## Detection
Check the gateway/agent log. If the response lacks your `system_prompt` text and the model uses its default persona, or if the log shows `provider=custom` instead of the named provider, you have this bug.

```log
# ❌ Broken: shows provider=custom
agent.conversation_loop: ... provider=custom base_url=https://... model=agnes-2.0-flash

# ✅ Fixed: shows provider=agnes
agent.conversation_loop: ... provider=agnes model=agnes-2.0-flash
```

## Scope
Affects ALL providers using the inline `model.provider: custom` format. Does NOT affect named providers defined in the `providers:` section. Applies to Hermes v0.18.0 (confirmed); may also affect other versions.

## Related
- Use `hermes-provider-config` skill for general provider configuration.
- Use `hermes-provider-healthcheck` for verifying provider connectivity.
