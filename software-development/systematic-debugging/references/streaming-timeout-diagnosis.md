# Streaming Timeout Diagnosis

## Session: 2026-06-12 — Xunfei Provider ReadTimeout

### Problem
Long-running LLM tasks (code generation, file analysis) via Xunfei (讯飞) custom OpenAI-compatible provider timeout after ~78 seconds with `ReadTimeout`.

### Diagnosis Steps

1. **Check Hermes gateway streaming config:**
   ```
   ~/.hermes/config.yaml → streaming.enabled: false
   ```
   Gateway is configured to disable streaming.

2. **Check the provider config:**
   ```
   ~/.hermes/config.yaml → providers.xunfei
     stream: true  (DEFAULT — inherited from openai-compatible template)
     timeout: not set (default varies)
   ```
   Provider-level `stream: true` overrides gateway's `streaming.enabled: false`.

3. **Root cause:** The provider section explicitly enables `stream: true`. This sends `stream: true` in HTTP requests to the upstream API. When the upstream doesn't respond with chunks within the default read timeout (~78s for long code generation tasks), the HTTP client throws `ReadTimeout`.

4. **The fix:**
   ```yaml
   providers:
     xunfei:
       model: xopqwen36v35b
       api_base: maas-api.cn-huabei-1.xf-yun.com/v2
       api_key: key:secret
       timeout: 300
       max_tokens: 16384
       extra_body:
         stream: false
   ```

### Key Insight

**Layered streaming config:**
- Gateway level: `streaming.enabled` (Hermes gateway config)
- Provider level: `stream` (OpenAI-compatible API request parameter)
- Provider `stream` setting is sent as part of the API request body

When `stream: true` at provider level → request includes `"stream": true` → upstream starts streaming → chunks arrive slowly → default HTTP timeout triggers → `ReadTimeout`.

Even if gateway `streaming.enabled: false`, if the provider config has `stream: true`, the timeout still happens because the request is still a streaming request at the HTTP level.

### When This Applies

Any custom OpenAI-compatible provider that may send long-running requests:
- Code generation / file analysis tasks
- Long context windows
- Slow upstream APIs (free tiers, rate-limited)
- Providers that default to `stream: true`

### Fix Pattern

For any custom provider experiencing `ReadTimeout`:
1. Check `providers.<name>.stream` in config
2. Set `extra_body: {stream: false}` if streaming not needed
3. Set `timeout: 300` (or higher for very long tasks)
4. Set `max_tokens` to a reasonable cap

### Why `stream: false` Instead of Setting `stream: true` at Gateway

Hermes gateway's `streaming.enabled` controls whether Hermes displays streaming output in the chat UI. Setting provider `stream: false` controls the HTTP request body. These are orthogonal:
- `streaming.enabled: true` + `stream: false` → single response, displayed progressively
- `streaming.enabled: false` + `stream: true` → request is streaming but gateway buffers it (wastes upstream resources)
- Both must be `false` for true non-streaming behavior
