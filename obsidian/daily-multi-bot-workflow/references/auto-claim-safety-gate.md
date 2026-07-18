# auto-claim 安全门控

## 必做校验

`auto-claim.py` 在 claim 前必须检查任务标题/分类是否命中高风险关键词。
命中时不得认领，改为追加一条 `blocked` 事件，要求人工确认。

## 当前拦截词

删除、del 、rm 、清理、clean、rsync 、格式化、flash、强制、刷机、发布、deploy、exec 、xargs、危险

## blocked 事件格式

```jsonl
{"id":"evt-<ts>-<tid_suffix>","ts":"<iso>","bot":"<bot>","session":"<session>","task_id":"<tid>","action":"blocked","note":"high-risk task blocked: <category> <title>"}
```

## 兜底字段

如未来要扩展，新增风险级时不要在 `auto-claim.py` 里写死业务词，改成从 `blocklist.txt` 读取；当前版本的钥匙词列表仍放在脚本里作为默认值。
