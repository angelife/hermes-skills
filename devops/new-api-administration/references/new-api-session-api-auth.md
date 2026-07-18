# New API Session-Based API Auth for Management Calls

> 当 Web UI 不可用或需要脚本化管理时，通过 session cookie + `New-Api-User` header 调用 New API 管理接口。

## Authentication Flow

New API 的管理 API（`/api/user/`, `/api/token/`, `/api/channel/` 等）**不使用** 推理用的 API key（`sk-*`），而使用 **session cookie 认证**。

### 1. Login — 获取 session cookie

```bash
# Login and save cookie
curl -s -c /tmp/newapi_cookies.txt \
  -X POST http://127.0.0.1:3000/api/user/login \
  -H "Content-Type: application/json" \
  -d '{"username":"root","password":"123456"}'
```

默认 admin 凭据：`root` / `123456`（首次启动时设置）。

### 2. 关键 Header

**所有管理 API 调用都需要 `New-Api-User` header**，值为用户 ID（admin 为 `1`）：

```bash
curl -s -b /tmp/newapi_cookies.txt \
  -H "New-Api-User: 1" \
  -G "http://127.0.0.1:3000/api/token/" \
  --data-urlencode "page_size=50"
```

不传此 header 会返回 `401 Unauthorized`。

### 3. Session 短生命周期

New API session **可能只有几秒到几分钟有效**。多次调用之间 session 会过期：

```bash
# ❌ 分开两步会失效（session cookie 在第一步后过期）
curl -c /tmp/na_cookie.txt -X POST ...login...     # OK
curl -b /tmp/na_cookie.txt ...channel update...     # 401 — cookie expired

# ✅ 解决：同一 curl 进程或 Python 的 CookieJar 维持 session
# 或用 cookie 字符串传值：
SESSION=$(curl -s -c - -X POST ...login... | grep session | awk '{print $NF}')
curl -s -H "Cookie: session=$SESSION" ...channel...
```

**最佳实践：在同一条 pipeline 里完成 login + 操作 + 读取结果。**

## Common Operations (via API)

### Create Token

```bash
# Login → create token → read key from DB
SESSION=$(curl -s -c - -X POST http://127.0.0.1:3000/api/user/login \
  -H "Content-Type: application/json" \
  -d '{"username":"root","password":"123456"}' | grep session | awk '{print $NF}')

curl -s -H "Cookie: session=$SESSION" \
  -H "New-Api-User: 1" \
  -H "Content-Type: application/json" \
  -X POST http://127.0.0.1:3000/api/token/ \
  -d '{"name":"my-token","unlimited_quota":true,"group":"default"}'
```

**⚠️ Token key 不会被 API 返回** — 创建响应只有 `{"message":"","success":true}`。  
必须从 DB 读取：

```bash
docker cp <container>:/data/one-api.db /tmp/one-api.db && \
sqlite3 /tmp/one-api.db "SELECT id, name, key FROM tokens WHERE name='my-token'"
```

### List Tokens

```bash
curl -s -b /tmp/na_cookie.txt \
  -H "New-Api-User: 1" \
  "http://127.0.0.1:3000/api/token/?page_size=50"
```

Tokens 的 `key` 字段在 API 响应中会被**截断为 `sk-6******2251`** 格式，完整 key 只有 DB 里有。

### Create / Update Channel

```python
import urllib.request, json, http.cookiejar

BASE = "http://127.0.0.1:3000"
cj = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))

def api(method, path, data=None):
    hdrs = {"Content-Type": "application/json", "New-Api-User": "1"}
    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(f"{BASE}{path}", data=body, headers=hdrs, method=method)
    with opener.open(req, timeout=10) as r:
        return json.loads(r.read())

# Login (CookieJar persists session automatically)
api("POST", "/api/user/login", {"username":"root","password":"123456"})

# Get channel list
channels = api("GET", "/api/channel/")

# Update channel models
api("PUT", "/api/channel/", {"id": 1, "models": "grok,grok-4.5,grok-4", "name": "...", ...})
```

`GET /api/channel/` 不需要 id 参数？使用 `GET /api/channel/?id=1` 或 `GET /api/channel/` 获取全列表。  
`PUT /api/channel/` 的 body 必须包含完整 channel 对象（id, name, type, models, ...）。

### Get Specific Channel Detail

```bash
curl -s -b /tmp/na_cookie.txt \
  -H "New-Api-User: 1" \
  "http://127.0.0.1:3000/api/channel/?id=1"
```

### Fix Abilities (After Direct DB Write)

```bash
curl -s -X POST -b /tmp/na_cookie.txt \
  -H "New-Api-User: 1" \
  http://127.0.0.1:3000/api/channel/fix
```

## Token Key Format

New API 生成的 token key 为 51 字符：`sk-` + 48 hex chars。  
示例：`sk-4EpnI5Rgx8tV0VQg5F7S3cvkWeQA9fJrRudOtfT2dBCuAyHq`

## Pitfalls

- **Session expires fast** — 不要跨多次 curl 调用共享 cookie 文件。用 Python CookieJar 或单次 pipeline。
- **`New-Api-User` header 必须传** — 不传返回 401。
- **Token key 不会在创建时返回** — 只能从 DB 读取。创建前先用 `docker cp` 准备读取。
- **渠道 models 字段需要与 abilities 同步** — 仅 DB 写 channels 表不够，还需 `POST /api/channel/fix` 或重启容器。
- **上游 key 过期 vs 渠道配置问题** — 区分方法：
  - `无可用渠道（distributor）` → 路由层问题（模型名不匹配、abilities 缺失）
  - `Invalid token` → 上游 key 问题，与 New API 配置无关
  - 测：`curl -x socks5h://127.0.0.1:10808 https://upstream/v1/models -H "Authorization: Bearer $KEY"`
