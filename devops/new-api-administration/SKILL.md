---
name: new-api-administration
title: New API 运维管理
description: New API（基于 one-api）网关的渠道管理、路由调试、配额诊断和常见报错处理
---

# New API 运维管理

## 架构核心

New API 渠道路由依赖三个要素：

1. **`channels` 表** — 渠道配置（name, type, key, base_url, models, group）
2. **`abilities` 表** — 每个渠道在每个分组下支持哪些模型（group, model, channel_id, enabled）
3. **缓存初始化** — 启动时从 abilities 表构建 `group2model2channels` 映射

直接写 `channels` 表不会自动生成 `abilities` 记录，导致路由器找不到渠道。

## 渠道管理

### 正确添加渠道

```bash
# 通过 API（推荐）
POST /api/channel/
Body: {"type":1, "key":"...", "models":"m1,m2", "group":"default"}

# 通过 Web 界面
# http://localhost:3000/channel → 添加渠道
```

以上两种方式会自动生成 `abilities` 表记录。

### 修复能力表（abilities）

如果渠道已有但 abilities 丢失：

```bash
POST /api/channel/fix
```

**⚠️ abilities 表 schema 可能随版本变化** — 不要硬编码列名。插入前先查：

```sql
PRAGMA table_info(abilities);
```

### 批量测试脚本

Shell 版本（可独立运行，不依赖 Python）：
```bash
bash scripts/batch-test-hetaosu-keys.sh
```

Python 版本（适合集成到 Python 工作流）：

```python
# 安全写法：先查列名
cols = [row[1] for row in cur.execute("PRAGMA table_info(abilities)")]
valid_cols = [c for c in ['channel_id','model','enabled','priority','weight','group','created_time'] if c in cols]
placeholders = ','.join(['?' for _ in valid_cols])
values = [cid, 'grok-4.5', 1, 0]  # channel_id, model, enabled, priority
# 如果 weight/group 存在才加
if 'weight' in cols: values.append(100)
if 'group' in cols: values.append('default')
cur.execute(f"INSERT INTO abilities ({','.join(valid_cols)}) VALUES ({placeholders})", values)
```

## 模型可用性发现（Model Discovery）

当用某组 Key 调 `/v1/chat/completions` 返回 `model_not_found` 时，Key 本身有效但该组无此模型。以下是找到正确模型名的方法：

### 方法一：Playground 配置导出

从 New API 页面导出 Playground 配置 JSON（点击 Playground → 下载/导出），`inputs.model` 和 `inputs.group` 字段直接显示了该用户实际能用的模型和所属组：

```json
{
  "inputs": {
    "model": "openrouter/free",     // ← 实际可用的模型名
    "group": "91普通用户"           // ← 用户所属组
  }
}
```

**注意：** Playground 配置里的模型名是精确值——直接复制到 API 调用即可，不要猜标准名。`gpt-4o-mini` 可能不存在但 `openrouter/free` 或 `gpt-5.5` 工作正常。

### 方法二：`/model-status` 页面

New API 内置 `/model-status` 页面展示**按组+模型**的实时统计（请求量、成功率、延迟）。选择你的 Key 所在组即可看到该组有哪些模型：

```
https://your-new-api-host/model-status
```

页面元素：组筛选 combobox（`All groups`）、模型名搜索、每个模型行含 Group 标签和状态（Normal/Warning/Abnormal）。

### 方法三：遍历常用模型名

```bash
for m in "openrouter/free" "gpt-5.5" "gpt-4o-mini" "claude-sonnet-4" "glm-4.5-flash" "deepseek-v3.2" "deepseek-chat"; do
  result=$(curl -sS -m10 "https://your-gateway/v1/chat/completions" \
    -H "Authorization: Bearer $KEY" \
    -H "Content-Type: application/json" \
    -d "{\"model\":\"$m\",\"messages\":[{\"role\":\"user\",\"content\":\"hi\"}],\"max_tokens\":5}")
  echo "$result" | grep -q '"choices"' && echo "✅ $m"
done
```

`model_not_found` 错误信息包含组名，可用于推断：`"No available channel for model gpt-4o-mini under group 91普通用户 (distributor)"` → Key 属 `91普通用户` 组，`gpt-4o-mini` 不存在。

### 关于 "distributor" 组

New API 分销商模式——"distributor" 类型用户组意味着 Key 是**分销商 Key**，供下游调用。该组可用的模型由管理员在渠道配置中指定映射，与本机渠道无关。分销商 Key 通过 `/v1/models` 返回空列表不代表 Key 无效。

### 用于找到实际模型名后的批量测试

```bash
# 对所有 Key 测试同一个模型
for key in sk-a sk-b sk-c; do
  result=$(curl -sS -m15 -x socks5h://127.0.0.1:10808 "https://gateway/v1/chat/completions" \
    -H "Authorization: Bearer $key" \
    -H "Content-Type: application/json" \
    -d '{"model":"glm-4.5-flash","messages":[{"role":"user","content":"hi"}],"max_tokens":5}')
  echo "$key: $(echo "$result" | grep -q '"choices"' && echo '✅' || echo '❌')"
done
```

## 渠道管理 — 查看

```bash
GET /api/channel/
```

需要 Admin 权限：Header 中加 `Authorization: Bearer ***` 和 `New-Api-User: <user_id>`。

### 直接从 DB 插渠道（不推荐，仅紧急情况）

API 添加渠道返回 500 时（如密钥列表过长导致请求体超限），可退而使用 SQLite 直接写入：

**⚠️ 渠道表可能被 Docker 重建清空。** 当 Docker 容器被删除再重建（`docker rm new-api && docker run ...`），如果挂载的 volume 路径变化或容器 `--volumes-from` 配置丢失，`channels` 表会变成空表，而 `tokens` 表（在另一挂载路径或同一 DB 的不同表）可能保留。排查方法：

```sql
-- 渠道丢失时的典型现象：
SELECT COUNT(*) FROM channels;  -- =0
SELECT COUNT(*) FROM tokens;    -- >0（令牌还在）
-- 解决：重新创建渠道（见下文），或者先检查 volume 挂载路径是否匹配
```

**必须同时插 `abilities` 表，否则路由找不到渠道。**
-- 先查最大 channel id
SELECT MAX(id) FROM channels;

-- 写入渠道（注意 `group` 保留字加反引号）
INSERT INTO channels (
    id, type, key, status, name, weight, created_time, test_time, response_time,
    base_url, other, balance, balance_updated_time, models, `group`, used_quota,
    model_mapping, status_code_mapping, priority, auto_ban, test_model, remark
) VALUES (
    <new_id>, 1, '<key(s)>', 1, '<name>', 100, strftime('%s','now'), 0, 0,
    '<base_url>', '', 0, 0, '<model1,model2,...>', 'default', 0,
    '', '', 100, 1, '<test_model>', '<remark>'
);

-- 必须写 abilities，否则路由找不到
INSERT INTO abilities (`group`, model, channel_id, enabled, priority, weight)
VALUES ('default', 'grok-4.5', <channel_id>, 1, 100, 100);

-- 然后通过 API 同步 rest：POST /api/channel/fix
```

**关键：** API 渠道操作会触发 eventos/caches 刷新，直写 DB 后必须调用 `POST /api/channel/fix`（或重启容器）让 abilities 缓存重建。

**⚠️ 已知失败案例（2026-07-18）：**
1. **`base_url` 尾部带 `/v1`** → New API 会追加 `/v1`，产生 `//v1/v1` 双重路径，上游返回 404 被误判为路由问题。**修复：** 渠道的 `base_url` 去掉尾部 `/v1`（写 `https://api.futureppo.top` 而非 `https://api.futureppo.top/v1`）。
2. **直接 SQL abilities 插入可行**（本站已验证）——写入 abilities 表 + 重启容器后渠道正常路由。`POST /api/channel/fix` 可能因 API bug（nil pointer dereference）无法调用。
3. **终极方案：** 通过 Web UI 添加渠道——触发完整内部事件链。

### 多 Key 池化渠道

NewAPI 支持在一个渠道内放入多个 API Key（换行分隔），自动轮转与容灾。适用于：
- 同一上游的大量免费/公益 key（如 hetaosu 的 100+ Grok 密钥）
### 批量测试脚本

Shell 版本（可独立运行，不依赖 Python）：
```bash
bash scripts/batch-test-hetaosu-keys.sh
```

Python 版本（适合集成到 Python 工作流）：

```python
# keys_blob = "\n".join(all_keys)  # 20-100+ keys, each on its own line
INSERT INTO channels (
    id, type, key, name, status, base_url, models, `group`,
    weight, priority, auto_ban, test_model, remark
) VALUES (
    <new_id>, 1, '<key1>\n<key2>\n<keyN>',
    'channel-name', 1, 'https://upstream.api/v1',
    'grok-4.5,grok-4', 'default',
    100, 100, 1, 'grok-4.5', 'multi-key pool'
);
```

**注意：**
- API 的 `POST /api/channel/` 对大 key blob（20+ keys）可能返回 500 — 退而使用 SQLite 直写
- `auto_ban=1` 自动跳过失效 key（非 200 响应），不掉池
- 权重和优先级统一设 100（对于同级 key pool）
- 写完后必须 `POST /api/channel/fix` 修复 abilities

## 令牌管理

### Token 表结构

```sql
-- tokens 表完整 schema（v6.x）
PRAGMA table_info(tokens);
-- id INTEGER PRIMARY KEY
-- user_id INTEGER           -- 所属用户
-- key varchar(128)          -- 密钥（sk- 开头）
-- status INTEGER            -- 1=启用, 0=禁用
-- name TEXT                 -- 显示名称
-- created_time INTEGER      -- Unix 时间戳
-- accessed_time INTEGER     -- 最后访问时间
-- expired_time INTEGER      -- 过期时间（-1=永不过期）
-- remain_quota INTEGER      -- 剩余额度（0=unlimited_quota 接管）
-- unlimited_quota numeric   -- 1=无限额度, 0/NULL=配额制
-- model_limits_enabled numeric -- 0=不限模型, 1=受 model_limits 限制
-- model_limits TEXT         -- 允许的模型列表（JSON 数组或空字符串）
-- allow_ips TEXT            -- IP 白名单（""=不限制）
-- used_quota INTEGER        -- 已用额度
-- group TEXT                -- 所属分组（"default" 等）
-- cross_group_retry numeric -- 是否跨组重试
-- deleted_at datetime       -- 软删除时间
```

### 创建令牌（DB 直写）

### 批量测试脚本

Shell 版本（可独立运行，不依赖 Python）：
```bash
bash scripts/batch-test-hetaosu-keys.sh
```

Python 版本（适合集成到 Python 工作流）：

```python
import sqlite3, secrets, time
from pathlib import Path

# ⚠️ DB 路径三种可能：先确认哪个存在
# 1. Docker bind mount（当前配置）：/tmp/na-current.db
# 2. 旧配置：/Users/macos/.hermes/data/new-api/one-api.db
# 3. 其他宿主机路径
# 验证：docker inspect new-api --format '{{range .Mounts}}{{.Source}}{{end}}'
db_paths = [
    Path("/tmp/na-current.db"),
    Path("/Users/macos/.hermes/data/new-api/one-api.db"),
    Path("/Users/macos/new-api-data/one-api.db"),
]
db = next((p for p in db_paths if p.exists()), db_paths[0])

con = sqlite3.connect(str(db))
con = sqlite3.connect(str(db))
key = "sk-" + secrets.token_hex(24)       # 51 字符密钥
uid = con.execute("SELECT id FROM users WHERE username='root'").fetchone()[0]
now = int(time.time())

con.execute("""INSERT INTO tokens (
    user_id, key, status, name, created_time, accessed_time, expired_time,
    remain_quota, unlimited_quota, used_quota, model_limits_enabled,
    model_limits, allow_ips, "group"
) VALUES (?, ?, 1, ?, ?, ?, -1, 0, 1, 0, 0, '', '""', 'default')""",
(uid, key, 'token-name', now, now))
tid = con.lastrowid
con.commit()

# 写完后必须重启 Docker 让缓存刷新
import subprocess
subprocess.run(["docker", "restart", "new-api"], timeout=60)
```

**关键参数说明：**
- `unlimited_quota=1` → 无限额度；设 0 则需配 `remain_quota`
- `expired_time=-1` → 永不过期
- `model_limits_enabled=0` → 不限模型
- `` `group` `` 是 SQLite 保留字，必须加反引号
- `"group" = 'default'` → 使用 default 分组渠道

**注意事项：**
- Docker 重启后 tokens 表持久保留（挂载卷），但 channels 表可能被重置
- 写完后去浏览器验证：`http://localhost:3000/console/token`

**⚠️ 关键陷阱：密钥输出会被截断**

### 批量测试脚本

Shell 版本（可独立运行，不依赖 Python）：
```bash
bash scripts/batch-test-hetaosu-keys.sh
```

Python 版本（适合集成到 Python 工作流）：

```python
# 方案 A：保存到文件（推荐）
Path("/tmp/new_token.txt").write_text(key + "\n")

# 方案 B：从 DB 回读
r = con.execute("SELECT key FROM tokens WHERE name=? ORDER BY id DESC LIMIT 1", ('token-name',)).fetchone()
if r: print(r[0])
```

密钥为 51 字符：`sk-` + 48 位 hex（`secrets.token_hex(24)`）。

### 令牌验证

```bash
# 测试 token 是否有效
curl http://localhost:3000/v1/models \
  -H "Authorization: Bearer sk-xxxxx"
# → HTTP 200 返回模型列表即 OK
```

### 令牌配额检查

```sql
SELECT id, name, key, remain_quota, unlimited_quota, used_quota, status FROM tokens;
SELECT id, username, quota, used_quota FROM users;
```

## 配额诊断

### 错误识别

- **"预扣费额度失败, 用户剩余额度: ＄X"** → 用户级配额不足
- **"empty stream with no finish_reason"** → 可能原因：配额耗尽、api_key 错误、YAML 配置损坏
- **"Invalid token"** → token 无效或 key 截断

### 配额检查

```sql
SELECT id, username, quota, used_quota FROM users;
SELECT id, name, remain_quota, unlimited_quota FROM tokens;
```

### 修复配额

```sql
UPDATE users SET quota = 100000000 WHERE id = 1;  -- root 用户加额度
```

强制 token 无限额：`tokens.unlimited_quota = 1` 但仍有用户级配额检查。

### 注意事项

- `tokens.unlimited_quota = 1` 不绕过用户级预扣费检查
- 大请求（~43K tokens）可能触发高额预扣费（~$2.65），需确保用户余额足够
- 配额修改后需重启 New API：`docker restart new-api`

## 常见故障排查

| 现象 | 可能原因 | 操作 |
|------|----------|------|
| provider failed after retries | 上游限流(429)、配额耗尽、key 错误 | 查 errors.log → curl 直测 |
| empty stream | 配额不足、YAML 缩进错误 | 查 quota → 修 config |
| Invalid API key | api_key 含字面 `...`（截断值） | 从 DB 读完整 key 重写 |
| 渠道存在但路由不到 | abilities 表缺失 | `POST /api/channel/fix` |
| `/model <provider>` 显示 0 模型 | Hermes provider 配置缺少 api_key，`/v1/models` 认证失败 | 从 settings 表查 unified_api_key 补到 provider 配置 |
| 渠道配好但报 404 | type=1 为标准 OpenAI 兼容 | 确认 /v1 前缀 |
| 渠道存在、abilities 存在、但报 `Invalid URL (POST /v1/v1/chat/completions)` | **`base_url` 尾部带了 `/v1`**，New API 自动追加 `/v1` 导致 `//v1/v1` | 渠道 base_url 去掉尾部 `/v1` |
| 无可用渠道（distributor） | 模型名大小写/前缀不匹配 | 检查 models 表 vs channel.models |
| 无可用渠道（distributor） | Docker 容器无法连上游（如 Cloudflare 1010） | **三路法区分：**<br/><br/>**① 宿主机直测上游**：`curl -sS -m 10 https://upstream/v1/models -H "Authorization: Bearer $KEY"`<br/>**② 宿主机走代理**：`curl -x socks5h://127.0.0.1:10808 -sS -m 10 ...`<br/>**③ Docker 容器内**：`docker exec new-api wget -q -O- --timeout=10 https://upstream/v1/models`<br/><br/>**判定：**<br/>• ①=200 但③不通 → **Docker 网络问题**，加 proxy env 或 `--network host`<br/>• ①=403/1010 → **上游被 Cloudflare 拦**，再测②<br/>• ①②都 403/1010 → **上游不可用**（通道耗尽/CF 防护），非网络配置问题。Docker proxy 加不加都没用 |
| upstream check failed: EOF | Docker 容器无外网 | 重启 Docker Desktop |

### 批量测试脚本

Shell 版本（可独立运行，不依赖 Python）：
```bash
bash scripts/batch-test-hetaosu-keys.sh
```

Python 版本（适合集成到 Python 工作流）：

```python
# 从 Mac 直测（隔离 Nut3 端问题）
key = conn.execute('SELECT key FROM tokens WHERE id=4').fetchone()[0]
urllib.request.Request('http://localhost:3000/v1/chat/completions', data, headers={'Authorization': 'Bearer sk-'+key})
```

重要：流式测试需用 `stream=True`，非流式可能掩盖问题。

## 集成 FreeLLMAPI 作为新渠道

FreeLLMAPI 是一个 OpenAI 兼容的聚合网关，自动聚合 16+ 免费 LLM 渠道（Gemini, Groq, Cerebras, Mistral, OpenRouter 等）。适合作为 New API 的上游。

### 部署步骤

1. `git clone https://github.com/tashfeenahmed/freellmapi.git`
2. 生成 encryption key：`openssl rand -hex 32`
3. `.env` 至少设置：
   - `ENCRYPTION_KEY=<结果>`
   - `PORT=3001`
   - `HOST_BIND=0.0.0.0`
4. `docker compose up -d`

### 首次设置

容器启动后会自动创建默认用户 `test@example.com` / `changeme123`：
- 登录：`POST /api/auth/login` with credentials
- 获取 unified API key：启动日志打印了 `Your unified API key: freellmapi-xxx`
- 或用 token 访问 `/api/keys`

### Hermes 多模型选项配置

**⚠️ 不要使用 `model: provider: custom` 旧格式** — 这会导致 Hermes 的 `/model` 命令只显示 `auto` 一个选项，不会 probe 上游 API 获取模型列表。根因：`get_compatible_custom_providers()` 函数只读 `providers:` keyed dict 和 `custom_providers` 列表，不读 `model: provider: custom` 下的 `base_url/api_key`，所以 Hermes 不把它当有 credentials 的自定义 endpoint。

**正确格式 — 使用 `providers:` keyed dict：**

```yaml
model:
  default: auto
  provider: freellmapi

providers:
  freellmapi:
    name: freeLLMAPI
    base_url: http://192.168.50.98:3001/v1
    api_key: freellmapi-xxx
    models:
      - deepseek-v4-pro
      - minimax-m2.7
      - ...  # 从 freeLLMAPI /v1/models 获取完整列表
```

这样 Hermes 的 `list_authenticated_providers()` 会正确识别 `freellmapi` 是一个自定义 endpoint，`/model` 命令会通过 `fetch_api_models()` probe `api_url` 获取 71 个模型。

`models` 列表写多少个，`/model` 命令就显示多少个。

**关键坑点：** 从旧格式迁移到新格式后，必须重启 Hermes gateway 才能生效（Python 进程缓存了旧配置）。

**auto vs 具体模型名：**
- `default: auto` → freeLLMAPI 自动选最优模型，不固定；收到 429 不会自动切换
- `default: deepseek-v4-pro` → 固定用这个模型；429 了需要自己换

### 批量替换密钥

**不要追加到旧 key blob — 整个替换掉失效批次。**

**⚠️ 前置：全量 Key 验证** — 同批次 key 可能部分失效（实测 10 key 有 4 个 timeout）。见 `references/hetaosu-multi-key-import.md` → 全量 Key 验证协议，逐个测过后只留 HTTP 200 通过的 key。

1. 先用全量验证脚本测所有 key，只留通过的
2. 连 SQLite：`UPDATE channels SET key='<newline-separated-keys>' WHERE id=<channel_id>`（只写验证通过的 key）
3. 同步 `~/.hermes/secrets/hetaosu-keys-full.txt`
4. `docker restart new-api`
5. 页面点「测试」验证

注意：渠道 ID 在 DB 重建后可能从 8 变成 1。abilities 可能丢失，需重新 INSERT。

### 配置 Docker 容器代理访问上游

NewAPI 在 Docker 中访问上游时如果被 Cloudflare 等拦截（1010 错误），而宿主机走代理能通，需给容器配置代理。

**⚠️ 已知陷阱：`host.docker.internal` 在 Docker for Mac 上只解析 IPv6**

Docker Desktop for Mac 上 `host.docker.internal` 在容器内经 `getent hosts` 验证仅解析到 IPv6 地址（如 `fdc4:f303:9324::254`）。如果宿主机上的代理（如 v2rayN SOCKS5）只监听 IPv4 `127.0.0.1:10808`，则设置 `https_proxy=socks5://host.docker.internal:10808` 会**导致所有出站连接失败**——容器尝试用 IPv6 连接代理，但代理没有 IPv6 监听。

**先测上游能不能直连，再决定要不要设代理：**

> 🆕 实战案例：2026-07-18 — 详见 `references/docker-proxy-debug-20260718.md`
> 40 个 hetaosu 密钥全部可用（HTTP 200），`model_not_found` 的根因是 `https_proxy=socks5://host.docker.internal:10808` 这个环境变量在 macOS Docker Desktop 上主动阻断连接。
> 修法：删掉容器重建（不加 proxy env），容器直连上游即可。

```bash
# ① 宿主机直连
curl -sS -m10 https://gy.hetaosu.xyz/v1/models -H "Authorization: Bearer $KEY"

# ② 宿主机走代理
curl -sS -m10 -x socks5h://127.0.0.1:10808 ...

# ③ 容器内裸连
docker exec new-api sh -c 'wget -q -T10 -O /tmp/t --header="..." --post-data="{}" https://gy.hetaosu.xyz/v1/models && cat /tmp/t'
```

**判定：**
- ①=200 且 ③=200 → **不需要代理**，不要设 `https_proxy`
- ①=不通但 ②=200 且 ③=不通 → **需要代理**，但必须先修 IPv4 监听问题

**如果你确定需要给容器配置代理，以下是正确做法：**

先确保代理能通过 Docker bridge 访问：
1. 在 v2rayN GUI 中将 SOCKS5 监听从 `127.0.0.1` 改为 `0.0.0.0`
2. 然后用 Docker bridge 网关 IP 替代 `host.docker.internal`：

```bash
# 方案 A：用 Docker bridge 网关 IP（v2rayN 需监听 0.0.0.0:10808）
docker run -d --name new-api \
  --restart unless-stopped \
  -p 3000:3000 \
  -v /Users/macos/.hermes/data/new-api/one-api.db:/data/one-api.db \
  -e HTTPS_PROXY=socks5h://172.17.0.1:10808 \
  -e HTTP_PROXY=socks5h://172.17.0.1:10808 \
  calciumion/new-api:latest
```

```bash
# 方案 B：host 网络模式（容器直接使用宿主机网络栈）
docker run -d --name new-api \
  --network host \
  -v /Users/macos/.hermes/data/new-api/one-api.db:/data/one-api.db \
  calciumion/new-api:latest
# 注意：host 模式在 Docker for Mac 上端口不通过 -p 暴露，容器内的 3000 端口直接在宿主机网络接口上监听
# 但 127.0.0.1:10808 直接可用
```

**如果上游本身就是打通的：** 什么都不加，`https_proxy` 反而会阻塞。

**最后：** 如果 ①宿主机直连 ②宿主机走代理 都返回 Cloudflare 1010，说明是上游通道耗尽（如 hetaosu 无 x.ai 账号），不是容器网络问题。加 proxy env 也没用。**三路法先判定再下手。**

### 诊断流程（通用版）

当渠道报错时，先三板斧区分问题层级：

| 测试 | 命令 | 问题层级 |
|------|------|---------|
| 宿主机直连 | `curl https://upstream/v1/models -H "Authorization: Bearer $KEY"` | 上游本身 |
| 宿主机走代理 | `curl -x socks5h://127.0.0.1:10808 ...` | 代理需求 |
| Docker 容器内 | `docker exec new-api wget -q -O- --timeout=10 ...` | 容器网络 |

- **用户偏好：dashboard 添加 key，禁止直接操作数据库**：虽然可以硬解密后 INSERT 到 api_keys 表，但用户看不到也不方便管理，而且用户明确要求删除这种 key 改用 dashboard 添加。**正确流程：登录 dashboard → Settings → 添加 provider key**，不要直接操作数据库
- **freeLLMAPI 本身是路由器，不会自动切换模型应对 429**：同一个 endpoint 可以调 72 个模型，但收到 429 后不会自动换，需要客户端自行换模型重试。`auto` 模型会让系统自动选最优，但也不处理 429 切换
- **NVIDIA NIM 的限额是账户级，key 轮换无效**：NVIDIA NIM free tier 按账户限制 RPS（40 RPM），freeLLMAPI 内多个 key 属于同一账户，轮换只延迟不绕过。关键：NVIDIA key 可能**静默变为 403（Authorization failed）**而非 429。直接 curl 测试 NVIDIA endpoint 返回 403 即 key 失效，不是限额问题。freeLLMAPI 的 health checker 可能仍报告 key 状态为"healthy"，但实际请求全部 403。解决：等配额刷新或换独立账户 key。详见 `references/freellmapi-429-debugging.md`
- **freeLLM-API 版本 quirks**：
  - `/health` 端点返回 React SPA HTML（不是 JSON health check），不能用 `grep "healthy"` 检测
  - `/v1/*` 端点需要 unified API key 鉴权（key 前缀 `freellmapi-`）
  - DB 表名是 `api_keys` 不是 `keys`；列包括 `id, platform, label, encrypted_key, iv, auth_tag, status, enabled, created_at, last_checked_at, base_url`
  - Cooldown 表名是 `rate_limit_cooldowns`，列包括 `platform, model_id, key_id, expires_at_ms, created_at`
  - 验证 key 是否活的：直接 curl NVIDIA endpoint `curl -s -w "\\n%{http_code}" https://integrate.api.nvidia.com/v1/chat/completions -H "Authorization: Bearer $KEY" -d '{"model":"...","messages":[],"max_tokens":10}'`
- **FreeLLM-API 的 escalating cooldown 机制**：同一 key 每多 hit 一次 429，冷却翻倍：`[2分钟, 10分钟, 1小时, 24小时]`。第 4 次 429 后冻结一整天。区分 RPM/TPM 短暂 429（固定 90s 冷却，不计入升级）和 RPD/TPD 耗尽（走升级冷却）。NVIDIA 因无明确 RPD 限制，账户级 RPS 打满后会触发升级冷却。
- **FreeLLM-API 实际配置的 provider**：DB 中 `SELECT DISTINCT platform FROM api_keys` 返回实际有 key 的 provider。catalog 里有 15+ provider 定义，但实际可能有 key 的只有 `nvidia`, `opencode`, `custom`, `agnes` 等几个。以实际为准。
- **对 NVIDIA 这类 per-account 限额的 provider，FreeLLM-API fallback 兜不住**：需要在 Hermes 配置层面加 `human_delay` 限速（mode: 'on'，间隔 3-6 秒），否则请求会卡在 cooldown 队列里。非 NVIDIA provider 不需要限速。
- **Tse 的沟通偏好**：在执行新任务前，先写出理解让 Tse 确认，对后再操作，不要直接动手。Tse 问"重复你的理解以免走偏"是常规操作，不是生气，是 Tse 的标准工作流程
- **dashboard 认证方式**：登录用 email + password（默认 `test@example.com` / `changeme123`），登录成功后返回 session token，放在 `Authorization: Bearer *** header 里访问 `/api/keys` 等管理端点。**不是用 gateway token**
- **api_keys 表用 AES-256-GCM 加密存储**：ENCRYPTION_KEY 从容器环境变量读取（`docker exec freellmapi-freellmapi-1 env | grep ENCRYPTION_KEY`）。字段有 `encrypted_key`、`iv`、`auth_tag`，直接写明文 key 无效。**不要直接操作 api_keys 表，通过 dashboard 添加**
- **key 前缀是 `freellmapi-` 不是 `sk-`**：New API 的 OpenAI 兼容渠道（type=1）理论上期望 `sk-` 前缀，但 `freellmapi-` 也能工作
- **SQLite 的 `group` 是保留字**：直接 SQL INSERT 时必须用反引号 `` `group` ``
- **docker-compose.yaml 文件名**：有些版本用 `.yaml` 有些用 `.yml`，不确定时 `ls docker*`
- **IPv6 问题**：Docker 映射绑在 `0.0.0.0`，但从 Mac 用 `localhost` 可能走 IPv6 `::1` 导致绕过后端。用 `http://127.0.0.1:3001` 明确指定
- **Docker Desktop 网络限制**：`host.docker.internal` 在 Docker Desktop for Mac 上经常超时（macOS Linux VM 网络栈问题），不要依赖它。用局域网 IP（如 `192.168.50.98`）或把服务放在同一 Docker 网络
- **Docker Desktop 网络恢复**：如果容器内所有外部 HTTPS 请求都超时/EOF，先尝试 `pkill -9 Docker && open -a Docker`（强制杀死并重启 Docker Desktop）。graceful 重启可能无法恢复网络栈
- **Hermes 12.x 的 `model: provider: custom` 旧格式是坑**：`model: provider: custom` + `base_url/api_key/models` 写在 `model:` 块下的写法会导致 `/model` 命令只显示 `auto`，因为 `get_compatible_custom_providers()` 不读这个结构。必须改用 `providers: freellmapi:` keyed dict 格式。迁移后需重启 gateway
- **Hermes `list_picker_providers()` vs `list_authenticated_providers()` 行为不同**：前者用于 Telegram/Discord 内联键盘，后者用于文本 fallback。两者都需要 `custom_providers` 列表有数据。如果配置格式不匹配，`/model` 就只看到 `auto`

### Hermes 直连 FreeLLMAPI（不走 New API）

当 New API 不需要时，可以直接把 FreeLLM-API 设为 Hermes 的 provider：

```bash
hermes config set providers.freellmapi.base_url http://localhost:3001
hermes config set providers.freellmapi.timeout 120
hermes config set providers.freellmapi.max_tokens 8192
```

然后在 config.yaml 里把 `model.provider` 改成 `freellmapi`。

**⚠️ 从 gateway 内部无法重启 gateway** — `hermes gateway restart` 会被 SIGTERM 拦截。需从外部终端（如另一个 SSH/Mac 终端窗口）执行。

### 接入 New API

```sql
-- 获取下一个 channel id
SELECT MAX(id) FROM channels;

-- 插入渠道（注意 `group` 加反引号）
INSERT INTO channels (
    id, type, key, name, status, created_time, test_time,
    base_url, `group`, models
) VALUES (
    7, 1, 'freellmapi-xxx', 'FreeLLMAPI (local)', 1,
    strftime('%s','now'), strftime('%s','now'),
    'http://127.0.0.1:3001', 'default',
    'auto,agnes-1.5-flash,kimi-k2.6,minimaxai/minimax-m2.7,deepseek-ai/deepseek-v4-flash,gpt-oss-20b,qwen/qwen3.5-122b-a10b'
);
```

models 字段必须包含 FreeLLMAPI 实际支持的模型名（从 `/v1/models` 查询可用模型）。

### 验证

配置写回后用 `head -6` 验证（不要只看 exit code）：

```bash
# 用 New API 的 channel fix 确保 abilities 同步
curl -s http://localhost:3000/api/channel/fix

# 测试路由
curl -s http://localhost:3000/v1/chat/completions \
  -H "Authorization: Bearer <新API_token>" \
  -d '{"model":"auto","messages":[{"role":"user","content":"test"}],"max_tokens":10}'
```

如果报 `无可用渠道（distributor）`：检查 models 字段是否匹配、FreeLLMAPI 是否已配置 provider key。

## Hermes 配置联动

当 New API 中新增了渠道/模型后，Hermes 所在的主机也需要同步更新其 provider 配置。

### 更新 Provider 模型列表

```bash
# 使用 hermes config set，而不是直接编辑 config.yaml
# Hermes 内部 security guard 会拦截对 config.yaml 的直接写入
hermes config set providers.grok-newapi.models '["grok-4.5", "grok-4", "grok-3", "glm-4.5-flash", "deepseek-v3.2"]'
```

### 更新 Provider Base URL

```bash
hermes config set providers.grok-newapi.base_url http://127.0.0.1:3000/v1
```

### 更新 API Key

```bash
hermes config set providers.grok-newapi.api_key '68d4501d...9da5'
```

输出会被截断显示（`68d4...9da5`），但实际已完整写入。

### 完整联动工作流

```
① 探测上游新模型的可用性（playground config / model-status）
② 按用户组批量测试 key 的可用模型
③ New API 创建渠道（Web UI 优先，避免 SQLite 直写）
④ 将新渠道的模型列表更新到 Hermes config provider 的 models 字段
⑤ 测试。通过 Hermes 的 token 调 New API，确保路由成功
```

## 路由诊断完整流程

当渠道存在但报"无可用渠道（distributor）"时，按以下顺序排查：

### 1. 确认 Docker 网络连通性

如果 New API 运行在 Docker 里，渠道的 `base_url` 指向宿主机或其他 Docker 容器，需要确认网络可达：

```bash
# 测试 Docker 容器能否访问外部
docker exec new-api wget -q -O- --timeout=5 https://www.baidu.com 2>&1 | head -3
# 测试 Docker 容器能否访问宿主机
docker exec new-api wget -q -O- --timeout=5 http://host.docker.internal:3001 2>&1 | head -3
# 测试 Docker 容器能否访问局域网 IP
docker exec new-api wget -q -O- --timeout=5 http://192.168.50.98:3001 2>&1 | head -3
```

**关键判断：**
- `host.docker.internal` 在 Docker Desktop for Mac 上可能超时（macOS 的网络栈问题）
- 局域网 IP 如 `192.168.50.98` 在 bridge 网络下可能不可达
- 如果所有测试都超时 → **Docker 容器完全没有外网访问能力**，不是渠道配置问题

**解决 Docker 网络问题：**
- 重启 Docker Desktop（最可靠）
- 检查 Mac 是否有 VPN/代理阻止了 Docker 网络
- 将 New API 和渠道服务放在同一 Docker 网络：`docker network connect freellmapi_default new-api`
- 改用 `--network host` 模式（Docker Desktop for Mac 上可能端口绑定失败）
- 终极方案：在 Mac 上直接运行 New API（非 Docker），消除网络层问题

### 3. 检查 models 表与渠道 models 字段的匹配

**New API 的 distributor 使用精确字符串匹配，大小学/前缀敏感。**

New API 路由流程：收到请求 model 名 → 在 models 表里查找匹配记录 → 从该记录的 channel_ids 里找 enabled 的 channel → 用 channel 的 base_url + key 转发请求。

这意味着 `channels.models` 字段的值必须与 `models.model_name` 完全一致（包括大小写和前缀）才能被路由到。

**实际案例：** Channel 7 的 models 字段写的是 `MiniMax-M2.7`，但 freeLLMAPI 返回的模型名是 `minimaxai/minimax-m2.7`，导致 New API 路由时在 models 表里找不到 `MiniMax-M2.7` 对应的可用 channel（因为 models 表里有的是 `minimaxai/minimax-m2.7`）。解决方法是让 channel 的 models 字段匹配 freeLLMAPI 返回的实际模型名。

验证方法：
```sql
-- 查看实际能路由成功的模型请求（用 minimaxai/minimax-m2.7）
SELECT model_name FROM models WHERE model_name LIKE '%minimax%';

-- 对比 channel 7 的 models 字段
SELECT models FROM channels WHERE id=7;

-- 测试 freeLLMAPI 返回的模型名
curl -s http://192.168.50.98:3001/v1/models \
  -H "Authorization: Bearer freellmapi-xxx" | \
  python3 -c "import sys,json; [print(m['id']) for m in json.load(sys.stdin)['data']]"
```

**解决：** 改 channels.models 字段，或通过 freeLLMAPI 的 `/v1/models` 确认实际模型名后对齐 channel 配置。

### 3. 检查 Docker 内部 DNS 和上游 API 可达性

```bash
# 看 New API 日志中的 upstream model update 错误
docker logs new-api 2>&1 | grep "upstream model update check failed"
```

如果看到 `EOF` 或 `dial tcp` 超时 → 容器无法连接上游 API，渠道会被标记为不可用。

### 4. 检查上游服务返回的具体错误

New API 的日志区分两种错误：
- `无可用渠道（distributor）` → **路由层**问题（模型名不匹配、channel 被跳过）
- `do request failed: Post "xxx": EOF` → **网络层**问题（容器到上游连接超时）
- `upstream error: do request failed` → 上游返回 HTTP 500 或其他错误

### 5. 确认 freeLLMAPI 的 provider key 是否可用

```bash
# 直接测试 freeLLMAPI
curl -s http://192.168.50.98:3001/v1/chat/completions \
  -H "Authorization: Bearer freellmapi-xxx" \
  -H "Content-Type: application/json" \
  -d '{"model":"minimax-m2.7","messages":[{"role":"user","content":"hi"}],"max_tokens":10}'
```

- `Invalid API key` → key 格式问题
- `All models exhausted` → freeLLMAPI 的所有 upstream provider key 都不可用或限流
- `authentication_error` → 认证失败

### 6. 清除缓存

```bash
docker restart new-api
# 或
docker exec new-api sh -c 'curl http://localhost:3000/api/admin/reload'
```

New API 可能缓存了旧的 channel 状态，重启后重新加载。

## 常见错误对照表

| 错误信息 | 层级 | 含义 |
|----------|------|------|
| 无可用渠道（distributor） | 路由 | 模型名在 models 表中找不到，或 channel 被跳过 |
| upstream model update check failed: EOF | 网络 | Docker 容器无法连接上游 API |
| do request failed: Post "xxx": EOF | 网络 | 实际请求时上游连接断开 |
| All models exhausted | 上游 | 上游服务所有 provider key 不可用 |
| Invalid API key | 认证 | key 格式错误或过期 |
| empty stream with no finish_reason | 响应 | 上游返回空响应（可能配额耗尽或 YAML 错误）
| `do request failed: net/http: invalid header field value for Authorization` | 渠道 key 含无效字符 | 多 key blob 中有空行/前后空格/回车符。修复：从 DB 读出 key，strip 每个 key，过滤空行，再 join 写回去。如果仍报错，退化为单 key 模式 |
| `chat 接口返回 502 但 /v1/models 正常` | hetaosu key 的 chat 配额耗尽 | `/v1/models` 200 ≠ chat 可用。见 `references/hetaosu-key-chat-vs-model-test.md` |
| 上游返回 `403: 该ip已被封禁，原因：bulk probe guard: ip X requested N distinct models in 60s` | 上游有批量探测防护，同 IP 在 60 秒内请求了 8+ 种模型触发封禁 | 封禁自动解除（通常数分钟到 1 小时），等待或换出口 IP。避免通过 New API 同时测试多个模型 |

## 模型列表管理

### `/v1/models` 架构

FreeLLMAPI 的 `/v1/models` 端点由 `services/model-listing.js` 的 `buildModelListing()` 生成，**永远返回所有模型**，不自动过滤不可用的。

可用性（`available`）基于：
- `m.enabled = 1`（模型启用）
- `EXISTS (enabled api_key WHERE platform matches AND (key_id matches OR key_id IS NULL))`

模型按 `model_id` 列去重（非 unify 模式），优先保留可用且最优的版本。

### 从列表中移除模型

- **禁用 API key**（`api_keys.enabled=0`）：模型标记为 `available=False` 但仍显示
- **DELETE models 行**：完全消失。catalog 迁移不会恢复已删除的行
  - 先删 `fallback_config` FK 引用，再删 `models` 行
- **Docker 环境 DB 修改**：不能用 `docker cp` 到已停止容器。用临时容器挂载 volume：
  ```bash
  docker run --rm --user root \
    -v freellmapi_freellmapi-data:/data \
    -v /tmp:/tmp:ro \
    ghcr.io/tashfeenahmed/freellmapi:latest \
    sh -c "cp /tmp/freeapi.db /data/ && chown node:node /data/freeapi.db && chmod 644 /data/freeapi.db && rm -f /data/freeapi.db-wal /data/freeapi.db-shm"
  ```

### Catalog 种子生命周期

- `seedModels()`：只在 `models` 表为空时运行（已删除的行不恢复）
- `migrateModels()`：用 `INSERT OR IGNORE` / `UPDATE`，不恢复已删行
- `migrateModelsV2()`：可 DELETE 不存在的模型

详见 `references/freellmapi-model-listing.md`。

### 模型价格未配置 (model_price_error)

最常见的两个原因：

**① SelfUseModeEnabled 未设为 true（双选项陷阱）**

New API 选项表 options 中有两个相似的 self_use 选项：

- `self_use_mode_enabled` — 只控制某些内部行为
- `SelfUseModeEnabled` — 控制是否检查模型价格（真正的开关）

必须同时将二者设为 true。从 Web UI 系统设置里打开后，再检查 API 返回的 option 列表：

```bash
curl -b /tmp/na_cookie.txt -H 'New-Api-User: 1' http://localhost:3000/api/option/
# 检查 output 里 Sel和sel的两个选项
```

CLI 设置：
```bash
curl -s -b /tmp/na_cookie.txt -H 'New-Api-User: 1' http://localhost:3000/api/option/ -X PUT -H 'Content-Type: application/json' -d '{"key":"SelfUseModeEnabled","value":"true"}'
```

**② models 表和 model_pricing 缺失**

渠道存在、abilities 存在，但依然报价格未配置时，检查两个表：

| 表 | 检查 | 修复 |
|----|------|------|
| models | 是否有对应模型的记录（model_name） | 手动插入 |
| options: model_pricing | 是否存在该模型（如 "grok-4.5":0） | 手动设置 |

models 表插入示例：
```sql
INSERT INTO models (model_name, description, vendor_id, status, name_rule, created_time, updated_time)
VALUES ('grok-4.5', 'Grok 4.5', 1, 1, 0, <unix_timestamp>, <unix_timestamp>);
```

model_pricing 设置示例（通过 API）：
```json
PUT /api/option/
Body: {"key":"model_pricing","value":"{\"grok-4.5\":0,\"grok-4\":0,\"grok-3\":0}"}
```

### 完整恢复流程（DB 备份还原后）

当从备份恢复 one-api.db 后，可能同时出现多个问题。恢复步骤：

1. 重置 root 密码（如果密码不匹配）
   ```bash
   pip3 install passlib
   python3 -c 'from passlib.hash import bcrypt; h=bcrypt.hash(\"123456\"); print(h)'
   # 填入 DB 的 users 表
   ```

2. 更新选项

3. 更新 model_pricing 以包含新模型

4. 插入 abilities（如果缺失）
   
5. 插入 models 表记录（如果缺失）

6. 重启容器：`docker rm -f new-api; docker run ...`

7. 通过 API 验证：`curl http://localhost:3000/v1/chat/completions`

## 参考

- `references/freellmapi-429-debugging.md` — NVIDIA NIM 账户级限额导致 429 的实际案例和排查步骤
- `references/freellmapi-0-models-diagnosis.md` — `/model` 显示 0 模型的诊断和修复（unified API key 缺失）
- `references/freellmapi-model-listing.md` — `/v1/models` 列表架构、去重逻辑、模型过滤方法和 catalog 迁移行为详解
