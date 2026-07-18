# FreeLLMAPI Probe Notes

## What it is
FreeLLMAPI is a local unified LLM router at `http://localhost:3001`. It has its own API key (`FREELLMAPI_API_KEY`) and its own model registry, independent of upstream provider keys.

## Correct probe template
```bash
curl -s -H "Authorization: Bearer $FREELLMAPI_API_KEY" http://localhost:3001/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"fusion","messages":[{"role":"user","content":"ping"}],"max_tokens":1}'
```

## Observed failure mode
Omitting `Authorization: Bearer` returns HTTP 401 with `{"error":{"message":"Invalid API key","type":"authentication_error"}}`. This is a probe-form error, not a service-down condition. Always include the key before declaring AUTH_FAIL.

## Playground note
`http://localhost:3001/playground` returns HTTP 200 when the container is running. That indicates the control plane/web UI is up, but does not prove model routing is authenticated. Use an authenticated API call as the real health signal.

## Models
The `/v1/models` response under auth returns a large catalog with many models marked `"available":false,"unavailable_reason":"no_key"`. Treat those as upstream-key gaps, not local-provider failures. `fusion` is one confirmed available alias for local testing.
