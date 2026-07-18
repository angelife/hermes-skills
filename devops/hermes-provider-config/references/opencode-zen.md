# OpenCode Zen

**Base URL:** `https://opencode.ai/zen/v1`
**Config key env var:** `OPENCODE_ZEN_API_KEY`

## Model ID Format

Use `opencode-zen/<model-id>` when selecting models in Hermes.

## API Endpoints

| Type | Endpoint |
|---|---|
| OpenAI-compatible | `https://opencode.ai/zen/v1/chat/completions` |
| Anthropic (Claude, Qwen) | `https://opencode.ai/zen/v1/messages` |
| OpenAI (GPT) | `https://opencode.ai/zen/v1/responses` |
| Google (Gemini) | `https://opencode.ai/zen/v1/models/gemini-xxx` |

## Free Models (7)

| Model ID | Notes |
|---|---|
| `deepseek-v4-flash-free` | Default preferred |
| `big-pickle` | Free |
| `mimo-v2.5-free` | Free |
| `minimax-m3-free` | Free |
| `nemotron-3-ultra-free` | Free |
| `north-mini-code-free` | Free |
| `qwen3.6-plus-free` | Free |

**Pitfall:** A 401 on `/chat/completions` may be a `CreditsError` ("No payment method") rather than an invalid API key. Test with a real chat completion, do not interpret every 401 as key invalidation-only.

**Pitfall:** The skill assumes all 9 keys in `key.txt` are usable without registration-specific issues. This session found OpenCode Zen returning `CreditsError` for multiple apparently-correct keys, even though the user characterized them as new/valid. Always end-to-end test each key after reading from `key.txt`; do not baptize them "valid" by filename/metadata alone.

**Pitfall:** Run the verification curl/py script from the machine's actual internet path, not from inferred provider docs behavior. OpenCode Zen keys in this session worked only after confirming the real HTTP behavior for that exact account/region/model combination.

```bash
curl -s https://opencode.ai/zen/v1/models \
  -H "Authorization: Bearer $OPENCO...KEY" \
  | jq -r '.data[].id' \
  | grep free
```
