# Hindsight retain 403 / PermissionDeniedError 排查记录

Date: 2026-07-06

## Symptom
- `hindsight_retain` returns 500 with detail `PermissionDeniedError`
- Docker `hindsight` logs show fact extraction worker calling external LLM provider and receiving `HTTP 403 Authorization failed`

## Verified chain
- MCP read path still alive: prior recalls/stats worked during the same session
- Write path fails during retain batch fact extraction, not during DB write
- Retry loop is scheduled but will not pass while provider auth remains invalid

## Likely cause
- The fact-extraction LLM provider config is invalid/expired
- This is not an MCP transport or Docker policy failure
- Fix priority: inspect Hindsight provider config first; do not retry retain blindly

## Quick checks
```bash
docker logs --since 30m --tail 80 hindsight
curl -s http://localhost:8888/v1/default/banks/hermes/stats
```

## Updated diagnosis from same session
- Hindsight container env `HINDSIGHT_API_LLM_*` points to `http://host.docker.internal:9090/v1` with model `meta/llama-3.1-8b-instruct`; this is NVIDIA local proxy logic, not generic OpenAI fallback.
- The host-side `nvidia_proxy.py` reads `NVIDIA_KEY_1` / `NVIDIA_KEY_2`, so if actual env uses different variable names or expired keys, every fact-extraction request returns `HTTP 403 Authorization failed`.
- Fast-path check: `curl -sS -o /dev/null -w "%{http_code}\n" http://localhost:9090/health` can show `keys_loaded`, but `/v1/chat/completions` remains 403; health success does NOT mean auth works.
- Local FreeLLMAPI (`localhost:3001`) also returned `Invalid API key` in this session, so the failure is broader than one proxy: the currently configured key set is not accepted somewhere in the chain.
- Repair priority: replace the invalid LLM supplier chain with a known-working provider/model/API key that Hindsight's fact extractor can actually call. Retrying retain without changing provider auth will not succeed.

## Updated repair result from same session
- Rebuilt `hindsight` container to use `https://integrate.api.nvidia.com/v1` with a working NVIDIA key.
- Then retained into the updated container and received `Memory stored successfully.`, confirming write restoration.
- Pitfall observed: the proxy health endpoint can lie. `http://localhost:9090/health` returned `keys_loaded:2`, but `/v1/chat/completions` still returned `403 Authorization failed`.
- Pitfall observed: changing provider can change failure mode. This session, retain first changed from `403 Authorization failed` into `[Errno 54] Connection reset by peer`; that still meant the write path was not restored until container port readiness and provider auth were both verified before retrying retain.