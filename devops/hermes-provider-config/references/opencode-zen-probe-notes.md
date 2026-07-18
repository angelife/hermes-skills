# OpenCode Zen Probe Notes

## Misassignment trap
This install previously held `opencode-zen-free` configured to Cloudflare's account endpoint:
`https://api.cloudflare.com/client/v4/accounts/35bee725a22385b01606526119015d16/ai/v1`
That is **not** OpenCode Zen upstream. The real upstream is `https://opencode.ai/zen/v1`.

## Session-verified auth behavior (2026-07-06)
With Hermes default/provider errors showing provider `opencode-zen` at endpoint `https://opencode.ai/zen/v1` and Hermes returning `401 Invalid API key`, live probes showed:

- `GET https://opencode.ai/zen/v1` with existing `OPENCODE_ZEN_API_KEY` => `401`
- `POST https://opencode.ai/zen/v1/chat/completions` with existing `OPENCODE_ZEN_API_KEY` => `403 Forbidden`

This means the issue is **not** that the endpoint is unreachable; it is not Hermes routing; it is upstream refusing/forbidding the request from this key/account scope.

## key.txt vs .env state
- `/Users/macos/key.txt` contains opencode zen section with `angelife.t@gmail.com` and multiple `sk-...` candidates.
- `~/.hermes/.env` had `OPENCODE_ZEN_API_KEY` empty; Hermes had no `opencode-zen` provider block in `config.yaml`.
- After explicit user instruction, one candidate was written to `.env`, and live probe returned `403`.

## Decision path when stuck on opencode 401/403
1. Confirm `.env` key is non-empty.
2. Confirm Hermes provider config actually references `OPENCODE_ZEN_API_KEY`.
3. Probe the **real/open** upstream: `POST /chat/completions` with the configured bearer key.
4. If HTTP 200 => Hermes config/routing issue.
5. If HTTP 401/403 => upstream is rejecting; do not retry as a Hermes bug. Next step is account/key-scope verification or provider replacement.

## Historical Cloudflare confusion
Earlier in this install's history, `opencode-zen-free` was tested against Cloudflare's chat endpoint and `Model not supported` was incorrectly used as evidence to remove the provider. That conclusion was invalid because the tested endpoint does not belong to OpenCode Zen.

## Correct probe template
```bash
curl -s -X POST https://opencode.ai/zen/v1/chat/completions \
  -H "Authorization: Bearer $OPENCODE_ZEN_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"deepseek-v4-flash-free","messages":[{"role":"user","content":"ping"}],"max_tokens":1}'
```
