# FreeLLM-API Fusion Mode Reference

Source: `server/src/services/fusion.ts` in local `~/freellmapi` repo (tashfeenahmed/freellmapi).
Verified 2026-07-03 against source code.

## What it is

Fusion is a virtual model (`model: "fusion"`) that runs a panel of models in parallel, then uses a judge model to synthesize one final answer. Similar to MoA but built into the FreeLLM-API proxy itself — no Hermes-side config needed.

## Basic usage

```bash
curl http://localhost:3001/v1/chat/completions \
  -H "Authorization: Bearer $FREELLMAPI_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "fusion",
    "messages": [{"role":"user","content":"你好"}]
  }'
```

## The `fusion` field (inline override)

Any request can pass a `fusion` object alongside the standard OpenAI fields. All fields are optional — missing ones fall back to dashboard-saved defaults.

| Field | Type | Description |
|---|---|---|
| `models` | `string[]` | Explicit panel member model IDs. Omit → auto-select from Fallback Chain. |
| `k` | `int > 0` | Auto-panel size. Default 4, hard max 8 (operator-configurable via `fusion_max_k` setting). |
| `judge` | `string` | Judge/synthesizer model ID. Omit → top-ranked available model. |
| `strategy` | `"synthesize"` \| `"best_of"` | `synthesize` (default): judge blends all answers into one. `best_of`: skip judge, return longest single panel answer (cheaper, no +1 call). |
| `expose_panel` | `boolean` | `true` → attach each panel member's raw answer + judge metadata in `x_fusion` field of response. |

### Example with full override

```json
{
  "model": "fusion",
  "messages": [{"role":"user","content":"解释量子计算"}],
  "fusion": {
    "models": ["deepseek-v4-flash", "glm-5.1", "qwen3-30b-a3b"],
    "k": 3,
    "judge": "deepseek-v4-pro",
    "strategy": "synthesize",
    "expose_panel": true
  }
}
```

## Dashboard defaults (saved config)

Persisted in settings table under `fusion_config` key. Configurable via web UI at `http://localhost:3001` → Models → Fusion tab.

- `mode`: `"auto"` (pick diverse panel from Fallback Chain each request, ignore saved `models`) or `"explicit"` (always use saved `models` list)
- `models`: explicit panel list (used only in `explicit` mode)
- `judge`: default judge model (null = auto)
- `k`: default panel size
- `strategy`: default strategy
- `expose_panel`: default

**Inline `fusion` field overrides saved defaults field-by-field** — if a field appears in the request, it wins; otherwise the saved default applies.

## Strategy comparison

| Strategy | Calls made | Quality | Cost |
|---|---|---|---|
| `synthesize` | k panel + 1 judge | Highest — judge reads all answers and writes blended response | k+1 model calls |
| `best_of` | k panel only | Lower — just picks the longest panel answer, no synthesis | k model calls |

## Streaming (SSE)

When `stream: true`:
1. `_fusion` frames are pushed as each panel member starts/finishes (status: `ok`/`failed` + content)
2. When the judge fires, a `_fusion` frame with `event: "judge"` is pushed
3. The final assistant message is the synthesized answer
4. `[DONE]` terminates the stream

Non-streaming: single JSON response. `x_fusion` contains panel answers only if `expose_panel: true`.

## Internal constants (from fusion.ts)

- `DEFAULT_PANEL_K` = 4
- `HARD_MAX_PANEL_K` = 8
- `SYNTHESIS_QUORUM` = 2 (if < 2 panel members succeed, skip judge — return the single survivor directly)
- `MAX_SLOT_ATTEMPTS` = 4 (per-slot key-rotation budget before dropping a slot)
- `MAX_JUDGE_ATTEMPTS` = 6

Operator settings: `fusion_default_k`, `fusion_max_k` (in settings table).

## Model ID matching

`isFusionModel()` matches case-insensitively:
- `fusion` → ✅
- `FUSION` → ✅
- `fusion:smart` → ✅ (suffix form for future variants)
- `auto` → ❌ (different virtual model)

## Using from Hermes

Point a Hermes provider at FreeLLM-API and use `model: fusion`:

```yaml
# config.yaml
providers:
  freellmapi:
    base_url: http://localhost:3001/v1
    api_key: ${FREELLMAPI_API_KEY}
    timeout: 120
    max_tokens: 16384
```

Then in chat: `/model freellmapi/fusion` — every prompt gets the multi-model panel + judge treatment.

**Note:** Fusion adds latency (panel runs in parallel, then judge runs serially). For simple Q&A use a single model instead. Reserve `fusion` for research, analysis, or any prompt where the cost of being wrong outweighs the extra latency.
