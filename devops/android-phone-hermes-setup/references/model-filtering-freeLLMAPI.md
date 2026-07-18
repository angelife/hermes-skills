# Model Filtering Results for freeLLMAPI Channel

## Test Date: 2026-06-26

## Channel: freeLLMAPI (http://192.168.50.98:3001/v1)

### ✅ Working Models (12)
- auto
- fusion
- kimi-k2.6
- deepseek-v4-pro
- minimax-m2.7
- mistral-large-3-675b
- deepseek-v4-flash
- glm-5.1 (fastest response)
- big-pickle
- mimo-v2.5
- nemotron-3-nano-30b
- nemotron-3-super-120b

### ❌ Failed Models (62) — Reasons by Category

**503 model_not_found (distributor routing error)** — New API can't find model mapping:
- deepseek-v4-pro (when listed in model table but not in distributor)

**403 Forbidden (NVIDIA NIM channel)**:
- llama-4-maverick
- llama-3.1-70b
- llama-3.3-70b

**404 Not Found (model removed/deprecated)**:
- gemma312b
- minimaxaiminimax-m2.7
- minimaxaiminimax-m3
- qwen3-30b-a3b
- qwen3-coder-480b
- owl-alpha
- compound
- glm-4.7
- gpt-oss-120b
- qwen3-30b-a3b-fp8
- nemotron-3-120b
- glm-4.7-flash
- llama-4-scout
- command-a-reasoning
- poolside-laguna-m.1
- mistral-large-3
- mistral-medium-3.5
- mistral-small-4
- stepfun-step-3.7-flash
- codestral
- devstral
- hermes-3-405b
- llama-3.3-70b-fp8-fast
- compound-mini
- gpt-oss-20b
- gpt-oss-safeguard-20b
- gemma-4-31b
- gemma-4-31b-it
- gemini-2.5-flash
- gemma-4-26b-it
- gpt-4.1
- glm-4.6v-flash
- magistral-medium
- gemma-4-26b-a4b
- gemma-4-26b-a4b-it
- nemotron-3-nano-30b-reasoning
- command-r
- dolphin-mistral-24b-venice
- gemini-2.5-flash-lite
- nemotron-nano-12b-vl
- poolside-laguna-xs.2
- command-r-2
- command-a
- llama-3.1-8b-instant
- ministral-3-8b
- nemotron-nano-9b-v2
- granite-4.0-h-micro
- liquid-lfm-2.5-1.2b
- liquid-lfm-2.5-1.2b-thinking
- llama-3.2-3b
- nemotron-3-ultra-550b

**No upstream key**: ~46 models lack API key in the freeLLMAPI distributor

## Other Channels Tested

### Agnes AI (https://apihub.agnes-ai.com)
- ✅ agnes-1.5-flash
- ⏳ agnes-2.0-flash (timeout, possibly dead)
- ❌ agnes-image-2.1-flash (429, no deployment)
- ❌ agnes-video-v2.0 (404)

### NVIDIA NIM (https://integrate.api.nvidia.com)
- ✅ google/gemma-2-2b-it
- ✅ meta/llama-3.1-8b-instruct
- ✅ meta/llama-3.3-70b-instruct
- ✅ deepseek-ai/deepseek-v4-flash
- ❌ mistralai/mistral-large (404, removed)
- ❌ microsoft/phi-4-mini-instruct (timeout)
- 100+ total models on NVIDIA NIM, mostly free open-source

### Mimo (https://token-plan-cn.xiaomimimo.com)
- ❌ All 401 — API Key expired

### Freemodel (https://api.freemodel.dev) — Paid
- ❌ gpt-5.4 (timeout)
- ✅ gpt-5.5
- ✅ gpt-5.4-mini

## Key Takeaways

1. **freeLLMAPI channel model list must be filtered** — leaving dead models causes 503 errors
2. **NVIDIA NIM is the largest free model source** — but models are removed periodically
3. **Agnes AI has limited working models** — only agnes-1.5-flash is reliable
4. **Always re-test after config changes** — model availability changes over time
