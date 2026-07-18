# FreeLLMAPI 429 调试

## 2026-06-26 进阶排查：FreeLLM-API DB schema + NVIDIA 403 失效

### 新发现

1. **NVIDIA key 已返回 403（Authorization failed），不是 429**
   - 直接 `curl https://integrate.api.nvidia.com/v1/chat/completions -H "Authorization: Bearer ***" -d '{"model":"meta/llama-3.1-8b-instruct","messages":[{"role":"user","content":"hi"}],"max_tokens":10}'` → **403 Forbidden**
   - key 不是"限速"而是"过期"。FreeLLM-API 的 health checker 可能仍报告 `status: "healthy"`，但实际请求全部 403
   - 解决方案：去 dashboard 重新添加 NVIDIA key

2. **FreeLLM-API DB schema（确认版）**
   - 表名：`api_keys`（不是 `keys`）
   - 列：`id INTEGER, platform TEXT, label TEXT, encrypted_key TEXT, iv TEXT, auth_tag TEXT, status TEXT, enabled INTEGER, created_at TEXT, last_checked_at TEXT, base_url TEXT`
   - 查 NVIDIA key：`SELECT * FROM api_keys WHERE platform = 'nvidia'`
   - 返回 3 个 NVIDIA key（id=2, 5, 6），状态均为 healthy
   - 表名 `rate_limit_cooldowns`，列：`platform, model_id, key_id, expires_at_ms, created_at`
   - 当前有 22 条 cooldown 记录

3. **FreeLLM-API 版本 quirks（实测）**
   - `/health` → 返回 React SPA HTML，不是 JSON health check
   - `/v1/models` → 返回 `{"error":"Invalid API key"}`（需鉴权）
   - `/v1/chat/completions` → 也返回 `{"error":"Invalid API key"}`（需鉴权）
   - Unified API key：`freellmapi-d2451bbc0aa4b19939d46a2ec86caf8906332220cf650a94`

4. **FreeLLM-API 实际配置的 provider（DB 查询确认）**
   - `SELECT DISTINCT platform FROM api_keys` → `agnes, custom, nvidia, opencode`
   - catalog 定义 15+ provider，但实际有 key 的只有这 4 个
   - fallback chain 有 130+ 条目，但受限于实际 provider 可用性

### 分层诊断法（通用）

遇到"FreeLLM-API 卡住/不跳"时，按此顺序排查：

```bash
# 第 1 层：直接测上游 API（绕过 FreeLLM-API）
curl -s -w "\\nHTTP %{http_code} %{time_total}s" \
  https://integrate.api.nvidia.com/v1/chat/completions \
  -H "Authorization: Bearer YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"meta/llama-3.1-8b-instruct","messages":[{"role":"user","content":"hi"}],"max_tokens":10}'
# 403 → key 失效（不是限额）
# 429 → 限流中（等冷却或降频）
# 200 → upstream 正常，问题在 FreeLLM-API 层

# 第 2 层：看 FreeLLM-API 实时日志
docker logs -f freellmapi-freellmapi-1 --tail=50
# 找关键词：fail → key 失败, next → 切换 key, timeout → 网络问题
# 完全没日志 → 请求根本没进来，卡在 Hermes 层

# 第 3 层：查 FreeLLM-API 状态
curl -s http://localhost:3001/health  # 可能返回 HTML，不要依赖
curl -s http://localhost:3001/v1/models -H "Authorization: Bearer freellmapi-xxx"  # 需鉴权

# 第 4 层：查 DB cooldown 状态
docker exec freellmapi-freellmapi-1 node -e "
const sqlite = require('better-sqlite3');
const db = sqlite('/app/server/data/freeapi.db');
console.log(JSON.stringify(db.prepare('SELECT * FROM rate_limit_cooldowns WHERE key_id = 2').all()));
db.close();
"
```

### FreeLLM-API DB schema 速查

| 表名 | 列 | 用途 |
|------|-----|------|
| `api_keys` | id, platform, label, encrypted_key, iv, auth_tag, status, enabled, created_at, last_checked_at, base_url | API key 配置 |
| `rate_limit_cooldowns` | platform, model_id, key_id, expires_at_ms, created_at | 冷却记录 |
| `rate_limit_usage` | platform, key_id, kind, created_at_ms, ... | 用量统计 |
| `requests` | - | 请求记录 |
| `models` | id, platform, model_id, alias | 模型注册表 |
| `fallback_config` | id, model_db_id, priority, enabled | 路由优先级 |
| `settings` | key, value | 系统设置 |
| `profiles` / `profile_models` | - | 用户 profile |
| `provider_quota_state` | - | provider 配额状态 |

### Escalating Cooldown 机制（源码确认）

```javascript
// ratelimit.js
const COOLDOWN_DURATIONS = [
    2 * MINUTE,     // 第 1 次 hit → 2 分钟
    10 * MINUTE,    // 第 2 次 → 10 分钟
    HOUR,           // 第 3 次 → 1 小时
    DAY,            // 第 4+ 次 → 24 小时
];

// 区分两种 429：
// RPM/TPM 短暂超限 → 固定 90 秒冷却，不走升级
// RPD/TPD 耗尽 → 走升级冷却（2min → 10min → 1hr → 24hr）
// 403 Forbidden → MODEL_FORBIDDEN_COOLDOWN_MS（24 小时）
// 402 Payment Required → PAYMENT_REQUIRED_COOLDOWN_MS（24 小时）
```

**关键点**：NVIDIA NIM 的 40 RPM 是账户级限制，不是 per-key。FreeLLM-API 的 `selectKeyForModel()` 会轮换 key，但每个 key 撞的是同一账户墙。第 1 次 429 → key A 冷却 2 分钟 → key B 也 429 → 冷却 10 分钟 → ... → 所有 key 都冷却后，该模型直接挂。

### 解决方向（按优先级）

1. **去 dashboard 更新失效的 NVIDIA key**（403 时）
2. **清 cooldown**：`DELETE FROM rate_limit_cooldowns WHERE key_id = 2;`
3. **禁用 NVIDIA key**（如果 key 确实全失效且无新 key）
4. **对 NVIDIA 限速**：Hermes `human_delay` → mode: 'on', 间隔 3-6 秒
5. **走非 NVIDIA provider**：OpenCode、custom、groq、cloudflare 正常

---

## FreeLLM-API Fallback 源码机制（关键理解）

### 路由流程（router.js）
1. **`routeRequest()`** — 按策略排序 fallback chain，遍历每个模型
2. **`selectKeyForModel()`** — 对单个模型，在其所有 key 间 round-robin
3. 一个 key 429 → 写入 `rate_limit_cooldowns` → 下一个 key → 直到该模型所有 key 耗尽 → 跳到 chain 下一个模型
4. 最多 20 次尝试（每个 key 一次 + fallback 跨模型）

### 冷却升级机制（ratelimit.js）
```
COOLDOWN_DURATIONS = [2分钟, 10分钟, 1小时, 24小时]
```
同一 key 在 24h 窗口内每多 hit 一次 429，冷却翻倍。第 4 次后冻结一整天。
- **区分两种 429**：RPM/TPM 超限（短暂冷却 90s）vs RPD/TPD 耗尽（走升级冷却）
- NVIDIA NIM free tier 没有明确 RPD 限制，但账户级 RPS 限额打满后会触发升级冷却

### 为什么"不跳"
- fallback 确实会跨模型跳（chain 遍历），但：
  - **请求指定模型时**（如 Hermes 请求 glm-5.1），只在 glm-5.1 的所有 key 都 429 后才换模型
  - **NVIDIA 所有 key 共享账户** → 所有 key 同时 429 → 该模型直接挂
  - chain 里的下一个模型如果是 NVIDIA 的（llama-3.1-70b 等），也挂 → 无限 429
  - 只有非 NVIDIA 渠道（OpenCode、custom、groq、cloudflare）才正常

### NVIDIA 渠道的特征
- platform: `nvidia`, 所有 key_id 可能共用同一个账户
- models: z-ai/glm-5.1, deepseek-ai/deepseek-v4-pro, meta/llama-3.1-70b, moonshotai/kimi-k2.6 等
- 限额: free · 40 RPM（每账户 40 RPS），eval-only ToS
- 症状：`fail` + `next` 频繁出现，`next` 后仍然 `fail`

### 诊断步骤
1. 看日志：`fail` 后面跟 `next` 说明在轮换 key
2. 如果 `next` 后仍然同一个错误 → 账户级限额
3. 查 cooldown 表：`key_id=2` 通常对应 NVIDIA
4. 检查其他 provider（opencode, custom, groq, cloudflare）是否正常

### 参考文件
- FreeLLM-API 源码: `/app/server/dist/services/router.js`（路由核心）
- FreeLLM-API 源码: `/app/server/dist/services/ratelimit.js`（冷却/限流逻辑）
- FreeLLM-API GitHub: https://github.com/tashfeenahmed/freellmapi
