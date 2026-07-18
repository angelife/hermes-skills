# Google Gemini API — Provider Reference

## API Key Format

- Google AI Studio keys: `AIza...` or `AQ.A...` (starting pattern)
- Stored in `.env` as `GOOGLE_GEMINI_KEY`

## Endpoints

| Endpoint | Usage |
|---|---|
| `https://generativelanguage.googleapis.com/v1beta/openai` | OpenAI-compatible (Hermes base_url) |
| `https://generativelanguage.googleapis.com/v1beta/openai/chat/completions` | Chat (OpenAI format) |
| `https://generativelanguage.googleapis.com/v1beta/models` | List models (NOT OpenAI format) |

## Free-Tier Models (verified 2026-06-29)

- `gemini-2.5-flash` — ✅ Free, general purpose
- `gemini-3-flash-preview` — ✅ Free, latest flash

## Paid Models (require billing)

All return HTTP 429 on free-tier keys:
- `gemini-2.0-flash` 
- `gemini-2.5-pro`
- `gemini-3-pro-preview`
- `gemini-3.1-pro-preview`

## Also accessible (model listing confirmed, billing status unknown)

- Gemma 4 26B/31B
- Imagen 4 / 4 Ultra / 4 Fast (image gen)
- Veo 2 / 3 / 3.1 (video gen)
- Lyria 3 (audio gen)
- Deep Research / Max / Pro
- Gemini Robotics-ER

## Configuration in Hermes

```yaml
providers:
  google-gemini:
    base_url: https://generativelanguage.googleapis.com/v1beta/openai
    api_key: ${GOOGLE_GEMINI_KEY}
    timeout: 120
    max_tokens: 8192
```

The OpenAI-compatible endpoint mirrors the `/v1/chat/completions` format — no adapter needed.

## Known Pitfalls

1. Empty `message.content` possible on very short responses — increase `max_tokens`
2. Free tier cannot access Pro models — always test before setting as default
3. Model listing shows ALL models Google offers, but most require payment
