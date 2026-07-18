# NVIDIA Provider Config for Hermes on Android Chroot

Tested and verified on Mi8 (192.168.1.26, Debian chroot, Hermes v0.18.0) — 2026-07-07.

## Endpoint

```
base_url: https://integrate.api.nvidia.com/v1
```

## Verified Working Models

| Model | Status | Notes |
|-------|--------|-------|
| `meta/llama-3.1-8b-instruct` | ✅ Reliable | ~36ms TTFT, always available |
| `deepseek-ai/deepseek-v4-flash` | ⚠️ 503 | "ResourceExhausted: All workers are busy" — not reliable |
| `mistralai/mistral-7b-instruct-v0.3` | ❌ 404 | Decommissioned / behind function ID gate |

## Key Inventory (土同学 Mac)

| Key Variable | Value (redacted) | In Use By |
|-------------|-------------------|-----------|
| `NVIDIA_API_KEY` | `nvapi-k_jGh...` | **金同学** (Mi8, since 2026-07-07) |
| `NVIDIA_API_KEY_2` | `nvapi-uTbF...` | Available |
| `NVIDIA_API_KEY_3` | `nvapi-dPGU...` | Available |

## Proxy Requirement

NVIDIA API requires proxy in China:

```
HTTPS_PROXY=http://192.168.1.8:10808
HTTP_PROXY=http://192.168.1.8:10808
```

Tested: `curl -x http://192.168.1.8:10808 https://integrate.api.nvidia.com/v1/models` — works.
Direct (no proxy): DNS + SSL both blocked by GFW.

## Config.yaml Block

```yaml
providers:
  nvidia:
    base_url: https://integrate.api.nvidia.com/v1
    api_key: ${NVIDIA_API_KEY}
```

## .env Entry

```
NVIDIA_API_KEY=nvapi-<full_key>
```

## Switching from Another Provider

Steps to swap a chroot Hermes (e.g. Agnes → NVIDIA):

1. **Test locally first**: Via Mac's terminal, verify the new provider works through the proxy
2. **Push key to remote .env**: `adb -s <IP> shell 'su 0 -c "chroot <chroot_path> /bin/bash -c '\''echo NVIDIA_API_KEY=... >> /.hermes/.env'\''"'`
3. **Update config.yaml on remote**: Rewrite `/.hermes/config.yaml` with the new provider section and `model.provider` + `model.default`
4. **Restart gateway**: `adb -s <IP> shell 'su 0 -c "chroot <chroot_path> /bin/bash -c \"cd /root/.hermes && set -a && source ...\""'` with `--replace`
5. **Verify**: Check gateway log for `✓ telegram connected` and no `No LLM provider configured` errors

## Common Errors

| Error | Meaning |
|-------|---------|
| `HTTP 401` | Invalid API key |
| `HTTP 503 / ResourceExhausted` | All workers busy — try a different model |
| `HTTP 404 / Not Found for account` | Model decommissioned or behind a specific function ID gate |
| `SSL_ERROR_SYSCALL` | Proxy not configured / connection blocked |

## Model List

To list available models:

```sh
curl -sS -x http://192.168.1.8:10808 \
  -H "Authorization: Bearer ${NVIDIA_API_KEY}" \
  https://integrate.api.nvidia.com/v1/models
```

Free models include: `meta/llama-3.1-8b-instruct`, `meta/llama-3.3-70b-instruct`, `nvidia/nemotron-mini-4b-instruct`, and others. Some require specific function IDs (not accessible via the generic chat completions endpoint).
