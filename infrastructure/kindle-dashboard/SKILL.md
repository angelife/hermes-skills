---
name: kindle-dashboard
description: "Use when opening/fixing :28080 五行舰桥、看系统建成进度、今日干到哪、架构分层/服务监管、或用户说「一目了然/系统各部分工作状况/项目进度」。纯 HTML 面板（Kindle ePaper 友好）+ 待决策队列 + /api/status。"
trigger: 用户要看系统状态/建成进度/今日进度；新会话可检查待处理响应；改 dashboard 后必须重启并验 HTTP 200
---

# Kindle Dashboard · 五行舰桥

> **最终目的：** 对照 [架构 v2](https://angelife.github.io/knowledge-architecture/v2/) 把系统完全建成。  
> 面板顶部 = 总进度；中间 = 今天干到哪；下面 = 哪块服务挂了。

## 架构

```
浏览器 / Kindle  ──HTTP──>  dashboard_server.py (:28080)
                              │
         ┌────────────────────┼────────────────────┐
         ▼                    ▼                    ▼
   架构蓝图+探针          日报/TODO/task        scores.json
   服务端口探测           CREATIVE/晚课         pending 决策
```

## 组件

- **`~/.hermes/scripts/dashboard_server.py`** — HTTP 服务器，`:28080` bind `0.0.0.0`
- **`~/.hermes/state/actions/pending.json`** — 待用户决策
- **`~/.hermes/state/actions/responses/*.json`** — 用户已决策
- **`~/.hermes/state/self_check/scores.json`** — 自检评分（`unified-self-check` 写）
- **`/api/status`** — JSON：build_pct / layers / services（机器可读）
- 入口随局域网 IP 变：`~/kindle-bridge/sync-lan-ip.sh`（见 `lan-ip-auto-sync`）

## 面板功能（优先级从上到下）

| 区域 | 数据来源 | 说明 |
|------|---------|------|
| **系统建成总进度** | 架构 v2 蓝图 + 实时探针 | 规划稳定×0.6 + 实时健康×0.4 → build% |
| **今日进度** | 日报、`_TODO.md`、`task.yaml`、晚课、`CREATIVE.md` | 今天完成/未完成/阻塞/待拍板 |
| **架构分层状态** | 输入/处理/知识/输出/编辑 明细 | ●稳定 ○在建 !标稳定但不通 |
| **服务监管** | 端口+HTTP 探测 | 28080/10088/8888/10808/19825/8081/8089/8091/28081 + cron |
| 自检评分 | `scores.json` | 7 层 + 总分 |
| 系统状态 | cron / provider 池 | Agent 运行中 |
| 当前任务 | `active/task.yaml` | 焦点任务 |
| 联邦舰队 | `:28081` Hub | 未跑则标「Hub 未运行」 |
| 系统资源 | load / mem / disk | |
| 网络检查 | 代理/出口/DNS | |
| 记忆健康 | :8888 / exports | **勿 pgrep 判死** |
| 设备状态 | ADB / uptime | |
| 待决策 | pending + morning queue | |
| 最近事件 | runtime events | |

## 建成度怎么算

- 蓝图组件见 `dashboard_server.py` 的 `ARCH_BLUEPRINT`（与 architecture-v2 完成度明细对齐）
- 有 `probe` 的组件：端口/进程/路径实时检
- 无探针：planned=stable 视为 ok，wip 视为未完成
- 降级 = 规划 stable 但探针失败

## 改完必须闭环

1. `python3 -m py_compile ~/.hermes/scripts/dashboard_server.py`
2. `kill $(pgrep -f dashboard_server.py)` → 后台再启 `--port 28080 --bind 0.0.0.0`
3. `curl -s http://127.0.0.1:28080/health` → 200
4. 验收首页含：`系统建成总进度` / `今日进度` / `架构分层` / `服务监管`
5. 可选：`curl -s http://127.0.0.1:28080/api/status | python3 -m json.tool | head`

**交付 = 进程在听端口 + HTTP 200，不是桌面截图。** 见 `references/startup-discipline.md`。

## 按钮类型

| 按钮 | 含义 | 行为 |
|------|------|------|
| 普通选项 | 单次选择 | 写入响应文件，清空 pending |
| Always | 永久采纳 | 写入响应文件，标记 `always: true` |
| Session | 本次会话有效 | 写入响应文件，标记 `session: true` |
| Reject | 拒绝 | 写入响应文件，标记 `rejected: true` |

## 响应文件格式

```json
{
  "id": "test-002",
  "choice": "继续",
  "timestamp": 1783877698.09,
  "source": "kindle-dashboard"
}
```

## 参考

- `references/system-build-progress.md` — 建成进度公式、数据源、服务探针清单
- `references/startup-discipline.md` — 交付=端口在听，不是桌面 HTML
- `references/daemon-detection-patterns.md` — Hindsight 嵌入模式判断
- 相关：`lan-ip-auto-sync`、`unified-self-check`、`federation-hub`
