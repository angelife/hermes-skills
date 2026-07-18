# Bot-Not-Responding Quick Diagnosis (2026-06-26)

## Symptom

User reports "Telegram bot not responding." Gateway process is alive, periodic refresh running.

## Investigation Steps

1. Check last few lines of gateway.log — are messages still coming in?
   - `tail -20 ~/.hermes/logs/gateway.log`
   - If you see "inbound message" entries, polling works. Problem is outbound.

2. Check gateway.error.log for upstream model API errors:
   - `tail -20 ~/.hermes/logs/gateway.error.log`
   - Look for RateLimitError (429), InvalidParams, auth errors

3. Differentiate the 429 source:
   - **Telegram API 429**: appears in gateway.log directly, bot can't send messages TO telegram
   - **Model provider 429**: appears in gateway.error.log as `RateLimitError`, provider=nvidia/etc. Bot can receive but can't generate AI replies.

## This Session's Findings

### NVIDIA API 429 (minimax-m2.7)
- Provider: nvidia (integrate.api.nvidia.com)
- Model: minimaxai/minimax-m2.7
- Error: HTTP 429 Too Many Requests across all 3 retry attempts
- All AI responses blocked — bot could receive messages but couldn't reply
- Fix: restart gateway to reset rate limit counters, or wait for cooldown

### Xunfei InvalidParams (xopqwen36v35b)
- Provider: xunfei (maas-api.cn-huabei-1.xf-yun.com)
- Error: RequestParamsError:Invalid Params (code 10163)
- Likely model-switch config mismatch — parameter format incompatible
- Not a gateway issue; needs provider/model config review

## Restart Procedure (quick)

```bash
launchctl unload ~/Library/LaunchAgents/ai.hermes.gateway.plist
sleep 3
launchctl load ~/Library/LaunchAgents/ai.hermes.gateway.plist
# Wait 10s, then verify:
tail -5 ~/.hermes/logs/gateway.log | grep Connected
```
