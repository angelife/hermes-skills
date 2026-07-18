# hetaosu 多 Key 渠道导入记录

## 背景

河涛 Grok 公益免费中转站 (`gy.hetaosu.xyz`) 提供无限量 Grok API，上游需补充 x.ai 账号。用户有 20+ 个 hetaosu 密钥（`sk-*` 格式），最终目标扩至 100+。

## 导入方式

API 创建渠道返回 **500**（密钥列表过长），改为 SQLite 直写：

```python
# 秘钥存入 ~/.hermes/secrets/hetaosu-keys-full.txt（chmod 600）
keys_blob = "\n".join(all_sk_values)  # 20 keys, ~2KB
```

DB 写入 `channels` 表 + `abilities` 表 + `POST /api/channel/fix` 完成。

## 关键参数

| 参数 | 值 |
|------|------|
| name | 河涛Grok-hetaosu |
| type | 1 (OpenAI) |
| base_url | https://gy.hetaosu.xyz/v1 |
| models | grok-4.5,grok-4,grok-3,grok-3-mini |
| group | default |
| weight | 100 |
| priority | 100 |
| auto_ban | 1 |
| test_model | grok-4.5 |

## 连通性问题

### 现象

| 测试路径 | 结果 | 说明 |
|---------|------|------|
| 宿主机直连 `gy.hetaosu.xyz` | HTTP 403 Cloudflare 1010 | 被 WAF 拦截 |
| 宿主机走 socks5h://127.0.0.1:10808 | HTTP 403 Cloudflare 1010 | 代理不突破 Cloudflare |
| 宿主机走 http://127.0.0.1:10809 | HTTP 403 Cloudflare 1010 | 同样被拦 |
| NewAPI Docker 容器内直连 | `do request failed` | 容器 bridge 无代理 |

**关键判断：** Cloudflare 1010 在**本机直连和走代理时都出现**，说明不是代理缺失问题，而是 `gy.hetaosu.xyz` 本身的上游条件决定是否放行。中转站的前端有 Cloudflare WAF 保护，只有特定 IP/UA/指纹组合才能通过。

### 根本原因

`gy.hetaosu.xyz` 是一个 Grok API 公益免费中转站，其上游需要 x.ai 账号池来转发请求。当上游账号全部离线/超额时，中转站返回 1010（即使 API key 有效）。这不是本机或 Docker 的网络问题——试了代理、试了直连、试了不同 curl UA，全部被 Cloudflare 1010 拦截。

### 排查优先级（下次遇到类似问题）

1. **先用宿主机 curl 直测**（不通过 Docker）——排除容器网络层
2. **再走代理测**——排除是否需要代理才能到上游
3. **如果直连和代理都被 Cloudflare/1010 拦住**——说明是上游服务本身的限制，不是本机网络问题
4. **检查上游本身是否有可用通道**——免费中转站经常上游通道不存在/超额
5. **只有 Docker 容器不通但宿主机通**——才配 Docker proxy 或 `--network host`
6. **Docker Desktop for Mac 的 `host.docker.internal` 不可靠**——macOS Linux VM 网络栈不稳定，不要依赖它。改用 `--add-host host.docker.internal:host-gateway` 或局域网 IP

## 多 Key 池优势

- 单 channel 管理，不需要每个 key 建一个 channel
- `auto_ban=1` 自动跳过失效 key
- 20+ keys 轮转，减轻单个 key 的速率限制
- 加 key 只需追加到 key blob 里（改 DB 或 API update）

## 全量 Key 验证协议（前置步骤）

**不要只抽测一个 key 就认为整批都能用。** 同批次 key 可能有部分失效（超时、quota 耗尽、被上游回收）。

### 协议

1. 对所有新 key **逐个独立测试**，不是抽检
2. 测试 endpoint：`GET /v1/models`（HTTP 200 = 可用）
3. 只把通过的 key 加入池；失败的单独列出交给用户
4. 并发测试（10 keys 约 30s）不要串行

### 批量测试脚本

```python
import subprocess, re
from pathlib import Path

keys_file = Path("~/.hermes/secrets/hetaosu-keys-full.txt")
keys = []
for line in keys_file.read_text().strip().split("\n"):
    parts = line.strip().split(None, 1)
    if len(parts) == 2:
        keys.append((parts[0], parts[1]))  # (name, sk-value)

results = {}
for name, key in keys:
    r = subprocess.run(
        ["curl", "-sS", "-m", "20", "-w", "__HTTP__:%{http_code}",
         "-x", "socks5h://127.0.0.1:10808",
         "https://gy.hetaosu.xyz/v1/models",
         "-H", f"Authorization: Bearer {key}"],
        capture_output=True, text=True, timeout=30
    )
    http_code = "?"
    m = re.search(r'__HTTP__:(\d+)', r.stdout)
    if m: http_code = m.group(1)
    results[name] = http_code == "200"

good = [n for n,ok in results.items() if ok]
bad = [n for n,ok in results.items() if not ok]
print(f"能用: {len(good)}/{len(keys)}, 失效: {len(bad)}: {', '.join(bad)}")
```

### 典型结果会分化

实测 10 key 批次结果（2026-07-17）：
- ✅ 6/10：HTTP 200，通过
- ❌ 4/10：exit 28 timeout（curl 20s 无响应），上游已不认

**40 key 全量测试（2026-07-18）：** 全部 HTTP 200，40/40 可用。这是首次全量通过——之前批次分化是因为上游短暂不可用而非 key 本身失效。

**根因：** 部分 key 配额耗尽或被上游回收，同批非同时激活。

### 常见失效模式

| 现象 | HTTP | 含义 |
|------|------|------|
| 正常返回模型列表 | 200 | ✅ 可用 |
| 超时无响应 | 000 (exit 28) | key 已不活跃或 quota 耗尽 |
| Invalid token | 401 | key 格式/拼写错误 |
| Cloudflare 1010 | 403 | 上游 WAF 拦截，非 key 层问题 |

## 批量替换密钥（旧批次全换新批次）

当上游给了新的 key 批次（旧批次失效/被锁），不要追加，**整个替换**：

```bash
# Step 0: 全量验证，只留通过的 key（见上一节）
# Step 1: 测试一个新 key 确认上游可用
curl -x socks5h://127.0.0.1:10808 -sS -m 20 -w '\nHTTP:%{http_code}' \
  https://gy.hetaosu.xyz/v1/models \
  -H "Authorization: Bearer sk-xxxxx"
# → HTTP:200 即可继续

# Step 2: 更新 secrets 文件（只写通过验证的 key）
write_file ~/.hermes/secrets/hetaosu-keys-full.txt

# Step 3: 更新 NewAPI DB
python3 -c "
import sqlite3
db = '/Users/macos/new-api-data/one-api.db'
con = sqlite3.connect(db)
con.execute('UPDATE channels SET key=? WHERE id=?', (\n'.join(good_keys), channel_id))
con.commit()
"

# Step 4: 如果有 abilities 丢失
# con.execute('INSERT INTO abilities (channel_id, model, enabled, priority) VALUES (?, ?, 1, 0)', (cid, 'grok-4.5'))

# Step 5: 重启
docker restart new-api
```

注意事项：
- 渠道 ID 可能变化（DB 被重建后 id 从 1 重算），先 `SELECT id, name FROM channels` 确定
- `abilities` 表可能在 DB 重建后丢失，需要从 abilities 表查 `SELECT * FROM abilities WHERE channel_id=?`，没有就重新 INSERT
- 替换后必须 `docker restart new-api` 让缓存刷新
- secrets 文件同步更新：写入 `~/.hermes/secrets/hetaosu-keys-full.txt`
- **用完删临时脚本**：`.tmp_*.py` 脚本在 `~/angelife.github.com/` 和 `/tmp/` 下，改完即删

## 密钥安全

- 完整密钥存 `~/.hermes/secrets/hetaosu-keys-full.txt`（chmod 600）
- 掩码预览存 `~/.hermes/secrets/hetaosu-keys.tsv`
