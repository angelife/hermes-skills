# provider-quota-debug — FreeLLM-API & Hermes provider 故障快速定位

**适用情况：** 金同学（Mi8 dipper）或其他 Hermes 实例遇到下列症状的任一种——
- `Title generation failed: LLM returned invalid response (type=str)` — FreeLLM-API 返 HTML 而非 JSON
- `Provider failed after retries` — 真实 provider 上游失败，需要查 root cause
- `send_path_degraded` / `httpx.ReadError` 交错出现时

## FreeLLM-API 容器配置（来源：一手实测）

**容器名：** `freellmapi-freellmapi-1`（不是 `freellmapi`，带前缀）

**docker-compose.yml 路径：** `/Users/macos/freellmapi/docker-compose.yml`

**关键 volume 映射：** `freellmapi-data` → `/app/server/data/` —— 这是 SQLite 数据库 + 其它持久状态。**容器 stdout 默认不打错误**，真正 stack 在 SQLite 里查。

**镜像内部：** `ghcr.io/tashfeenahmed/freellmapi:latest`，**没有 sqlite3 CLI、也没有 python3**，但有 node。

## 一手定位流程（task 包合规只读诊断用）

### Step 1 — 拿 container external logs

```bash
docker logs freellmapi-freellmapi-1 --since 1h 2>&1 | grep -i -A 20 "title_generation\|provider failed\|deepseek"
```

如果容器 stdout 是空的（典型），下一步必须查 SQLite。

### Step 2 — 把 db 抽出来用 mac sqlite3 读

容器内没有 sqlite3 CLI，且 `/usr/bin/sqlite3` 在 mac 默认有，可行路线：

```bash
docker cp freellmapi-freellmapi-1:/app/server/data/freeapi.db /tmp/freeapi.db
sqlite3 -header -column /tmp/freeapi.db "..."
```

**Task 包合规要点：只读，与主 db 分离、不修改原 db。** 测试完 `rm /tmp/freeapi.db`。

### Step 3 — 知道 db schema（实测结果）

```
tables:           api_keys, embedding_models, fallback_config, media_models,
                  models, profile_models, profiles, provider_quota_observations,
                  provider_quota_state, quirk_targets, quirks,
                  rate_limit_cooldowns, rate_limit_usage, requests,
                  sessions, settings, users

注意：没有 channels 表。是 models 表代替。
```

### Step 4 — 关键查询模板

**该 model 当前 enabled 状态 + 同名多通道：**
```sql
SELECT id, platform, model_id, display_name, enabled, rpm_limit, rpd_limit, monthly_token_budget
FROM models
WHERE LOWER(model_id) LIKE '%needle%'
ORDER BY id;
```

"同名多通道"是 FreeLLM-API 的真实形态——同一 model 名可在 `nvidia` 和 `opencode` 双发，**field 是 `platform` 不用 provider**。

**最近请求 + 真实 error：**
```sql
SELECT id, platform, model_id, status, error, created_at
FROM requests
WHERE LOWER(model_id) LIKE '%needle%'
   OR LOWER(requested_model) LIKE '%needle%'
ORDER BY created_at DESC LIMIT 15;
```

**rate_limit_cooldowns schema（注意：表里只有 expires_at_ms + created_at）：**
```sql
SELECT * FROM rate_limit_cooldowns ORDER BY created_at DESC LIMIT 10;
```

`expires_at_ms` 是 ms epoch，转 `expires_at_ms / 1000` 到 `date -r @<sec>` 拿本地时间。

**quota 余量（NVIDIA / 其他 provider 的尝试命中）：**
```sql
SELECT platform, key_id, quota_pool_key, metric, limit_value, remaining_value,
       reset_strategy, source, confidence, notes, observed_at
FROM provider_quota_state
WHERE platform = 'nvidia' ORDER BY updated_at DESC LIMIT 10;
```

`remaining_value = 0` + `source = 'error_body'` 通常意味着该 key 最近一次报错是被 quota / 403 切断。

### Step 5 — 看 FreeLLM-API 内部路由逻辑（必要时）

NVIDIA family 有时是 `OpenCode Zen` 在跑，不是真 NVIDIA NIM——看 `models` 表 `platform = 'opencode'` 行存在就说明系统在走 promo trial 通道。

## Hermes 一侧典型错误对照（agent.log）

**`Auxiliary title_generation: LLM returned invalid response (type=str)` + 收到 `<!doctype html>` 的 body：**

- 不是 model 失败，是**路由错接到了 web UI 端点**（通常 `/`、`/index.html`、或某个 `/panel/`）
- 这种错误的典型诱因：请求 client ID 重复、idempotency 撞 cache 路由，或上游 fallback 链走到 web SPA fallback
- 不需要查 `models` 表，需要查 Hermes `auxiliary_client` 代码 + FreeLLM-API 路由分发
- 不在本参考范围内的"根因级别"——这条只是症状层面

## 在 SQLite 排查时要警惕的常见 SQL 错误

- 不能用 `provider` 列 — 实际字段名是 `platform`
- 不能用 `priority` 列 — `models` 表没有这一列
- 没有 `disabled_reason` 列 — 用 `enabled` (0/1) 字段判断
- 没有 `provider` 列 — `provider_quota_state` / `provider_quota_observations` 也是 `platform` 字段
- 没有 `created_until` 列 — `rate_limit_cooldowns` 用 `created_at`+`expires_at_ms`

## 已踩过的坑

1. 容器内 `sqlite3` / `python3` 都没装，不能 in-container 调试
2. 默认 Dockerfile 不打开 application log 文件 descriptor，看不到 Python logging 流
3. migrations.js 是编译产物，改它不会反向安装——下次升级镜像会被覆盖
4. **`requests.status` 字段存的是字符串**（`success` / `error`），不是 `status_code` int。`status_code` 实际标准化在 `error` 字段的 body 里
