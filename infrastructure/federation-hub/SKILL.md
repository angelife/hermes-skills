---
name: federation-hub
description: 五行舰队联邦控制平面 — Agent Registry + Event Log + Lease Manager + Task Ledger
trigger: 需要建立多 Agent 联邦架构、跨 Agent 协调、任务分发
---

# Federation Hub — 五行舰队联邦控制平面

## 架构

弱中心架构：Hub 只维护事实，不思考不执行。每个 Agent 自治，通过 HTTP 向 Hub 注册、心跳、拉取任务、推送事件。

## 组件

| 组件 | 端口 | 说明 |
|------|------|------|
| Federation Hub | 28081 | 联邦控制平面 — Agent Registry + Event Log + Lease Manager + Task Ledger |
| Kindle Dashboard | 28080 | 系统状态面板，含联邦舰队状态 |

## 文件

- `~/.hermes/scripts/federation_hub.py` — Hub 服务端
- `~/.hermes/scripts/agent_client.py` — Agent 客户端库
- `~/.hermes/federation/hub.db` — SQLite 数据库

## 启动与验证

```bash
# 后台启动 Hub
python3 ~/.hermes/scripts/federation_hub.py --port 28081

# 验证 Hub 运行
curl -s http://localhost:28081/status

# 注册 Agent
python3 ~/.hermes/scripts/agent_client.py register tu 土同学 coordinator

# 心跳
python3 ~/.hermes/scripts/agent_client.py heartbeat tu

# 查看状态 — 显示 Agent 在线数、任务数、事件数
python3 ~/.hermes/scripts/agent_client.py status

# 快速检查所有端点
curl -s http://localhost:28081/status       # → 服务状态
curl -s http://localhost:28081/agents       # → Agent 列表
curl -s http://localhost:28081/tasks        # → 任务列表
curl -X POST http://localhost:28081/register -H "Content-Type: application/json" \
  -d '{"agent_id":"test","name":"test"}'    # → 注册测试
```

## 进程管理

```bash
# 检查进程
ps aux | grep federation_hub | grep -v grep

# 停止
kill <PID>  # 或 Ctrl+C（前台）
```

## Dashboard 集成

联邦舰队状态自动渲染在 Kindle Dashboard（端口 28080）：
- Agent 在线数（在线/总数）
- 待办任务数
- 事件总数
- 各 Agent 名称、角色、在线状态

无需额外配置——dashboard 每次渲染时自动查询 Hub API。

## API 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /status | Hub 状态概览 |
| GET | /agents | Agent 列表 |
| GET | /tasks | 任务列表 (?status=&assigned_to=) |
| GET | /events | 事件日志 (?limit=&type=) |
| GET | /memory | 全局记忆 (?key=) |
| POST | /register | 注册 Agent |
| POST | /heartbeat | Agent 心跳 |
| POST | /tasks | 创建任务 |
| POST | /lease/acquire | 获取任务租约 |
| POST | /lease/release | 释放任务租约 |
| POST | /events | 推送事件 |
| POST | /memory | 设置全局记忆 |

参考 `references/verified-api-exercises.md` 查看已验证的 curl 示例。

## 架构原则

- **弱中心**：Hub 只维护事实，不思考不执行
- **Agent 自治**：每个 Agent 独立决策，通过 HTTP 与 Hub 通信
- **租约机制**：任务通过 Lease 分配，超时自动释放
- **事件驱动**：跨 Agent 事件通过 Event Log 同步