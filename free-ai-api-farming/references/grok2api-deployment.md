# grok2api Docker 部署参考

## 快速部署（macOS Docker）

```bash
git clone https://github.com/chenyme/grok2api.git
cd grok2api

# 生成安全密钥
JWT_SECRET=$(openssl rand -hex 32)
ENC_KEY=$(openssl rand -base64 32)
ADMIN_PWD=$(openssl rand -hex 8)
```

## config.yaml 最小配置

```yaml
server:
  listen: "0.0.0.0:8000"
  maxBodyBytes: 33554432
  readTimeout: 15m
  requestTimeout: 2h
  swaggerEnabled: true

auth:
  accessTokenTTL: 15m
  refreshTokenTTL: 720h
  secureCookies: false

secrets:
  jwtSecret: "<openssl rand -hex 32>"       # 至少32字符
  credentialEncryptionKey: "<openssl rand -base64 32>"  # 写入后不可换

bootstrapAdmin:
  username: "admin"
  password: "<随机强密码>"     # 首次登录后建议删除本段

frontend:
  staticPath: "./frontend/dist"

database:
  driver: sqlite
  sqlite:
    path: "./data/backend.db"

runtimeStore:
  driver: memory

media:
  driver: local
  local:
    path: "./data/media"
```

## 启动

```bash
docker compose up -d
# 访问 http://localhost:8000
# 用 bootstrapAdmin 凭证登录管理后台
```

## 首次配置

1. 登录管理后台
2. "上游账号" → 接入 Grok Build/Web/Console 账号
3. 等待额度同步完成
4. "客户端密钥" → 创建 `g2a_xxx` API Key
5. 用该密钥调用 `/v1/*` 接口

## 验证

```bash
curl http://localhost:8000/v1/models \
  -H "Authorization: Bearer g2a_xxx_xxx"
```

## 注意事项

- 管理后台首次创建管理员后，建议从 config.yaml 删除 `bootstrapAdmin` 段
- `credentialEncryptionKey` 必须长期保留，更换后已有账号凭据无法解密
- 默认 SQLite 适合单机测试；生产多实例需换 PostgreSQL + Redis
- Docker 部署后注意 8000 端口安全策略
