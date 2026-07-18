# Hermes 显示 0 模型诊断法

## 现象

`/model freellmapi` 返回空（0 个模型），但 freellmapi 本身正常运行。

## 根因

freeLLM-API（New API 架构）的 `/v1/models` 端点需要 **统一 API key 鉴权**。Hermes provider 配置缺少 `api_key` 时，请求不带 Authorization header，freeLLM-API 返回 `401 Invalid API key` → Hermes 认为无模型。

## 统一 API key 的获取

freeLLM-API 的统一 API key 存在 SQLite 数据库的 `settings` 表中：

```bash
# 方法 1：从容器 logs 获取
docker logs freellmapi-freellmapi-1 2>&1 | grep "unified API key"

# 方法 2：从数据库直接查
docker cp freellmapi-freellmapi-1:/app/server/data/freeapi.db /tmp/freeapi.db
sqlite3 /tmp/freeapi.db "SELECT value FROM settings WHERE key='unified_api_key';"
```

Key 格式类似：`freellmapi-d2451bbc0aa4b19939d46a2ec86caf8906332220cf650a94`

## 修复

在 Hermes config.yaml 的 `freellmapi` provider 中补上 `api_key`：

```yaml
providers:
  freellmapi:
    base_url: http://localhost:3001
    api_key: freellmapi-<完整key>
    timeout: 120
    max_tokens: 8192
```

修改后需重启 gateway：`hermes gateway restart`

## 验证

```bash
# 直测 freeLLM-API 模型列表
curl -s http://localhost:3001/v1/models \
  -H "Authorization: Bearer freellmapi-<完整key>" | \
  python3 -c "import sys,json; [print(m['id']) for m in json.load(sys.stdin)['data']]"
```

返回 70+ 模型即修复成功。
