# Docker 容器 hindsight 迁移记录

基于 2026-06-20 迁移操作记录。金同学（@peterchan90_bot）的 Docker 容器从无 memory provider 迁移到 hindsight cloud。

## 注意事项

1. **先问用户** — 修改另一个 agent 的配置前，必须确认用户同意。不要擅自操作。
2. **备份** — 改任何配置文件前，先备份。

## 迁移步骤

### 1. 探查

```bash
docker exec hermes-minimaxlab sh -c 'cat /opt/data/config.yaml | head -30'
docker exec hermes-minimaxlab sh -c 'grep -A5 "^memory:" /opt/data/config.yaml'
docker exec hermes-minimaxlab sh -c 'uv pip list | grep hindsight'
docker exec hermes-minimaxlab sh -c 'grep HINDSIGHT /opt/data/.env'
```

### 2. 备份

```bash
docker exec hermes-minimaxlab sh -c 'cp /opt/data/config.yaml /opt/data/config.yaml.bak.$(date +%Y%m%d_%H%M%S)'
```

### 3. 修改 memory.provider

**正确做法**：限定只在 memory 区块内替换：

```bash
docker exec hermes-minimaxlab sh -c '
sed -i "/^memory:/,/^[a-z]/ s/provider: '\'''\''/provider: hindsight/" /opt/data/config.yaml
'
```

**全局替换会误伤**：`sed -i "s/provider: ''/provider: hindsight/" config.yaml` 会连 delegation、tts 等一起改。

### 4. 修复误伤的 delegation.provider

如果误伤了 delegation（`delegation.provider: hindsight`），修复：

```bash
# 先补回 memory 的 hindsight
sed -i "/^memory:/,/^[a-z]/ s/provider: ''/provider: hindsight/" config.yaml
# 再恢复 delegation 为空
sed -i "/^delegation:/,/^[a-z]/ s/provider: hindsight/provider: ''/" config.yaml
```

### 5. 添加 API Key

```bash
docker exec hermes-minimaxlab sh -c 'echo "HINDSIGHT_API_KEY=*** >> /opt/data/.env'
```

### 6. 升级客户端

```bash
docker exec hermes-minimaxlab sh -c 'uv pip install "hindsight-client>=0.8.0"'
```

### 7. 验证最终配置

```bash
docker exec hermes-minimaxlab sh -c '
echo "=== Memory ===" && grep -A5 "^memory:" /opt/data/config.yaml
echo "=== Delegation (不应被改) ===" && grep -A3 "^delegation:" /opt/data/config.yaml
echo "=== API Key ===" && grep HINDSIGHT /opt/data/.env | sed "s/hsk_.*/hsk_****/"
'
```

## 生效时机

memory provider 变更在 **下一 session 启动时**生效，无需重启容器。

## 回滚到本地 SQLite（undo）

如果云端 hindsight 配置后用户要求**撤销**（如"木同学是本地 hindsight"），需恢复原状：

### 回滚清单

| 要改的地方 | 云端模式值 | 本地模式值 |
|-----------|-----------|-----------|
| `config.yaml` → `memory.provider` | `hindsight` | `''` |
| `.env` → `HINDSIGHT_API_KEY` | `hsk_xxx` | 整行删除 |
| `hindsight/config.json` | `{"mode": "cloud", ...}` | 删除或清空文件 |
| `uv pip list` → hindsight-client | 已安装 | 可选卸载 |

### 步骤

```bash
# 1. 确认当前状态
docker exec <container_name> sh -c '
echo "=== memory.provider ===" && grep -A5 "^memory:" /opt/data/config.yaml | grep provider
echo "=== .env ===" && grep HINDSIGHT /opt/data/.env
echo "=== config.json ===" && cat /opt/data/hindsight/config.json 2>/dev/null || echo "（不存在）"
'

# 2. 恢复 memory.provider
docker exec <container_name> sh -c '
sed -i "/^memory:/,/^[a-z]/ s/provider: hindsight/provider: '\'''\''/" /opt/data/config.yaml
'

# 3. 从 .env 移除 HINDSIGHT_API_KEY
docker exec <container_name> sh -c '
sed -i "/^HINDSIGHT_API_KEY=/d" /opt/data/.env
'

# 4. 删除或清空 cloud config.json
docker exec <container_name> sh -c '
rm -f /opt/data/hindsight/config.json
# 或保留但改回 local:
# printf '"'"'{"mode": "local_embedded"}\n'"'"' > /opt/data/hindsight/config.json
'

# 5. 验证回滚
docker exec <container_name> sh -c '
echo "=== memory.provider（应为空）===" && grep -A5 "^memory:" /opt/data/config.yaml | grep provider
echo "=== .env（不应有 HINDSIGHT）===" && grep HINDSIGHT /opt/data/.env || echo "☑️ 已移除"
'
```

### 关键

- **本地 SQLite 不受影响**：`query.py` + `hindsight.db` 是独立文件，云端配置切换不影响它们的存在。改回 `provider: ''` 后 Hermes 恢复默认内置 memory，本地 `query.py` 独立脚本依然正常查询。
- **hindsight-client 包可选保留**：已安装的 `hindsight-client` pip 包不会干扰本地模式。Hermes 只是不加载它了。留着无害，移除也行。
- **无需重启容器**：memory provider 是 session 级配置，新 session 自动生效。但改 config 后习惯性 restart 也没副作用。
- **先确认后执行**：执行回滚前向用户确认步骤，让用户看一眼再执行，避免再次越界。

## 迁移本地 SQLite 数据到云端

已配好 cloud 模式后，之前本地存储的 hindsight 实体和关系不会自动同步。以下是从 Docker 容器本地 SQLite 迁移到云端 bank 的完整流程。

### 场景

- 容器的 `/opt/data/hindsight/hindsight.db` 已积累实体会话和关系
- 改成 `memory.provider: hindsight` + `mode: cloud` 后，新 session 的 retain 走云端，但老数据留在本地
- 需要把 18 个实体和 12+ 个关系这样的知识图谱迁移到共享 bank

### 流程

```bash
# 1. 从容器内导出 entities + relations 到宿主
docker exec <container_name> python3 -c "
import json, sqlite3, sys
db_path = '/opt/data/hindsight/hindsight.db'
conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()
cursor.execute('SELECT * FROM entities')
entities = [dict(row) for row in cursor.fetchall()]
cursor.execute('SELECT * FROM relations')
relations = [dict(row) for row in cursor.fetchall()]
conn.close()
json.dump({'entities': entities, 'relations': relations}, sys.stdout, ensure_ascii=False, default=str)
" > /tmp/mu_hindsight_export.json
```

### 上传到云端

使用宿主机上的 hindsight_client（通常在 Hermes venv 内）批量上传：

```python
# 使用 ~/.hermes/hermes-agent/venv/bin/python3
from hindsight_client import Hindsight
import json

h = Hindsight("https://api.hindsight.vectorize.io", api_key="hsk_xxx")
bank_id = "hermes"

with open("/tmp/mu_hindsight_export.json") as f:
    data = json.load(f)

items = []

# 每个实体 → 一条 memory
for e in data["entities"]:
    content = f"Entity: {e['name']} (type: {e['etype']})"
    if e["description"]:
        content += f" - {e['description']}"
    items.append({
        "content": content,
        "entities": [{"text": e["name"], "type": e["etype"]}],
        "tags": ["entity", "migration", "mu_local"],
    })

# 每个关系 → 一条 memory  
entity_lookup = {e["id"]: e["name"] for e in data["entities"]}
for r in data["relations"]:
    fname = entity_lookup.get(r["from_entity"], str(r["from_entity"]))
    tname = entity_lookup.get(r["to_entity"], str(r["to_entity"]))
    content = f"Relation: {fname} --[{r['rtype']}]--> {tname}"
    items.append({
        "content": content,
        "entities": [{"text": fname, "type": "entity"}, {"text": tname, "type": "entity"}],
        "tags": ["relation", "migration"],
    })

# 分批上传（cloud API 有超时限制，10 条一批）
for i in range(0, len(items), 10):
    batch = items[i:i+10]
    result = h.retain_batch(bank_id=bank_id, items=batch)
    print(f"Batch {i//10 + 1}: {result.items_count} items")

# 验证
resp = h.recall(bank_id=bank_id, query="Entity: NVIDIA")
for r in resp.results:
    print(r.text)
```

⚠️ **使用宿主机 hindsight_client**：把导出文件放 Mac 上，用 `~/.hermes/hermes-agent/venv/bin/python3` 跑上传脚本。容器内可能没有外网 API 访问，或 hindsight_client 版本不兼容。

### 先用 recall 去重

正式迁移前可以检查云里是否已有同名数据，避免重复：

```python
resp = h.recall(bank_id=bank_id, query='NVIDIA')
existing = set()
for r in resp.results:
    if r.type == 'world':
        existing.add(r.text.split(' | ')[0])
```

### 常见陷阱

1. **分批避免超时** — cloud API 并非批量越大越快。单次 `retain_batch` 传 30+ 条会超时。建议每批 ≤ 10 条。

2. **export 脚本用 `sys.stdout` + `>` 而不是中间文件** — Docker 内外的文件系统隔离。用 `docker exec ... > /tmp/file.json` 是最简单的导出方式。

3. **宿主机 hindsight_client 位置** — 系统全局可能没有安装。从 Hermes 的 venv 用：
   ```bash
   ~/.hermes/hermes-agent/venv/bin/python3 /tmp/upload.py
   ```

4. **`.env` 中的 `***` 陷阱** — 详见主 SKILL.md「API Key 被写入 `***`」陷阱。

## 用户纠正模式

用户对你的配置操作不满意时，你的自然反应可能是解释理由或论证正确性。**不要**。

### 正确流程

1. **认错** — `好的，我的错，不应该没问你就直接改了 XXX`
2. **问清意图** — `你的意思是 XX 要保持 YY 模式，不改成 ZZ，对吧？`
3. **提供回滚方案** — `我建议回滚：把 A 改回 B，移除 C。要我做吗？`
4. **执行** — 用户点头后做，不要自己做决定

### 反面例子

- ❌ `我是考虑到共享记忆更高效才改的`（辩解）→ 用户不想听理由
- ❌ `其实云端模式比本地好`（论证）→ 用户知道自己在做什么
- ❌ 直接执行回滚不确认（再次越界）→ 用户会失去信任
- ✅ `好的，我的错。要恢复原状吗？`（简洁认错+询问）

## 多 Agent 共享

所有 agent 用相同 HINDSIGHT_API_KEY + bank_id=hermes → 共享记忆池。

如需隔离，设 `HINDSIGHT_BANK_ID_TEMPLATE="hermes-{profile}"`。
