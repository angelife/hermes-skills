# Memory Optimization Session — June 21, 2026

Context: Hindsight v0.8.3 running in Docker on macOS (Docker Desktop VM, 8GB limit).
Python hindsight-api process consuming **2.76GB RSS**. Total container ~3.1GB.

## Environment at Time of Analysis

Only 5 env vars set (all others used defaults):
```
HINDSIGHT_API_CONSOLIDATION_WORKERS=1
HINDSIGHT_API_DB_POOL_SIZE=5
HINDSIGHT_API_LLM_MODEL=meta/llama-3.1-8b-instruct
HINDSIGHT_API_WORKERS=1
HINDSIGHT_API_WORKER_ID=hindsight-prod
```

## Key Defaults That Cost Memory

| Config | Default | Impact |
|--------|---------|--------|
| `embeddings_provider` | `local` | Loads `BAAI/bge-small-en-v1.5` via ONNX → 500MB+ |
| `reranker_provider` | `local` | Loads `cross-encoder/ms-marco-MiniLM-L-6-v2` → 200-500MB |
| `HINDSIGHT_ENABLE_CP` | `true` | Node.js next-server → 135MB |
| `db_pool_min_size` | 5 | 5 idle PG connections |
| PG shared_buffers | 256MB | Embedded pg0 default |
| PG maintenance_work_mem | 512MB | Very generous for embedded use |

## Peak RSS History

```
VmPeak: 8360404 kB (8.3GB virtual — mmap'd model files)
VmRSS:  2764464 kB (2.76GB physical — actual RAM)
```

## Models on Disk

```
~/.cache/huggingface/hub/ (217MB total)
├── models--BAAI--bge-small-en-v1.5/         # ONNX embeddings
└── models--cross-encoder--ms-marco-MiniLM-L-6-v2/  # transformers reranker
```

## ARM64 Compatibility

Confirmed: Hindsight publishes native ARM64 Docker images. `uname -m` inside the container returns `x86_64` on the current setup (macOS Rosetta emulation), but ARM64 images are available from the registry for direct deployment on ARM hardware.

## Summary of Potential Savings

| Lever | Saving | Cumulative |
|-------|--------|------------|
| Embeddings → API | -800MB | 2.76→1.96GB |
| Reranker → API/lazy | -300MB | 1.96→1.66GB |
| Disable Control Plane | -135MB | 1.66→1.53GB |
| PG memory tuning | -150MB | 1.53→1.38GB |
| Connection pool | -50MB | 1.38→1.33GB |

Total potential: **~1.4GB saved** (2.76GB → ~1.3GB)
