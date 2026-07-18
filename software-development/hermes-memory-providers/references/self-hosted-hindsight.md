# 自建 hindsight 本地服务配置记录

基于 2026-06-20 土同学的配置操作。用户自行在宿主机上通过 Docker 启动了 hindsight 服务。

## 连接信息

| 项目 | 值 |
|------|-----|
| 服务地址 | `http://localhost:8888` |
| 健康检查 | `curl localhost:8888/health` → `{"status":"healthy","database":"connected"}` |
| bank_id | `hermes`（保持与 cloud 一致，数据互通） |
| API Key | 仍需配置（`hsk_...`），即使 local_external 模式 SDK 也会发送此字段 |

## 配置

### config.json

```json
{
  "mode": "local_external",
  "bank_id": "hermes",
  "recall_budget": "low",
  "auto_retain": true,
  "auto_recall": false,
  "retain_async": true
}
```

### .env

```
HINDSIGHT_API_URL=http://localhost:8888
```

## 跨 bot 配置

| Bot | 容器 | URL |
|-----|------|-----|
| 土 | 宿主机 | `http://localhost:8888` |
| 金 | Docker | `http://host.docker.internal:8888` |
| 木 | Docker | `http://host.docker.internal:8888` |
| 火 | ? | `http://host.docker.internal:8888` |
| 水 | ? | `http://host.docker.internal:8888` |

## 验证方法

```bash
# 写入唯一标记并立即召回
python3 -c "
from hindsight_client import Hindsight
import os, uuid
h = Hindsight(api_key=os.environ['HINDSIGHT_API_KEY'],
              base_url='http://localhost:8888')
m = f'连通性验证_{uuid.uuid4().hex[:8]}'
h.retain(bank_id='hermes', content=m, context='test')
import time; time.sleep(1)
r = h.recall(bank_id='hermes', query=m, budget='low')
for i in (r.results or []):
    if m in i.text: print(f'✅ {i.text}')
"
```

或用已有脚本：

```bash
bash ~/.hermes/skills/software-development/hermes-memory-providers/scripts/verify_hindsight.sh
```

## API 端点发现

若需查询本地 hindsight 服务支持的端点，用 OpenAPI schema：

```bash
curl -s http://localhost:8888/openapi.json | python3 -c "
import json, sys
d = json.load(sys.stdin)
for path, methods in d.get('paths', {}).items():
    for method in methods:
        print(f'{method.upper()} {path}')
"
```

关键端点对照：

| 端点 | 用途 |
|------|------|
| `GET /health` | 服务器健康检查 |
| `GET /v1/default/banks/{bank_id}/stats` | bank 统计数据（类型分布+总数） |
| `GET /v1/default/banks/{bank_id}/memories/list` | 分页记忆列表 |
| `POST /v1/default/banks/{bank_id}/memories` | 创建记忆（接受 `{"items": [item]}`） |
| `POST /v1/default/banks/{bank_id}/import` | ⚠️ 仅用于 bank 模板/配置导入，非记忆数据 |

**导入速度**：每条 ~5-10s（LLM embedding + 实体提取），1,294 条约 1.5-2 小时。须用 `background=true notify_on_complete=true` 避免超时。

## 进度监控

```bash
curl -s -H "X-API-Key: $HINDSIGHT_API_KEY" \
  http://localhost:8888/v1/default/banks/hermes/stats \
  | python3 -c "import json,sys;d=json.load(sys.stdin);n=d['nodes_by_fact_type'];print(f'observation={n[\"observation\"]}  world={n[\"world\"]}  experience={n[\"experience\"]}  total={d[\"total_nodes\"]}')"
```

## .env 引号处理验证

Hermes 使用 `python-dotenv` 解析 `.env`，标准 dotenv 格式的引号会被自动剥离：

```python
# .env 文件中: KEY="value" 或 KEY='value'
# python-dotenv 解析后: KEY → value（引号被剥离）
```

实测验证（Docker 容器内）：

```bash
docker exec <container> python3 -c "
from dotenv import load_dotenv
import os
load_dotenv('/opt/data/.env')
key = os.environ.get('XUNFEI_API_KEY', '')
print(f'len={len(key)}, starts_quote={key.startswith(chr(34))}')
# → len=65, starts_quote=False  # 引号已剥离
"
```

所以 `XUNFEI_API_KEY="074bcc..."` 这类写法虽然不美观，但功能上没问题。

## ⚠️ 已知问题：hindsight 进程内存消耗过高

**现象**：hindsight Docker 容器（v0.8.3，约 15h uptime）消耗 **3.5GB RSS**，其中 Python API 进程占 ~3.2GB，数据库仅 263MB。

**内存分布**：

| 进程 | 内存 | 说明 |
|------|------|------|
| `hindsight-api` (Python/FastAPI) | ~3.2GB | 主 API 进程 |
| PostgreSQL | ~200MB | 20 个连接 |
| next-server (Web UI) | ~120MB | 内置管理界面 |
| **合计** | **~3.5GB** | |

**根因分析**：
- 数据库 263MB（3,312 条记忆节点），Python 进程 RSS 是数据的 **12 倍+**，比例不正常
- 后台 `consolidation`（记忆整合）持续调用 LLM 做实体识别、语义链接、因果链接（日志：`stage=llm.openai.consolidation+structured`）
- **处理完后 RSS 不释放**，随运行时间持续累积
- 20 个 PG 连接多数处于 idle，连接池未回收
- 未找到现成配置项可限制 consolidation 频率或内存上限

**快速诊断**：
```bash
# 整体内存概览
docker stats hindsight --no-stream --format "{{.Name}} {{.MemUsage}} {{.PIDs}}"

# 进程级 RSS 排行
docker exec hindsight ps aux | sort -k4 -rn | head -5

# 数据库磁盘体积（应与 RSS 对比）
docker exec hindsight du -sh /home/hindsight/.pg0/

# 日志中的 consolidation 活动
docker logs --tail 20 hindsight 2>&1 | grep -E "rss_mb|consolidation|WORKER_STATS"
```

**缓解思路**（未验证）：
- 降低 consolidation worker 数（当前无配置项，可能需要改代码或环境变量）
- 定时重启 hindsight 容器（cron 每日凌晨重启，释放累积内存）
- 限制 PG 连接池大小
- 禁用 Web UI（next-server 省 ~120MB，非主要问题源）
- 升级 hindsight 版本（后续版本可能已修复）

**写报告给外部工具（Claude/ChatGPT）排查时的格式要点**：
1. **先声明目标**：开头第一句写"目标是控制内存占用"或"想解决什么问题"
2. **再列现状**：环境、版本、数据量、内存分布
3. **列出疑点**：观察到的不正常现象
4. **最后问问题**：具体、可操作的提问

**注意**：此问题与 hindsight 数据量无关，是 hindsight-api 进程自身的后台 LLM 处理不释放内存所致。增加更多 agent 共享同一 hindsight 实例不会加剧此问题。
