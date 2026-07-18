# Token Accounting — Daily Resource Tracking

## Source

Hermes stores provider-reported token counts in `~/.hermes/state.db`:
- `sessions` table: `input_tokens`, `output_tokens`, `cache_read_tokens`, `cache_write_tokens`, `reasoning_tokens`
- `messages` table (per-message detail, if needed)

Data comes from the provider API response (usage field in chat completions).

## Daily Query (Beijing Time UTC+8)

```sql
SELECT
  CASE
    WHEN source = 'telegram' THEN '📱 Telegram'
    WHEN source = 'api_server' THEN '🌐 API(扩展)'
    WHEN source = 'cli' THEN '💻 CLI'
    WHEN source = 'cron' THEN '⏰ Cron'
    ELSE source
  END as 来源,
  COUNT(*) as 会话数,
  COALESCE(SUM(input_tokens), 0) as 输入,
  COALESCE(SUM(output_tokens), 0) as 输出,
  COALESCE(SUM(cache_read_tokens), 0) as 缓存读,
  COALESCE(SUM(input_tokens + output_tokens + cache_read_tokens), 0) as 总计
FROM sessions
WHERE date(started_at, 'unixepoch', '+8 hours') = date('now', '+8 hours')
GROUP BY source
ORDER BY 总计 DESC;
```

## Tip: Sessions with Zero Tokens

Cron watchdog sessions (`source='cron'`) typically have `0` tokens because they don't make LLM calls. They're health checks, not conversations. Normal and expected.

## Cross-Device Strategy (Future)

Currently only tracks 土 (Mac). Other nodes (水/Mi6, 金/Mi8, 火/坚果Pro3, 夏虫) each have their own state.db and will need their own queries. Plan:

1. Phase 1: 土 only (done)
2. Phase 2: Each node runs a cron to push daily total to shared Hindsight bank
3. Phase 3: Unified gateway (9Router/FreeLLM-API) if adopted — single query point

## Optimization Discipline

- Free tokens are tracked as if they cost money — builds efficient habits
- Main cost driver: long Telegram conversations (context compaction → large cache_read_tokens)
- Goal: minimize token waste so the habit transfers to paid models or self-hosted (unlimited tokens)