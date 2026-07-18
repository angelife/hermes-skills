# Provider Probe Quirks

## What this is
Session observations that show when a provider health probe fails because
of probe path/model mismatch, not because the key is actually bad.

## Base path duplication bug
If a provider block already contains a base URL like `.../v1` and the checker
also appends `/v1/models` or `/v1/chat/completions`, the real request goes to
a doubled path such as `.../v1/v1/models` and returns 404.

Observed on:
- `opencode-zen` with `base_url=https://opencode.ai/zen/v1`
- `nvidia-nim` with `base_url=https://integrate.api.nvidia.com/v1`
- `agnes` with `base_url=https://api.agnes.ai/v1`

## Auth errors on live chat calls can still mean the key is wrong
Use a real chat completion to distinguish a bad key from a bad probe.

Observed:
- `opencode-zen` real chat call returns `401 AuthError: Invalid API key`
- `nvidia-nim` real chat call returns `403 Authorization failed`

These are not probe-path artifacts; they are real AUTH_FAILs.

## Cloudflare Workers AI
- `GET /v1/models` returns 405; the provider requires normal POST calls.
- `@cf/meta/llama-3.1-8b-instruct` is deprecated and returns 410 on live calls.
- Free working alternatives: `@cf/qwen/qwen3-30b-a3b-fp8`, `@cf/ibm-granite/granite-4.0-h-micro`.

## Zhihu
- No usable `/v1/models` listing for health-check style probing.
- Real calls need a fresh `X-Request-Timestamp`; stale timestamps close the connection.
