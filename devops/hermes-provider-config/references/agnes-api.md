# Agnes AI Image Generation Notes

## Provider class
Agnes is not a chat LLM provider. In Hermes it is installed as an **image_gen backend plugin** at:
`/Users/macos/.hermes/plugins/image_gen/agnes/plugin.yaml`

In `config.yaml` it lives under `image_gen.agnes`, not `providers.agnes`.

## Endpoint and interface
- Base URL: `https://apihub.agnes-ai.com/v1`
- Route: `POST /v1/images/generations`
- Auth: `Authorization: Bearer <AGNES_API_KEY>`
- Model: `agnes-image-2.1-flash`

## Correct probe template
```bash
curl -s -X POST https://apihub.agnes-ai.com/v1/images/generations \
  -H "Authorization: Bearer $AGNES_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"agnes-image-2.1-flash","prompt":"ping","size":"1024x1024","extra_body":{"response_format":"url"}}'
```

## Previous invalided evidence
Earlier session output listed `AUTH_FAIL` or `SSLError` for Agnes. That conclusion was invalid because the agent probed it as if it were a chat LLM provider. The earlier failure was therefore likely a wrong probe path/protocol mismatch, not a key or service failure.

## Local verification results
With keys from `~/key.txt`, all test calls returned HTTP 200 and an image `url`, confirming the provider/keys/config path works when probed correctly.
