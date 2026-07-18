# FreeLLMAPI + New API 集成实战记录

## 背景

FreeLLMAPI (https://github.com/tashfeenahmed/freellmapi) 是一个 OpenAI 兼容的聚合网关，自动聚合 16+ LLM 厂商的免费额度（Gemini, Groq, Cerebras, Mistral, OpenRouter 等），统一一个 `freellmapi-xxx` token 访问所有模型。

## 部署

```bash
cd /Users/macos && git clone https://github.com/tashfeenahmed/freellmapi.git
cd freellmapi
ENCRYPTION_KEY=$(openssl rand -hex 32)
printf "ENCRYPTION_KEY=%s\nPORT=3001\nHOST_BIND=0.0.0.0\n" "$ENCRYPTION_KEY" > .env
docker compose up -d
```

## 首次设置

容器启动后自动生成：
- 默认用户：`test@example.com` / `changeme123`
- Unified API key（从 docker logs 获取）：`freellmapi-xxx`
- 启动日志显示 `Checking 0 keys` = 未配置上游 provider key

## 两种接入方案对比

### 方案 A：通过 New API 路由（复杂，需要改 New API 配置）

需要修改 New API 的 channels 表 + models 表，确保模型名精确匹配。路由链：
```
客户端 → New API (:3000) → freeLLMAPI (:3001) → 上游模型
```

适合场景：多个渠道需要统一管理、负载均衡、统一鉴权。

### 方案 B：Hermes 直连 freeLLMAPI（简单，改 Hermes 配置即可）

只改 Hermes 的 `.hermes/config.yaml`，不动 New API。路由链：
```
Hermes → freeLLMAPI (:3001) → 上游模型
```

**适合场景：火同学这类只需要一个上游（freeLLMAPI）的设备，直接切换最省事。**

修改内容：
```yaml
model:
  default: deepseek-v4-pro        # 改成 freeLLMAPI 支持的模型名
  provider: custom
  base_url: http://192.168.50.98:3001/v1   # 从 :3000 改到 :3001
  api_key: freellmapi-xxx         # 换成 freeLLMAPI 的 unified token
```

**实施步骤（坚果3/DT1902A）：**
1. `adb -s <serial> shell "run-as com.termux cat /data/data/com.termux/files/home/.hermes/config.yaml"` 读取当前配置
2. 本地替换 `base_url`（:3000→:3001）、`api_key`、`default`（模型名改为 freeLLMAPI 支持的）
3. `adb push modified.yaml /sdcard/Download/config_new.yaml`
4. `adb shell "run-as com.termux cp /sdcard/Download/config_new.yaml /data/data/com.termux/files/home/.hermes/config.yaml"`
5. `adb shell "run-as com.termux head -6 /data/data/com.termux/files/home/.hermes/config.yaml"` 验证

## 已知坑

1. **必须配置 provider key**：否则所有模型 `available=false`。需在 dashboard 添加上游 key
2. **通过 dashboard 添加 key，不要直接写数据库**：api_keys 表用 AES-256-GCM 加密存储（ENCRYPTION_KEY 从容器 env 获取）。直接 INSERT 明文 key 无效。正确方式：登录 dashboard → Settings → 添加 key
3. **dashboard 认证流程**：用 email + password 登录 → 获取 session token → 用于后续 `/api/keys` 等管理请求。不是用 gateway token
4. **key 前缀 `freellmapi-` 不是 `sk-`**：New API 的 OpenAI 渠道能接受
5. **SQLite `group` 是保留字**：直接 SQL 插入时加反引号 `` `group` ``
6. **models 字段要写全**：New API 路由依赖 models 字段匹配 models 表的 model_name（大小学/前缀敏感）
7. **IPv6 localhost**：Mac 用 `localhost:3001` 可能走 `::1` 绕过后端，用 `127.0.0.1:3001`
8. **容器内无 curl**：用 `docker exec ... node -e "..."` 或 `docker exec ... python3 -c "..."` 测试
9. **默认模型名必须匹配**：Hermes 的 `model.default` 必须是 freeLLMAPI 支持的模型名（如 `deepseek-v4-pro`），不能用 freeLLMAPI 没有的模型（如 `agnes-1.5-flash`）

## Dashboard 认证

```python
# 登录获取 session token
import requests
r = requests.post('http://192.168.50.98:3001/api/auth/login', json={
    'email': 'test@example.com',
    'password': 'changeme123'
})
session_token = r.json()['token']

# 用 session token 访问管理 API
requests.get('http://192.168.50.98:3001/api/keys',
    headers={'Authorization': f'Bearer {session_token}'})
```

## 接入 New API

渠道 ID 从 `SELECT MAX(id) FROM channels` 获取。插入后从 New API dashboard 或 `POST /api/channel/fix` 同步 abilities。

验证：`curl -s http://localhost:3000/v1/chat/completions -H "Authorization: Bearer *** -d '{"model":"auto",...}'`

报错 `无可用渠道（distributor）` → 检查 models 匹配 + provider key 配置