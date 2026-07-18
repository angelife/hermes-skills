# Rollover Workflow — 每日滚动与自愈预检

## 日常 flow（cron 每早执行）

```
1. 检查 _TODO.md 头部日期是否过期
2. 若过期 → 自愈预检（见下）
3. 读取 _EVENTS.jsonl 理解当前状态
4. 追加今天的工作记录 YYYY-MM-DD.md
5. 追加新任务事件到 _EVENTS.jsonl
6. 运行 reconcile-todo.py → 重建 _TODO.md
7. 补回 ## Lock 区块（reconcile 会清除它）
8. 归档今日快照 → 手动构造明日 `_TODO.md`（reconcile 总生成今天日期，不能用）
9. 追加滚动事件到 _EVENTS.jsonl
```

## 自愈预检步骤（_TODO.md 过期时）

```bash
# 0. 确定本地时区日期
TODAY=$(TZ=Asia/Shanghai date +%Y-%m-%d)

# 1. 归档旧 TODO
mkdir -p history
cp _TODO.md "history/_TODO_$(head -1 _TODO.md | grep -oP '\d{4}-\d{2}-\d{2}').md"

# 2. 运行合并器
python3 reconcile-todo.py

# 3. 检查并补回 Lock
grep -q "## Lock" _TODO.md || {
  # 找到 generated_by 行的行号，在其后插入 Lock
  # 实际用 patch 工具替代 sed
}
```

## 滚动到明日（end-of-day）

```bash
# 1. 快照今日（仅归档到 history/，根目录不保留副本）
cp _TODO.md "history/_TODO_$TODAY.md"

# 2. 计算明日
TOMORROW=$(TZ=Asia/Shanghai date -d "+1 day" +%Y-%m-%d)

# 3. 手动构造新 _TODO.md（❗ 不能跑 reconcile，因其总生成今天日期）
#    - LEGACY/INFRA：继承 @土 且 status != done 的任务
#    - AUTO：清空（含已认领但未完成的 AUTO——它们不跨日，来源 session 重建）
#    - 火或其他 bot 的任务不带到明天
#    - generated_by: rollover @ ...
#    - 补 ## Lock owner=土 current_session=土:cron:03a02cc22238

# 4. 追加滚动事件
cat >> _EVENTS.jsonl << 'EVTEOF'
{"id":"evt-YYYYMMDD-NNN","ts":"...","bot":"土","session":"土:cron:03a02cc22238","action":"note","note":"滚动 _TODO.md 至 TOMORROW_DATE，快照 TODAY_DATE 归档"}
EVTEOF
```

## 批量事件追加（cron 模式）

```bash
cat >> _EVENTS.jsonl << 'EVTEOF'
{"id":"evt-YYYYMMDD-NNN","ts":"...","bot":"土","session":"土:cron:03a02cc22238","action":"note","note":"事件说明"}
{"id":"evt-YYYYMMDD-NNN","ts":"...","bot":"土","session":"土:cron:03a02cc22238","task_id":"tsk-YYYYMMDD-NNN","action":"create","title":"任务标题","category":"AUTO"}
EVTEOF
```

## 2026-07-08 实测备忘

- `reconcile-todo.py` 每次调用都会覆盖整个 `_TODO.md`，包括被 `patch` 添加的 `## Lock`。必须每次 reconcile 后重新 patch。
- `_EVENTS.offset` 被 reconcile 更新为总行数。写 59 → 新增 4 条 → reconcile 后 offset=63。不阻止后续 clean read。
- 知 repo 内 `scripts/reconcile-todo.py` 和 vault 内 `reconcile-todo.py` 存在差异（前者有 `skip_bad_line` 调用，后者 `continue`）。使用 vault 内的版本。
- 快照仅归档到 `history/_TODO_YYYY-MM-DD.md`，根目录不保留副本。早期实践曾双写根目录和 history/，后统一为仅 history/。