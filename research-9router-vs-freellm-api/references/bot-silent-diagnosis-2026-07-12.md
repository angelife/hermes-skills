# OmniRoute 2026-07-12 Diagnosis: Bot Silent Root Cause

## Symptom
Hermes bot stopped responding on Telegram. Gateway process alive, Telegram connected, but no AI replies.

## Root Cause Chain (verified via logs)
1. **OmniRoute was NOT running** — port 20128 had no listener
2. Hermes default provider was `agnes` → `localhost:3001` (freeLLMAPI, also not running)
3. All fallback_providers were direct upstream calls (opencode-zen, nvidia, agnes)
4. When ALL upstream providers simultaneously returned errors (429/timeout/connection-error), the bot went completely silent with NO fallback path

## Fix Applied
1. Started OmniRoute via `node bin/omniroute.mjs serve --daemon --no-open`
2. Changed Hermes config: `provider: omniroute`, `base_url: http://localhost:20128/v1`
3. Set default model to `oc/deepseek-v4-flash-free` (built-in free pool)
4. Added omniroute as first entry in fallback_providers

## Remaining Issue
Free key pool (`oc/`) has burst rate limits. Rapid consecutive tests exhaust quota. Wait 2-5 minutes between retries.

## Key Lesson
Always check OmniRoute is running FIRST when diagnosing "bot silent" issues. A dead routing layer takes down all providers simultaneously.
