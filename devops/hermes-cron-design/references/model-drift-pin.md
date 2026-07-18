# Cron 模型漂移跳过 + 用户「有啥用啥」（2026-07-17）

## 现象

```
Skipped to prevent unintended spend: global inference config drifted
(model 'deepseek-v4-flash-free' -> 'grok-4.5'), and this job is unpinned.
```

- 不是业务逻辑坏了，是防误花
- `deliver=origin` 会把失败摘要推到聊天；`local` 静默更难发现

## 用户偏好

**「有啥用啥、不挑食」** — 不要停任务等免费模型；钉到**当前可用模型**继续跑。

## 修复

```
cronjob action=update job_id=<id> model={"model":"<当前可用>"}
```

例：驭智AI群监控 `99ccc2038487` → 钉 `grok-4.5`。

`hermes cron update` 不存在，用工具 `cronjob`。

## 预防

| 类型 | 做法 |
|------|------|
| LLM agent cron | 创建时就 pin model |
| 纯脚本 watchdog | `no_agent=True`，不受模型漂移影响 |

## 相关

- 群监控脚本：`~/.hermes/scripts/wechat-group-monitor.py`
- 数据：`~/.hermes/group-monitor/`
- 误诊注意：cron 会话里若终端输出异常，先本机 `python3` 验脚本再信「文件不存在」
