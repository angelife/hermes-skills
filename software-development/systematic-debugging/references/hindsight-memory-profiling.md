# Hindsight Memory Profiling

## Goal

Diagnose why hindsight container uses excessive RSS (e.g., 3.5GB for a 263MB DB).

## Quick Diagnostic Commands

```bash
# 1. Container-level memory
docker stats --no-stream --format "table {{.Name}}\t{{.MemUsage}}\t{{.MemPerc}}\t{{.PIDs}}"

# 2. Process-level inside container
docker exec hindsight ps aux --sort=-%mem | head -20

# 3. API stats
curl -s http://localhost:8888/v1/default/banks/hermes/stats

# 4. Active operations (consolidation etc.)
curl -s http://localhost:8888/v1/default/banks/hermes/operations?status=processing

# 5. Database disk size
docker exec hindsight du -sh /home/hindsight/.pg0/

# 6. Logs — look for consolidation worker stats
docker logs hindsight --tail 50 2>&1 | grep -i "rss_mb\|WORKER_STATS"
```

## Common Pattern

| Layer | Normal RSS | Problematic |
|-------|-----------|-------------|
| `hindsight-api` (Python) | ~200-500MB | **3.2GB** (leak) |
| PostgreSQL (all children) | ~200MB | ~1.1GB (idle connections) |
| next-server (Web UI) | ~120MB | ~120MB (expected) |

## Key Diagnostics

- **Python RSS**: The `hindsight-api` process at `~3.2GB` for a 263MB DB is the primary red flag
- **PIDs count**: 175+ (mostly id le PG connections) — check PG connection pool config
- **consolidation**: Background LLM-based entity/semantic linking that accumulates RSS over time
- **PostgreSQL**: `shared_buffers=256MB`, `work_mem=64MB` — not the bottleneck

## Likely Root Cause

The `hindsight-api` (FastAPI + Uvicorn) runs background consolidation tasks using LLM calls for entity recognition, semantic linking, and causal linking. These processes don't release RSS after completion, causing linear memory growth over time.

## Questions to Ask Maintainers

1. Can consolidation be disabled or scheduled (cron) instead of continuous?
2. Is there a `--lightweight` / `--memory-limit` mode?
3. Can Web UI (next-server) be disabled?
4. Can PG `max_connections` be lowered?
5. Latest version status: any memory fixes?

## Data to Collect Before Reporting

- `docker stats` output
- `ps aux --sort=-%mem` from inside container
- `curl .../stats` output (nodes, links, pending operations)
- logs showing `WORKER_STATS rss_mb=####`
- DB disk size

## Presenting Findings Template

```
目标：控制内存占用（当前 X GB，希望降到 Y GB）

环境：
- 镜像：ghcr.io/vectorize-io/hindsight:latest（v0.8.3）
- 数据量：数据库 Z MB，N 条记忆节点
- 运行时间：约 X 小时

内存分布：
| 进程 | RSS | 说明 |
|------|-----|------|
| hindsight-api (Python) | ~3.2GB | FastAPI |
| PostgreSQL | ~200MB | N 个连接 |
| next-server (Web UI) | ~120MB | 管理界面 |
| **合计** | **~3.5GB** | |

核心问题：
1. 数据库仅 Z MB，Python 吃掉 X GB —— 比例严重失调
2. consolidation 持续跑 LLM，RSS 不释放
3. N 个 PG 连接多数 idle 未回收
```
