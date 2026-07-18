# Hindsight Memory Diagnostics

## Objective
When hindsight consumes excessive memory (e.g. 3.5GB for a 263MB database), systematically identify where the memory is going and whether settings can be tuned.

**IMPORTANT: State the objective up front in any report — "we want to reduce memory to <target>". Don't just describe the problem.**

## Quick Stats

```bash
# Overview: all running containers
docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}\t{{.PIDs}}"

# Hindsight-specific
docker stats hindsight --no-stream --format "{{.MemUsage}} / {{.MemPerc}}"

# Data size on disk
docker exec hindsight du -sh /home/hindsight/.pg0/
```

## Memory Breakdown by Process

```bash
docker exec hindsight ps aux --sort=-%mem | head -20
```

Expected output shows:
- `hindsight-api` (Python/FastAPI) — usually the largest consumer (2-3.5GB RSS)
- `postgres` subprocesses — idle connections accumulate
- `next-server` (Web UI / Control Plane) — ~135MB

## Python RSS Diagnosis

The Python process RSS is the dominant consumer. To check precisely:

```bash
docker exec hindsight sh -c 'cat /proc/$(pgrep -f hindsight-api)/status | grep -E "VmRSS|VmPeak|VmSize"'
```

Values:
- `VmRSS` = actual physical RAM used
- `VmPeak` = peak RSS since process start (high peak = temporary spikes during consolidation)
- `VmSize` = virtual memory (mostly memory-mapped model files, not real RAM)

## Root Cause: Local ML Models (Not "Memory Leak")

The single biggest consumer is **locally-loaded ONNX + transformers models**, NOT data accumulation or PostgreSQL:

```bash
# Check what ML models are cached/loaded
docker exec hindsight du -sh /home/hindsight/.cache/huggingface/
docker exec hindsight ls /home/hindsight/.cache/huggingface/hub/
```

Default config loads three model artifacts into the Python process:

| Config Field | Default Value | Model | Estimated RSS |
|---|---|---|---|
| `embeddings_provider` | `local` | `BAAI/bge-small-en-v1.5` (ONNX) | ~300-500MB |
| `embeddings_onnx_model_id` | `intfloat/multilingual-e5-small` (cached) | ~300-500MB (onnx runtime) |
| `reranker_provider` | `local` | `cross-encoder/ms-marco-MiniLM-L-6-v2` (transformers) | ~200-500MB |

Total from ML models: **~1-1.5GB** of the Python process RSS, consumed at startup and never freed.

This is why the Python process shows high RSS even when the container was just restarted and has zero consolidation activity — the model weights are loaded into memory regardless.

## Environment Variable Audit

The hindsight config.py defines **200+ environment variables** with defaults. Only a handful are typically set explicitly:

```bash
docker exec hindsight env | grep HINDSIGHT | sort
```

To see what the actual active defaults are (vs. what was set explicitly):

```bash
docker exec hindsight python3 -c "
from hindsight_api.config import HindsightConfig
c = HindsightConfig.from_env()
for f in ['embeddings_provider','embeddings_onnx_model_id','embeddings_local_model',
          'reranker_provider','reranker_local_model','lazy_reranker',
          'enable_observations','enable_auto_consolidation',
          'worker_enabled','worker_max_slots','db_pool_min_size','db_pool_max_size',
          'recall_max_concurrent','skip_llm_verification']:
    print(f'{f}={getattr(c, f, \"N/A\")}')
"
```

## PostgreSQL Connection Analysis

```bash
# Count PostgreSQL processes
docker exec hindsight sh -c "ps aux | grep postgres | grep -v grep | wc -l"

# Check main postgres config for shared_buffers/work_mem
docker exec hindsight grep -E "shared_buffers|work_mem|effective_cache_size" /home/hindsight/.pg0/instances/hindsight/data/postgresql.conf
```

Key parameters:
- `shared_buffers` — typically 256MB
- `work_mem` — default 4MB, may be set as high as 64MB
- `maintenance_work_mem` — often 512MB
- `effective_cache_size` — default 4GB (estimation, not allocation)

Many idle PostgreSQL connections = connections not being recycled. Each idle connection consumes ~30-130MB RSS.

## Consolidation Status

```bash
# Current processing operations
curl -s http://localhost:8888/v1/default/banks/hermes/operations?status=processing | python3 -m json.tool

# Pending operations summary
curl -s http://localhost:8888/v1/default/banks/hermes/operations?status=pending | python3 -m json.tool

# Full stats (total nodes, links, pending consolidation count)
curl -s http://localhost:8888/v1/default/banks/hermes/stats | python3 -m json.tool
```

Key stats fields:
- `total_nodes` — total memory units stored
- `total_links` — temporal + semantic + causal links
- `pending_operations` / `operations_by_status` — consolidation queue depth
- `pending_consolidation` — items awaiting consolidation
- `last_consolidated_at` — when consolidation last completed

## Optimization Knobs

See the main SKILL.md "Hindsight Memory Optimization" section for the full recipe. Summary by impact:

1. **Switch embeddings to API** — saves ~500MB-1GB, set `HINDSIGHT_API_EMBEDDINGS_PROVIDER=openai`
2. **Switch reranker to API or lazy** — saves ~200-500MB, set `HINDSIGHT_API_LAZY_RERANKER=true`
3. **Disable Control Plane** — saves ~135MB, set `HINDSIGHT_ENABLE_CP=false`
4. **Reduce PG shared_buffers/work_mem** — saves ~100-200MB, tweak pg0 startup args
5. **Shrink DB pool min** — saves ~30-100MB, set `HINDSIGHT_API_DB_POOL_MIN_SIZE=2`

**Risk of #1:** Changing embeddings model invalidates all existing vectors. Recall quality degrades until re-consolidation.

## Diagnostics Report Template

When writing a report:

```markdown
**目标：** <state the objective clearly, e.g. "控制内存占用" or "把内存从3.5GB降到1GB以内">

**环境：**
- 镜像：<image>
- 数据量：<database size>（<node count> 条记忆节点）
- 已运行：<uptime>

**内存分布：**
| 进程 | 内存 | 说明 |
|------|------|------|
| hindsight-api (Python) | ~2.7GB | FastAPI + onnx + transformers models |
| PostgreSQL | ~0.8GB | N 个连接 |
| next-server | ~135MB | Web UI/Control Plane |
| **合计** | **~3.5GB** | |

**主动配置与默认值差异：**
<list env vars set vs defaults>

**优化方案：**
1. 关闭 Control Plane → 省 ~135MB
2. 嵌入改 API → 省 ~500MB-1GB
3. 懒 reranker → 省 ~200-500MB
4. 缩 PG 内存 → 省 ~100-200MB
5. 缩连接池 → 省 ~30-100MB

**想解决的问题：**
1. <specific question 1>
2. <specific question 2>
```

## Pitfalls

- **Don't trust `docker stats` alone** — it shows the container total but not the breakdown. Always use `ps aux --sort=-%mem` inside to see per-process.
- **Don't assume embeddings are remote because LLM is remote.** Default is `local`. Always verify with the config audit command above.
- **Idle PG connections are silent memory hogs** — they don't show errors, just accumulate. Each ~100MB.
- **The reports must state the goal up front** — the user corrected: "没写出我们的目标 控制内存的占用". Always lead with the objective, not just the symptoms.
- **Most env vars are NOT in .env** — only 5 were set in the audited environment. The default values live in `config.py`. Read the code, don't assume defaults from docs.
- **Changing embeddings provider silently degrades recall** — existing vectors become incompatible. Plan for re-indexing.
