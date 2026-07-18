# 自建 hindsight 服务器 (local_external 模式)

基于 2026-06-20 迁移: hindsight cloud (`mode: cloud`) 欠费(402) → 自建 Docker hindsight 服务 (`mode: local_external`)。

## 场景

- hindsight cloud 每日消耗耗尽（`recall_budget: mid` + `auto_recall:true` 每轮对话导致）
- 已有 Docker 版 hindsight 服务在本地运行（自建）
- 需要多个 agent（金木水火土）共享记忆池，但拒绝云费用

## 切换步骤

### 1. 确认自建服务可用

```bash
curl http://localhost:8888/health
# 期望: {"status":"healthy","database":"connected"}
```

### 2. 修改 hindsight config

```bash
cat > ~/.hermes/hindsight/config.json << 'EOF'
{
  "mode": "local_external",
  "bank_id": "hermes",
  "recall_budget": "low",
  "memory_mode": "hybrid",
  "auto_retain": true,
  "auto_recall": false,
  "retain_async": true
}
EOF
```

| 字段 | 云值 | 本地推荐值 | 原因 |
|------|------|-----------|------|
| `mode` | `cloud` | `local_external` | 指向自建服务 |
| `recall_budget` | `mid` | `low` | 本地免费用，但 low 足够 |
| `auto_recall` | `true` | `false` | 云时代每轮查询耗 token；本地可开 true，无费用 |
| `bank_id` | `hermes` | `hermes` | 保持相同 bank_id 才能访问旧记忆 |

### 3. 设置 API URL 环境变量

```bash
echo 'HINDSIGHT_API_URL=http://localhost:8888' >> ~/.hermes/.env
```

`hindsight_client` 的 SDK 读取 `HINDSIGHT_API_URL` 环境变量，不设置则默认连 cloud。

### 4. 验证 SDK 读写

```python
from hindsight_client import Hindsight
import os
h = Hindsight(
    api_key=os.environ["HINDSIGHT_API_KEY"],
    base_url=os.environ["HINDSIGHT_API_URL"]  # http://localhost:8888
)

# 写入
h.retain(bank_id="hermes", content="测试本地服务", context="验证")

# 召回
resp = h.recall(bank_id="hermes", query="测试", budget="low")
for r in resp.results:
    print(r.text)  # 注意: .text 不是 .content
```

## Docker 容器访问自建服务

### 原理

macOS Docker Desktop 内建 `host.docker.internal` DNS，容器内部通过该域名访问宿主机。

### 配置

```bash
# 在 Docker 容器的 .env 中
echo 'HINDSIGHT_API_URL=http://host.docker.internal:8888' >> /opt/data/.env
```

### 验证

```bash
docker exec <容器名> sh -c 'curl -s http://host.docker.internal:8888/health'
# 期望: {"status":"healthy","database":"connected"}
```

### 各 agent 配置值

| bot | 位置 | HINDSIGHT_API_URL |
|-----|------|-------------------|
| 土 | 本机 Mac | `http://localhost:8888` |
| 金/木 | Docker 容器 | `http://host.docker.internal:8888` |
| 火/水 | Docker 容器 | `http://host.docker.internal:8888` |

所有 bot 保持相同 `bank_id: hermes` → 自动共享记忆池。

## API 端点发现

自建 hindsight 服务的 API 路径可能与 cloud 不同。通过 `/openapi.json` 自动发现：

```bash
curl -s http://localhost:8888/openapi.json | python3 -c "
import json,sys
d=json.load(sys.stdin)
for p in sorted(d.get('paths',{}).keys()):
    print(p)
"
```

关键端点：

| 端点 | 方法 | 用途 |
|------|------|------|
| `/v1/default/banks/{bank_id}/memories` | POST | 批量创建 (`{"items": [...]}`) |
| `/v1/default/banks/{bank_id}/memories/recall` | POST | 语义召回 |
| `/v1/default/banks/{bank_id}/memories/list` | GET | 列表查看 |
| `/v1/default/banks/{bank_id}` | GET | bank 详情 |
| `/v1/default/banks/{bank_id}/stats` | GET | 统计 |
| `/health` | GET | 健康检查 |

## 记忆天然迁移（无需手动导入）

切换到 `local_external` 后，**auto-retain 会在每轮对话自动写入本地服务**。之前已从 cloud 导出到本地文件（`hindsight-export-*.json`）的记忆，通过**正常对话**即可自然填充到本地。

原因：Hermes 的 auto-retain 每轮存储对话摘要，这些摘要在 cloud 期间已记录。切换后继续对话，本地服务逐步积累与之前等质的记忆。

### 如需手动导入 JSON 备份

```bash
cd /Users/macos/.hermes/hermes-agent && source venv/bin/activate
python3 << 'PYEOF'
import json, os
with open("/Users/macos/.hermes/.env") as f:
    for line in f:
        if "HINDSIGHT_API_KEY" in line:
            key = line.strip().split("=", 1)[1]
            break

from hindsight_client import Hindsight
h = Hindsight(api_key=key, base_url=os.environ.get("HINDSIGHT_API_URL", "http://localhost:8888"), timeout=120)

with open("导出文件路径.json") as f:
    d = json.load(f)

# 遍历所有类型，逐个 retain（每次 retain 会调 LLM 提取实体，所以慢）
for mtype, items in d.get("memories", {}).items():
    for item in items:
        h.retain(bank_id="hermes", content=item["text"],
                 context=item.get("context", ""),
                 tags=item.get("tags", []))
        print(f"  ✓ {item['text'][:50]}")
PYEOF
```

**注意**：逐个 retain 会触发 LLM 实体提取，每个调用耗时数秒。82 条约需 5-10 分钟。

## 全库扫描技巧

hindsight 的 `recall` 需要非空 query。使用高频词可扫描大部分记忆：

```python
# "the the the" 高频词召回所有含英文的记忆
resp = h.recall(bank_id="hermes", query="the the the the the", budget="high")

# 中文高频词
resp = h.recall(bank_id="hermes", query="用户 的 了 是 在", budget="high")
```

注意：不保证 100% 覆盖率，但对于日常检查足够。

## 费用对比

| 维度 | cloud | local_external |
|------|-------|----------------|
| 推理 token | 按量计费（retain + recall 都花钱） | 0（自建服务用本地 LLM） |
| API 调用 | 按量计费 | 0 |
| 多 agent 共享 | ✅ 同 bank_id | ✅ 同 bank_id + 同 HINDSIGHT_API_URL |
| 维护成本 | 0 | 需保持 Docker 服务运行 |
| 离线可用 | ❌ | ✅ |
| 记忆安全 | 云端存储 | 本地存储 |
