# NLM 无人化夜训任务单模板（2026-07-17）

## 触发

- 「让 NLM 布置今晚无人化训练任务」
- 「完全授权 / 无人监督你自己完成」
- 已有一批群文/技术消化材料在 notebook 中

## 问 NLM 的约束（必须写进 query）

1. 用户睡觉，全程无人值守
2. 不能出现需要用户确认/密码/拍板的步骤
3. 可自动推进、可验证、可写日志
4. 失败自动降级/跳过，不能卡死
5. 优先机制锁死与闭环验证
6. 总时长 4–8 小时

## 输出结构

```
# 今晚无人化训练任务单
## 0. 训练目标（≤3）
## 1. 前置自检（失败则降级）
## 2. 主任务链 5–8 项
每项：ID / 名称 / 目标 / 自动动作 / 成功判定 / 失败降级 / 产物 / 预计耗时
## 3. 禁做清单
## 4. 评分规则（0–100）
## 5. 凌晨交付物
## 6. 可复制给 agent 的完整执行 prompt
```

## 执行落盘

```
技术消化/夜训-YYYY-MM-DD/
  TASK.md
  wiki/Index.md
  YYYY-MM-DD - Briefing.md
  YYYY-MM-DD - AnalysisTable.md
  YYYY-MM-DD - ReviewChecklist.md
  YYYY-MM-DD - 凌晨交付.md

~/.hermes/state/night-training-YYYY-MM-DD/
  TASK.md
  MECHANISM_LOCK.md
  RUNLOG.md
  DELIVERY.md
  browser_cache_check.json
```

## 常见降级（不要卡死）

| 任务 | 失败原因 | 降级 |
|------|----------|------|
| last30days | CLI 未装 | 用 NLM 既有热点结论 |
| graphify 语义图谱 | 缺 LLM API key | 本地 wiki-graph / code-only |
| USB 手机供网 | Apple Silicon 无 RNDIS；Mi8 无 wlan0 | 家宽或纯离线任务 |
| 浏览器深挖 | 反爬 | 跳过该 URL，记录链接 |

## 机制锁死优先切片

1. Hindsight：`retain_every_n_turns=10`（`~/.hermes/hindsight/config.json`）
2. 报错先 `session_search`（SOUL 已有则确认，不另起炉灶）
3. OpenBridge/浏览器可达性自检
4. 知识先编译进 Obsidian/wiki 再问答
