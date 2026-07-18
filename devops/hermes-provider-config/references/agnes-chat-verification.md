# Agnes AI Chat/Image Verification Note

## Verified capability surface
Agnes exposes both chat completions and image generation under the same base URL:
- Base URL: `https://apihub.agnes-ai.com/v1`
- Chat: `POST /v1/chat/completions`
  - Verified models: `agnes-2.0-flash`, `agnes-1.5-flash`
  - Auth: `Authorization: Bearer <AGNES_API_KEY>`
  - Response: HTTP 200 with standard OpenAI chat completion shape
- Image: `POST /v1/images/generations`
  - Model: `agnes-image-2.1-flash`
  - Auth: `Authorization: Bearer <AGNES_API_KEY>`
  - Response: HTTP 200 with image URL
- Discovery: `GET /v1/models`
  - Returns both text and image model IDs under `supported_endpoint_types: ["openai"]`

## Config implication
Do not treat Agnes as image-only. If text models should appear in `/model`, add a `providers.agnes` entry in addition to `image_gen.provider: agnes`.

## Verification recipe
```bash
curl -s -X POST https://apihub.agnes-ai.com/v1/chat/completions \
  -H "Authorization: Bearer $AGNES_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"agnes-2.0-flash","messages":[{"role":"user","content":"say OK"}],"max_tokens":10}'
```

## Session correction
Earlier session evidence classified Agnes as image-only after probing `/chat/completions` with an image model ID and seeing 404. The user's correction matched the official docs, and live probes with text model IDs returned HTTP 200. Future provider classification must use official docs plus per-surface probes, not one failed probe with the wrong model ID.