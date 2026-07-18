# Multi-Key Provider Fallback Template

## Pattern: same endpoint, multiple keys

This is the proven Hermes pattern for API key fallback when you have N keys for the same provider/endpoint. It does NOT rely on credential pools.

### .env variables
```dotenv
OPENCODE_ZEN_API_KEY_PRIMARY=<key0>
OPENCODE_ZEN_API_KEY_BACKUP=<key1>
OPENCODE_ZEN_API_KEY_BACKUP2=<key2>
NVIDIA_API_KEY=<key0>
NVIDIA_API_KEY_2=<key1>
NVIDIA_API_KEY_3=<key2>
```

### config.yaml providers block
```yaml
providers:
  opencode-zen-primary:
    base_url: https://opencode.ai/zen/v1
    api_key: ${OPENCODE_ZEN_API_KEY_PRIMARY}
  opencode-zen-backup:
    base_url: https://opencode.ai/zen/v1
    api_key: ${OPENCODE_ZEN_API_KEY_BACKUP}
  nvidia-primary:
    base_url: https://integrate.api.nvidia.com/v1
    api_key: ${NVIDIA_API_KEY}
  nvidia-backup:
    base_url: https://integrate.api.nvidia.com/v1
    api_key: ${NVIDIA_API_KEY_2}
```

### config.yaml fallback chain
```yaml
fallback_providers:
  - provider: opencode-zen-primary
    model: deepseek-v4-flash-free
  - provider: opencode-zen-backup
    model: deepseek-v4-flash-free
  - provider: nvidia-primary
    model: deepseek-ai/deepseek-v4-flash
  - provider: nvidia-backup
    model: deepseek-ai/deepseek-v4-flash
```

## Session specifics observed 2026-07-07
- OpenCode Zen model id: `deepseek-v4-flash-free`
- NVIDIA NIM model id: `deepseek-ai/deepseek-v4-flash`
- Hermes `fallback_providers` triggers on: rate-limit, 5xx, auth failures, connection errors
- fallback is turn-scoped; next user message re-tries primary first
- Adding KEY3: append provider block + append entry in `fallback_providers`