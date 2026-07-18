# 多容器 Hermes Agent 系统性巡检清单

Systematic checklist for inspecting Docker-based Hermes agents (金、木、火、水等) when adding them to a shared memory pool or diagnosing config drift.

基于 2026-06-20 对金/木两容器的全面巡检。

## 核心检查项

### 1. 容器基本信息

```bash
docker inspect <container> --format \
  '{{.State.Status}} {{.State.StartedAt}} {{.HostConfig.Memory}} {{.HostConfig.CpuShares}}'
```

- 预期: `running <timestamp> 0 0`（0 = 无限制）
- 注意: `Memory: 0` 表示无上限（默认），如果有具体数值则检查是否充足

### 2. 挂载点类型

```bash
docker inspect <container> --format \
  '{{range .Mounts}}{{.Type}} {{.Source}} -> {{.Destination}}{{"\n"}}{{end}}'
```

- `volume` → 匿名 Docker volume，数据不可从宿主机直接访问
- `bind` → 挂载到宿主机目录，数据可直读

**风险**：`volume` 类型的配置在移容器后不可达，需 `docker cp` 备份。

### 3. config_version 漂移

```bash
docker exec <container> grep '_config_version' /opt/data/config.yaml
```

各 agent 之间（包括本地土同学）的版本应当一致或接近。版本差 > 2 可能意味着：

- **容器落后于主机**（常见）：缺少新配置字段，部分功能无法使用，升级流程不完整
- **容器领先于主机**（也有，如新拉镜像的容器可能比本地 Hermes 更新）：容器配置文件可能有主机尚不认识的字段，但一般不造成功能问题——新配置只是静默忽略

无论哪个方向，版本漂移就是升级不一致的信号。正常状态是**所有 agent（含主机）的版本号相同**。

### 4. memory.provider 有效性

```bash
docker exec <container> grep -A5 "^memory:" /opt/data/config.yaml | grep provider
```

- 正确: `provider: hindsight`
- 陷阱: `provider: ''`（空 = 未启用）
- 注意: **不能只看 `.env` 里有没有 HINDSIGHT_API_KEY**，`memory.provider` 也必须设为 `hindsight`

### 5. delegation.provider 未污染 🔴

```bash
docker exec <container> grep -A3 "^delegation:" /opt/data/config.yaml | head -5
```

- 正确: `provider:` 为空（`provider:` 后什么也没有，或者 `provider: ''`）
- 陷阱: `provider: hindsight` — 这是 `sed` 替换 `memory.provider` 时误伤 `delegation.provider` 导致的

**修复**：
```bash
sed -i "/^delegation:/,/^[a-z]/ s/provider: hindsight/provider: /" /opt/data/config.yaml
```

### 6. HINDSIGHT_API_KEY 完整性

terminal 工具会静默替换 `hsk_*` 格式为字面量 `***`，导致 key 丢失。

```bash
docker exec <container> python3 -c "
with open('/opt/data/.env') as f:
    for line in f:
        if line.startswith('HINDSIGHT_API_KEY'):
            val = line.split('=',1)[1].strip()
            print(f'长度: {len(val)}, 前10: {val[:10]}, 后4: {val[-4:]}')
            print(f'是否***占位: {val == chr(42)*3}')
"
```

- 正常: `长度: 53, 前10: hsk_75b438, 是否***占位: False`
- 异常: `长度: 3, 前10: ***, 是否***占位: True`

修复参考 `cloud-full-export-recovery.md` 中的 base64 传递法。

### 7. HINDSIGHT_API_URL 正确性

```bash
# 检查 env 中的 URL
docker exec <container> grep HINDSIGHT_API_URL /opt/data/.env

# 连通测试
docker exec <container> sh -c "
curl -s -o /dev/null -w '%{http_code}' \
  -H 'X-API-Key: $(grep HINDSIGHT_API_KEY /opt/data/.env | cut -d= -f2)' \
  http://host.docker.internal:8888/health
"
```

预期: `200`

URL 规则：
| 容器位置 | 值 |
|---------|-----|
| 宿主机 | `http://localhost:8888` |
| Docker 容器 | `http://host.docker.internal:8888` |

### 8. APIs/Service Keys 检查

```bash
docker exec <container> python3 -c "
with open('/opt/data/.env', errors='replace') as f:
    for line in f:
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        print(repr(line))
"
```

检查 key 是否被意外包裹了引号（在 `.env` 中用 `echo 'KEY="value"'` 写入时可能带到文件里）：

- `XUNFEI_API_KEY="abcdef..."` → `python-dotenv` 会自动剥离双引号 ✅
- `OPENCODE_ZEN_API_KEY='******'` → 自动剥离单引号 ✅
- 实际上不影响使用，`python-dotenv` 会正确处理标准引用格式

### 9. 磁盘使用

```bash
docker exec <container> du -sh /opt/data/logs/
```

异常信号：
- 日志 > 100MB：日志可能未轮转
- 无可用磁盘：容器可能写满

### 10. Telegram 多容器冲突检查

当多个容器同时运行时，确认它们使用不同的 Telegram Bot Token，否则只有第一个连上的容器能正常工作。

```bash
TOKEN_A=$(docker exec <container_A> grep TELEGRAM_BOT_TOKEN /opt/data/.env | cut -d= -f2 | cut -c1-20)
TOKEN_B=$(docker exec <container_B> grep TELEGRAM_BOT_TOKEN /opt/data/.env | cut -d= -f2 | cut -c1-20)
echo "Token 相同: $([ "$TOKEN_A" = "$TOKEN_B" ] && echo 'YES - 冲突!' || echo 'NO - 安全')"
```

正常: 不同 token → 各容器独立收发消息，互不干扰。

### 11. Gateway state "draining" 非问题假设

```bash
docker exec <container> cat /opt/data/gateway_state.json | python3 -c "
import json,sys; s=json.load(sys.stdin)
print(f'state记载PID: {s[\"pid\"]}')
print(f'gateway_state: {s[\"gateway_state\"]}')
print(f'Telegram: {s[\"platforms\"][\"telegram\"][\"state\"]}')
"
```

如果 `gateway_state: "draining"` 但 Telegram 显示 `connected`，且容器内有正常的 gateway 进程在运行——**这是无害的过时状态**，不需处理。

**原因**：`hermes gateway run --replace` 启动新 gateway 时，旧的 gateway 进程在退出前写入 `draining` 状态。state 文件记录的是**旧进程的最终状态**，而实际服务已由新进程接管。容器重启后会自动刷新。

**诊断**：对比 state 文件中的 PID 与 `ps aux | grep "hermes gateway"` 的实际 PID。如果不同，说明 state 文件来自旧进程。

**不需要修复**——不影响功能，只在容器重启后自动清理。

### 12. 完整的 hindsight SDK 连通测试

```bash
docker exec <container> python3 -c "
import os
from dotenv import load_dotenv
load_dotenv('/opt/data/.env')
from hindsight_client import Hindsight
h = Hindsight(api_key=os.environ['HINDSIGHT_API_KEY'],
              base_url=os.environ['HINDSIGHT_API_URL'])
r = h.recall(bank_id='hermes', query='共享记忆测试', budget='low')
print(f'召回: {len(r.results)} 条')
for rr in r.results[:3]:
    print(f'  [{rr.type}] {rr.text[:60]}')
"
```

预期输出至少几条命中结果。

## 完整巡检命令（一行执行）

```bash
echo "=== 状态 ===" && \
docker exec <container> sh -c 'echo "$(docker inspect $(hostname) --format "{{.State.Status}}") started: $(docker inspect $(hostname) --format "{{.State.StartedAt}}")"' && \
echo "=== config_version ===" && \
docker exec <container> grep '_config_version' /opt/data/config.yaml && \
echo "=== memory.provider ===" && \
docker exec <container> grep -A5 "^memory:" /opt/data/config.yaml | grep provider && \
echo "=== delegation.provider ===" && \
docker exec <container> grep -A3 "^delegation:" /opt/data/config.yaml | head -3 && \
echo "=== HINDSIGHT_API_KEY (integrity) ===" && \
docker exec <container> python3 -c "
with open('/opt/data/.env') as f:
    for line in f:
        if line.startswith('HINDSIGHT_API_KEY'):
            val = line.split('=',1)[1].strip()
            print(f'len={len(val)}, placeholder={val==chr(42)*3}')
" && \
echo "=== HINDSIGHT_API_URL ===" && \
docker exec <container> grep HINDSIGHT_API_URL /opt/data/.env && \
echo "=== connectivity ===" && \
docker exec <container> sh -c '
KEY=$(grep HINDSIGHT_API_KEY /opt/data/.env | cut -d= -f2)
URL=$(grep HINDSIGHT_API_URL /opt/data/.env | grep -v "^#" | cut -d= -f2)
curl -s -o /dev/null -w "%{http_code}" -H "X-API-Key: $KEY" "$URL/health"
' && echo "" && \
echo "=== disk ===" && \
docker exec <container> du -sh /opt/data/logs/
```

## 何时做巡检

- **新增 agent 到共享池前** — 必须在连线前确认配置完整
- **config 迁移/升级后** — 验证无残留旧配置
- **记忆共享失效时** — 排查各 agent 的 memory.provider 是否全部设为 `hindsight`
- **用户怀疑"它的记忆和我不同"时** — 对比各 agent 的 bank_id、URL、API Key
