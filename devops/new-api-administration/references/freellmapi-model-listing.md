# FreeLLMAPI 模型列表架构与过滤

## 架构概览

FreeLLMAPI 的 `/v1/models` 端点和 Admin `/api/models` 端点使用不同的数据源：

- **`/v1/models`**（OpenAI 兼容）→ `services/model-listing.js` → `buildModelListing()`
- **`/api/models`**（Admin）→ `routes/models.js` → 直接查 `models` 表

## `buildModelListing()` 核心逻辑

```javascript
// 非 unify 模式（默认）：按 model_id 去重，一模型一条
// unify 模式：按 model_groups 的 canonicalId 聚合
```

### 可用性计算

```sql
available = CASE WHEN m.enabled = 1 AND EXISTS (
    SELECT 1 FROM api_keys k
    WHERE k.platform = m.platform
      AND k.enabled = 1
      AND (m.key_id IS NULL OR k.id = m.key_id)
) THEN 1 ELSE 0 END
```

- `available=1` = 模型启用 + 有匹配的启用 API key
- `available=0` = 模型禁用 或 没有已启用的 API key

**重要**：`buildModelListing()` **永远返回所有模型**，不会过滤掉 `available=0` 的模型。它们只是标记为 unavailable 但仍然在列表中。

### 去重逻辑

非 unify 模式下，按 `model_id` 列做 `PARTITION BY`，选可用且最聪明的：

```sql
ROW_NUMBER() OVER (
    PARTITION BY m.model_id
    ORDER BY (availableExpr) DESC, m.intelligence_rank ASC, m.id ASC
) AS rn
```

所以如果同一个 model_id 既有免费 catalog 版本（available=1）又有付费自定义版本（available=0），去重后只有免费版本出现。

### `/v1/models` 端点的额外处理

```javascript
const listed = onlyAvailable ? allListed.filter(m => m.available === 1) : allListed;
```

- 默认（无 `?available=true`）：返回 **所有模型**（包括 available=0 的）
- `?available=true`：只返回可用模型
- 端点额外添加 `auto` 和 `fusion` 两个虚拟模型

## 如何从 `/v1/models` 中移除模型

### 方法 A：禁用 API key（不彻底）

在 `api_keys` 表设 `enabled=0`：

```sql
UPDATE api_keys SET enabled=0 WHERE id=3;
```

**结果**：关联的模型 `available=0`，但仍出现在列表里。仅当有同名免费版本时才不可见（去重机制）。

### 方法 B：删除模型行（彻底）

从 `models` 表直接 DELETE（需先删 fallback_config 的 FK 引用）：

```sql
DELETE FROM fallback_config WHERE model_db_id IN (SELECT id FROM models WHERE key_id IN (3,4));
DELETE FROM models WHERE key_id IN (3,4);
```

**结果**：模型完全从 `/v1/models` 消失。

### 操作步骤（Docker 环境）

```bash
# 1. 停止容器
docker stop freellmapi-freellmapi-1

# 2. 用临时容器修改 DB（docker cp 不支持已停止容器）
docker run --rm --user root \
  -v freellmapi_freellmapi-data:/data \
  -v /tmp:/tmp:ro \
  ghcr.io/tashfeenahmed/freellmapi:latest \
  sh -c "cp /tmp/freeapi.db /data/ && chown node:node /data/freeapi.db && chmod 644 /data/freeapi.db && rm -f /data/freeapi.db-wal /data/freeapi.db-shm"

# 3. 启动容器
docker start freellmapi-freellmapi-1
```

## 种子数据生命周期

### `seedModels()` — 首次部署时运行

```javascript
const count = db.prepare('SELECT COUNT(*) as cnt FROM models').get();
if (count.cnt > 0) return;  // 已有数据就跳过
```

**规则**：若 `models` 表非空（cnt > 0），完全不运行。删除的行不会重新插入。

### `migrateModels()` — 每次迁移时运行

对模型的操作：
- **UPDATE** — 重命名/更新限额（如 DeepSeek R1 → V3.1）
- **INSERT OR IGNORE** — 添加新模型（已存在则跳过）
- 不恢复已删除的行

### `migrateModelsV2()` — 第二遍迁移

- **DELETE** — 移除不存在的模型（如 Cerebras qwen-3-coder-480b）
- **INSERT OR IGNORE** — 添加已验证的 OR :free 模型

**结论**：从 `models` 表 DELETE 的行不会被后续 migration 恢复。

## 适用场景的实际案例

### 场景：过滤掉自定义付费上游模型

用户在 Hermes 的 `/model freellmapi` 中看到 70 个模型，包含来自付费上游（freemodel.dev、token-plan）的 6 个模型。

**分析**：
- 这些模型属于 `platform='custom'`、`key_id IN (3,4)`、`enabled=1`
- 去重后仍显示 5 个唯一模型：`auto`、`gemma3:12b`、`minimaxai/minimax-m3`、`qwen3-30b-a3b`、`minimaxai/minimax-m2.7`（和免费版重复但去重仍显示）

**解决**：
1. 先在 `api_keys` 设 `enabled=0` → 模型 `available=0` 但仍显示
2. 再从 `models` DELTE 6 行 + 配套 `fallback_config` 行 → 模型完全消失
3. 模型总数从 70 → 65

**注意**：Docker 环境下的 DB 修改需用临时容器解决权限问题，不能用 `docker cp` 到已停止容器。

## 模型 ID 格式

| 来源 | model_id 示例 | API 显示 ID | 说明 |
|------|--------------|-------------|------|
| NVIDIA NIM | `minimaxai/minimax-m2.7` | `minimax-m2.7` | 平台前缀被剥离 |
| 自定义 key | `minimaxai/minimax-m2.7` | `minimaxaiminimax-m2.7` | `/` 被移除（待确认机制） |
| Cloudflare | `@cf/qwen/qwen3-30b-a3b-fp8` | `qwen3-30b-a3b-fp8` | `@cf/` 前缀被剥离 |
| 自定义 key | `qwen3-30b-a3b` | `qwen3-30b-a3b` | 直接显示无前缀 |
| 自定义 key | `gemma3:12b` | `gemma312b` | `:` 被移除（待确认机制） |

模型 ID 在 API 输出中被去除了平台前缀和特殊字符，但 `buildModelListing()` 的 SQL 查询明确返回 `model_id`。可能存在运行时中间件或 version diff 导致 ID 转换。

## 相关 SQL 查询

```sql
-- 查看所有 API key
SELECT id, platform, label, base_url, enabled FROM api_keys;

-- 按 key 查看模型
SELECT m.id, m.model_id, m.platform, m.key_id, m.enabled 
FROM models m WHERE m.key_id IS NOT NULL;

-- 查看付费自定义上游的模型
SELECT m.id, m.model_id, m.platform, ak.label, ak.base_url
FROM models m
JOIN api_keys ak ON m.key_id = ak.id
WHERE ak.platform = 'custom';

-- 统计各平台模型数
SELECT platform, COUNT(*) as cnt FROM models GROUP BY platform;
```
