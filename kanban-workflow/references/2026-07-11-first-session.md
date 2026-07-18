# Kanban Session Log — 2026-07-11 (双机联试首日)

## Setup
- 土同学 (本机, 192.168.1.8): Kanban init, GCC accepted
- 火同学 (SSH, 192.168.1.23): Kanban init, independently
- Two separate SQLite databases — not shared

## P2 Pipeline 演示
```
parent: P2: 信号融合 (triage)
  ├── P1: 链上数据采集 — 土同学 (ready)
  └── P1: 舆情分析 — 火同学 (running)
```
Result: Dispatcher auto-decomposed signal fusion into 3 sub-tasks (2 acquire + 1 fuse).

## P1 Fan-out 演示
```
parent: P1: 全链条安全审计 (todo)
  ├── 图片检查 (ready)
  ├── 链接检查 (ready)
  └── 安全标头 (ready)
```
Result: Dispatcher spawned 3 parallel audit tasks automatically.

## P5 Human-loop 演示
- Blocked `t_9e2f6b5c` (Audit Hugo site images) with reason "发现封面图 compress_ratio > 70%"
- Correct syntax: `hermes kanban block T_ID "reason text" --kind needs_input`
- Task shows `⊘` symbol in listing

## 站来地块 (Fire's 验证)
- SSH'd in, created "系统信息采集" task → dispatcher auto-completed to `done` ✅
- Produced 4 real artifacts: CPU_MODEL.txt (Intel i5-5257U), DISK_INFO.txt, FIRE_SYSTEM_REPORT.md, UPTIME.txt
- Proof of separate machine: Intel Core i5 vs Apple Silicon on 土同学

## Commands discovered
- `hermes kanban specify T_ID` — LLM-based task fleshing (can fail if LLM unavailable)
- `--force` flag on promote: bypasses parent dependency checks
- `kanban block T_ID reason` (positional, not --reason flag)
- `kanban log T_ID` — execution log with tool call history
