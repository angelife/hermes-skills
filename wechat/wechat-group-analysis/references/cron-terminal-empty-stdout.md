# Cron 跑 wechat-group-monitor：空 stdout 与恢复

会话：驭智AI群监控 cron（job 每 10m）  
日期：2026-07-17

## 结论（可复用）

1. **cron 会话 foreground `terminal` 常返回空字符串**（exit_code=0 也空）。不要据此判定脚本不存在或失败。
2. **可靠取输出**：`terminal(command=..., background=true, notify_on_complete=true)` → `process(action=wait)`，stdout 在 process 结果里。
3. **cron 里 `execute_code` 可能被拦**：`BLOCKED: … Cron jobs run without a user … approvals.cron_mode`。只用 terminal/process + 文件工具。
4. **脚本权威正文**：`skill_view(name='wechat-group-analysis', file_path='scripts/wechat-group-monitor.py')`。主路径 `~/.hermes/scripts/wechat-group-monitor.py` 缺失时，优先 `cp` 从技能目录复制；`write_file` 备选但注意转义问题（lint 可能将 `"` 误转为 `\"`）。
5. **安静条件**：脚本 JSON 的 `new==0` → 最终只回 `[SILENT]`；`new>0` → 中文总结新增内容特点，不贴 JSON。

## 推荐执行序列

```text
1. skill_view wechat-group-analysis（必要时再读 scripts/wechat-group-monitor.py）
2. terminal background:
     python3 ~/.hermes/scripts/wechat-group-monitor.py
   notify_on_complete=true, timeout>=120
3. process wait → 解析 JSON 一行
4. new==0 → [SILENT]
   new>0 → 结合 messages/文本字段中文摘要
```

## 正常安静样例（非故障）

```json
{"time": "2026-07-17T17:53:23+08:00", "new": 0, "members": 4, "active_now": 0, "top5": ["unknown: 21条, ESJ, 偶尔发言", "我: 6条, SJ, 偶尔发言", ...]}
```

→ 交付 `[SILENT]`。

## 勿固化的负向结论

- 不要写成「terminal 工具坏了」或「cron 读不到 ~/.hermes」——主会话可能正常；问题是 **cron foreground 取输出方式**。
- 不要因空输出立刻 `ln -sf` / 重装脚本；先 background 跑通。
