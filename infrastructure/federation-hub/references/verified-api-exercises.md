# Federation Hub 验证记录

## 启动

```bash
python3 ~/.hermes/scripts/federation_hub.py --port 28081
```

服务绑定 `0.0.0.0:28081`，SQLite 数据库 `~/.hermes/federation/hub.db`。

## 验证结果（2026-07-13）

### 注册 Agent

```bash
curl -s -X POST http://localhost:28081/register \
  -H "Content-Type: application/json" \
  -d '{"agent_id":"tu","name":"土同学","role":"coordinator","metadata":{"host":"MacMini","ip":"192.168.1.8"}}'
# → {"status":"ok","agent_id":"tu"}
```

### 创建任务

```bash
curl -s -X POST http://localhost:28081/tasks \
  -H "Content-Type: application/json" \
  -d '{"title":"微信文章自动归档","description":"拉微信→解密→分析→归档","created_by":"tu","priority":1,"tags":["wechat","data-pipeline"]}'
# → {"status":"ok","task_id":"task_b3340bd99cf5"}
```

### 查看状态

```bash
curl -s http://localhost:28081/status
# → {"agents":{"total":1,"online":1},"tasks":{"total":2,"pending":2},"events":1,"version":"1.0.0"}
```

### 获取 Agent 列表

```bash
curl -s http://localhost:28081/agents
# → [{"agent_id":"tu","name":"土同学","role":"coordinator","status":"online","last_seen":"...","created_at":"..."}]
```

## 所有 API 端点（已验证）

| 方法 | 路径 | 状态 |
|------|------|------|
| GET | /status | ✅ |
| GET | /agents | ✅ |
| GET | /tasks | ✅ |
| GET | /events | ✅ |
| GET | /memory | ✅ |
| POST | /register | ✅ |
| POST | /heartbeat | ✅ |
| POST | /tasks | ✅ |
| POST | /tasks/assign | 代码已就绪 |
| POST | /tasks/status | 代码已就绪 |
| POST | /lease/acquire | 代码已就绪 |
| POST | /lease/release | 代码已就绪 |
| POST | /events | 代码已就绪 |
| POST | /memory | 代码已就绪 |

## 注意

- 少量重复代码（`create_server` 函数声明了两次）不影响运行
- Hub 启动后自动创建数据库和表
- 使用 Python 内置 `http.server`，无需额外依赖
