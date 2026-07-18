# New API 完整恢复流程（DB 备份还原 + 40 Key 批量配置）— 2026-07-18

## 背景
New API Docker 容器因 `https_proxy` 环境变量导致无法连接 hetaosu 上游。整个过程：重建容器 → 恢复 DB → 配置 40 key → 修复渠道路由。

## 症状
```json
{"error":{"code":"model_not_found","message":"No available channel for model grok-4.5 under group default (distributor)"}}
```
→ abilities 缺失

修复后：
```json
{"error":{"code":"model_price_error","message":"模型 grok-4.5 的价格未配置"}}
```
→ SelfUseModeEnabled + model_pricing + models 表缺失

## 三阶段恢复

### 阶段 1：容器与 DB 基础
- 新旧 DB 都正确的情况下仍报错 → 逐步排查
- 去掉 `https_proxy` 环境变量（不要加），容器裸连 hetaosu 即可
- 使用 `calciumion/new-api:latest` 镜像，挂载 DB 到 `/data/one-api.db`

### 阶段 2：渠道路由
- channels 表存在 ≠ 路由通
- abilities 表必须同步填充（每个 model + group 一行）
- models 表必须包含对应模型记录

### 阶段 3：定价与自用模式
- 必须同时设 `self_use_mode_enabled=true` 和 `SelfUseModeEnabled=true`
- model_pricing 必须包含所有用到的模型

## 关键命令

### 密码重置
```bash
pip3 install passlib
python3 -c 'from passlib.hash import bcrypt; import sqlite3
h = bcrypt.hash("123456")
conn = sqlite3.connect("/tmp/na-current.db")
conn.execute("UPDATE users SET password=? WHERE id=1", (h,))
conn.commit()
conn.close()'
```

### 查看所有 option（含隐藏项）
```bash
curl -b /tmp/na_cookie.txt -H 'New-Api-User: 1' http://127.0.0.1:3000/api/option/
```

### 查看渠道详情
```bash
curl -b /tmp/na_cookie.txt -H 'New-Api-User: 1' http://127.0.0.1:3000/api/channel/?id=1
```

### 批量测试 40 hetaosu 密钥
```bash
for key in 'sk-...' 'sk-...'; do
  http_code=$(curl -s -o /dev/null -w "%{http_code}" -m10 https://gy.hetaosu.xyz/v1/models -H "Authorization: Bearer $key")
  echo "$http_code $key"
done
```

## 批量更新渠道密钥
```sql
-- 构建 40 key 的 blob（换行分隔）
UPDATE channels SET key='<key1>
<key2>...
<key40>' WHERE id=1;
```
然后重启容器。

## 注意事项
- `POST /api/channel/fix` 修复 abilities（但不会修 models 表）
- 容器重启后 session cookie 会过期，需要重新 login
- `New-Api-User: 1` header 在每次管理 API 调用时都必须传
- Docker 容器的 `--log-dir` 和 `--log-stdout` 参数在这个版本的 New API 中不支持

## 最终拦路虎：Authorization header 无效值

在解决了上述所有问题后，最终遇到：
```
do request failed: Post "https://gy.hetaosu.xyz/v1/chat/completions": net/http: invalid header field value for "Authorization"
```

这表示渠道的 key 字段包含 Go net/http 不接受的字符（如空行、前后空格、回车符）。**修复：** 从 DB 读出 key，split 后 strip 每个 key，过滤空行，再 join 写回。同时检查 `hex(key)` 确认没有 0a0a（连续空行）或 20（空格）前缀。
