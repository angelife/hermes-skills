---
name: android-local-hindsight
description: >
  把任意 Android chroot/容器中的 Hermes 实例切到你们这台 Mac 上的本地 hindsight 共享记忆。
  适用对象：Mi8/Mi6 本地 chroot Hermes、Docker 中的 Hermes bot。
  不要每次配都重新打字；触发词：hindsight、改成本地共享记忆、接共享记忆、local_external、8888。
---

# Android / 远程 Hermes → 本地 Hindsight

## 用户偏好（中文环境必读）
- 用户明确反感反复确认、罗列选项、绕远路和情绪化输出；这类反馈已在会话中多次出现。
- **执行规则**：方案确定后直接干，不再问“是否可以/要不要/要不要重启”。
- **输出规则**：只说结果、日志关键字和下一步，不写感叹号堆叠。
- **技能职责**：存储“如何做”的固定套路，而不是每次把用户偏好复述给用户。
- **必做顺序**：provider/网络/配置修复必须先在本地 Mac 上完成真实验证，再把通过测试的配置原样复制到 Android/容器 Hermes。不允许先把未经验证的配置推上去，再回来补测。

## 前提
- Mac 本地 Docker hindsight **已在跑**，且 `http://localhost:8888/health` 返回 `{"status":"healthy"}`
- 远程 Hermes 目录已存在，写命令能进器设备/容器
- 远程机器能访问 Mac 局域网 IP `192.168.1.8:8888`（同局域网直通）

## 固定指针（你环境里是锁死的）
- Mac hindsight 容器名：`hindsight`
- Mac 局域网 IP：`192.168.1.8`
- Hindsight port：`8888`
- bank_id：`hermes`
- Mac `.env` 里的 `HINDSIGHT_API_KEY`：用宿主机 `~/.hermes/.env` 中那同一个即可

## 快速配置脚本
在 Android chroot 执行：
```bash
# 1. 写 .env
cat > /root/.hermes/.env << EOF
HINDSIGHT_API_KEY=<与Mac相同的hindsight key>
HINDSIGHT_BANK_ID=hermes
HINDSIGHT_BUDGET=mid
HINDSIGHT_API_URL=http://192.168.1.8:8888
HINDSIGHT_MODE=local_external
EOF

# 2. 写 hindsight config.json
mkdir -p /root/.hermes/hindsight
cat > /root/.hermes/hindsight/config.json << EOF
{
  "mode": "local_external",
  "bank_id": "hermes",
  "recall_budget": "mid",
  "auto_recall": true,
  "auto_retain": true,
  "recall_types": "observation",
  "bank_id_template": "",
  "recall_tags": [],
  "retain_tags": [],
  "retain_every_n_turns": 1
}
EOF

# 3. 确保 config.yaml memory.provider=hindsight
```

config.yaml 里必须有：
```yaml
memory:
  provider: hindsight
```

## Android chroot 的启动方式（关键）
在 chroot 里直接调 `hermes` 经常找不到命令，标准启动必须带：
```bash
export HERMES_HOME=/root/.hermes
export PYTHONPATH=/root/.hermes/hermes-agent
export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/root/.hermes/hermes-agent/venv/bin
```
否则会报 `hermes: inaccessible or not found` 或 imported plugins 缺失。

## Telegram 代理必配（Android chroot 默认不通 Telegram）
Android chroot Hermes 默认**无法直连** `api.telegram.org`，必须在 `.env` 和启动环境里同时写：
```bash
HTTPS_PROXY=http://192.168.1.8:10808
HTTP_PROXY=http://192.168.1.8:10808
NO_PROXY=127.0.0.1,localhost,192.168.1.0/24
TELEGRAM_BOT_TOKEN=8858037161:...
TELEGRAM_ALLOWED_USERS=8858037161
```
config.yaml 里也要开：
```yaml
gateway:
  telegram:
    enabled: true
    bot_token: "8858037161:..."
    allowed_users: []
    dm_policy: open
    group_policy: open
```
Mac 侧需先在 `192.168.1.8:10808` 开代理；用前先 `curl -x http://192.168.1.8:10808 https://api.telegram.org` 验证。

## 写入 + 重启顺序
1. 先 `.env` + `hindsight/config.json`
2. 再改 `config.yaml` 的 `memory.provider` 和 `gateway.telegram`
3. **必须**重启 gateway，否则老进程继续用旧配置
4. chroot 里 `hermes gateway run` 会自己续锁；被拒时用 `--replace` 或直接 kill PID

## chroot 内文件写不进去时的救急方案（base64 round-trip）
当 `cp`/`sed`/`cat > file` 在 chroot 内被引号、权限或路径吞掉时，按这个步骤写入：
```bash
# 1) 本机生成完整目标文件，再 base64 编码写入临时文件
base64 /path/to/local/.env > /tmp/mi8_env_b64.txt

# 2) push base64 到 chroot 外可见路径
adb push /tmp/mi8_env_b64.txt /data/local/tmp/mi8_env_b64.txt

# 3) 在 chroot 内用 Python 解码到目标路径
adb shell "su 0 -c 'cp /data/local/tmp/mi8_env_b64.txt /data/local/tmp/chroot/debian/tmp/mi8_env_b64.txt'"
adb shell "su 0 -c 'chroot /data/local/tmp/chroot/debian /usr/bin/python3 -c \"import base64; from pathlib import Path; Path(\"/root/.hermes/.env\").write_bytes(base64.b64decode(Path(\"/tmp/mi8_env_b64.txt\").read_text()))\"'"
```
这样可绕过 shell 引号和 `sed` 权限问题，从 chroot **外部**间接写入内部文件。

## 修正 hindsight config 的坑
如果 `hindsight/config.json` 不是合法 JSON，memory 会静默失效。
**必做**：写完后做一次本地语法校验或直接由 Python `json.loads()` 通过，不要手工写 YAML 风格进去。

## Hermes Telegram + NO_PROXY 陷阱
Hermes Telegram adapter 会读取环境里的 `NO_PROXY` / `no_proxy`。如果 `.env` 或启动 env 里包含：
```
NO_PROXY=api.telegram.org,149.154.166.110,149.154.167.220
```
即使 `HTTPS_PROXY` 存在，Hermes 也会对 Telegram 走直连；在 Android chroot 默认网络不通 Telegram，结果就是 `httpx.ConnectError`。  
**正确写法**：`NO_PROXY` 只保留局域网，不要包含 Telegram IP/域名。
```bash
NO_PROXY=127.0.0.1,localhost,192.168.1.0/24
```

**新坑：`.env` 会反写启动脚本里的 NO_PROXY**  
若启动脚本里已经设好保守 `NO_PROXY`，但 Hermes 启动时 source/sequence `.env`，`.env` 里的旧 `NO_PROXY` 会覆盖脚本里的值。  
修复：改完 `.env` 后必须 tail 确认 `.env` 里没有 Telegram 相关 NO_PROXY；若有，删掉或改回仅局域网。

## 敏感值脱敏与校验
终端/日志输出层对 `bot_token`、API key、token 类值做自动脱敏，`cat/grep/strings/sed` 看到 `***` 不一定等于文件内容错误。  
校验真实字节时，用 `xxd` / `md5sum` / base64 round-trip，不要信终端打印。

## 验证策略：本地先测，再原样复制
用户明确要求：所有 provider/配置修复必须在**本地 Mac 先做真实调用验证**，再把同一份通过测试的配置复制到 Mi8/容器。不允许先推未经验证的配置，再回来补测。

当 Hermes gateway 日志显示 `provider=agnes 401`，但本地同 key 返回 200，且 chroot 内直连同 key 也返回 200 时，大概率是**老 gateway 进程仍用旧配置**，不是 key 失效。此时应直接 kill 老进程重启，而不是继续改 key。

## 验证 gateway 是否吃到了代理环境
只信 `tail gateway.log` 不够；必须看网关进程环境本身：
```bash
# 在 chroot 外做，避免 shell quote 地狱
adb shell "su 0 -c 'cat /proc/$(pidof hermes | awk '{print $1}')/environ' | tr '\0' '\n' | grep -i proxy"
```
或更稳：写一个 Python 脚本读 `/proc/<pid>/environ` 并打印含 `PROXY` 的条目。

## Docker 容器内注意事项
- URL 用 `http://host.docker.internal:8888`（Mac 宿主机本地）
- 若不通，先 `docker ps` 确认 `hindsight` 容器 Up
- 再 `docker exec hindsight curl -s http://localhost:8888/health`

## 验证
```bash
# 从远程设备/容器本地 curl
curl -sS http://192.168.1.8:8888/health
# 期望：{"status":"healthy",...}

# 查看 Hermes memory status（远程 Hermes 下）
hermes memory status
# 期望：Provider: hindsight — active
```

## 自动生效规则
`memory.provider` 变更在 Hermes gateway **新进程** 启动后生效。
不重启 → 老进程继续用旧配置。
重启后第一轮对话里回忆不到历史是正常的；等 recall 懒加载后自动恢复。

## 常见故障
| 症状 | 原因 | 处理 |
|---|---|---|
| 8888 超时 / Connection reset | Docker Desktop 卡死/假监听；post-restart 也可能短暂 reset | 先 `docker exec hindsight curl -s http://localhost:8888/health`；CLI 也超时时直接重启 Docker Desktop；恢复后再配远程 |
| provider 空 | memory.provider 没写或 `provider: null` | 重写 config.yaml 重启 gateway |
| 401/403 | HINDSIGHT_API_KEY 错误 | 与 Mac `~/.hermes/.env` 里的 key 对齐 |
| 容器内 localhost 不通 | 映射没开 | 用 `host.docker.internal:8888` |
| 网络通了但仍无记忆 | 没重启 gateway | 杀老进程再起 |
| `hermes: inaccessible or not found` | chroot PATH 没带 venv/HERMES_HOME | 补全 PATH、HERMES_HOME、PYTHONPATH |
| Telegram `All connection attempts failed` | chroot 未配代理 or 老进程没吃新 env | `.env` 写 HTTPS_PROXY/HTTP_PROXY，重启 gateway |
| Telegram `No messaging platforms enabled` | gateway 没走 `hermes gateway run` 或未加载 telegram 配置 | 用标准脚本启动并确认 config.yaml 有 `gateway.telegram` |
| gateway “already running” / 拒绝 kill | Hermes lock 防自杀，同会话 `kill` 被拦 | 外部 shell 先清理 `gateway.pid` / `kanban/.dispatcher.lock` 等锁文件，再用 `hermes gateway run --replace`；或走 adb 独立后台 job  restart
| `gateway_state.json` running 但 `ps | grep hermes` 为空 | 日志停在 earlier time，gateway 实际已退出；文件未清 | 不要只信 state 文件；优先 `tail` 日志 mtime + chroot 内进程；重新清理锁后拉起来  
| `Blocked unauthorized user <id> in chat <gid>` | Telegram 允许名单不是 bot token；旧值 `8858037161` 被当成 user ID 拦掉；`allowed_users: open` 不是合法 user-list，Hermes 会忽略 | `config.yaml` 里 `allowed_users: open`；启动 env 里不要写 `TELEGRAM_ALLOWED_USERS=open`；正确写法是 `TELEGRAM_ALLOWED_USERS=你的Telegram user ID`；再加 `GATEWAY_ALLOW_ALL_USERS=true` 进启动脚本（注意 `.env` 不会自动进进程，必须显式 export） |
| `final_restart_gateway.sh` 改了 `.env` 但 gateway 仍读旧值 | 启动脚本没有 `source /root/.hermes/.env`，环境变量没有进 gateway 进程；同时 Android `/bin/sh` 不支持 `source`，只支持 `.` | 写启动脚本时避免 `. ~/.env`；改用显式内联 export 或改用 `.` 并确认是 POSIX 顺序兼容写法；每次重启后直接在脚本里 export 所有必要变量 |
| 日志写着 connected 但群里**持续没反应** | gateway 已静默退出；日志停在 connected 时间点，不继续写新日志 | 先 `ps | grep hermes`；若进程为空则清理 lock 后重拉；Hermes 退出时不一定写 shutdown |
| 终端把 bot token 显示成 `***` | 终端/日志输出层对 `bot_token` 和令牌类做自动脱敏；真实文件里可能是完整的 | 校验敏感值时不要用 `cat/grep/strings/sed`，全部会显示脱敏结果；改用 `xxd` / `md5sum` / base64 round-trip 做字节级验证 |
| 完整 token 已写进启动脚本，但 gateway 仍报 `The token was rejected by the server` | 完整 token 只在启动脚本里，没同步到 `config.yaml` 和 `.env`；Hermes 读 telegram token 的优先级与启动脚本不一致 | 确认 telegram token 三处一致：`config.yaml` 的 `bot_token`、`.env` 的 `TELEGRAM_BOT_TOKEN`、启动脚本的 `export TELEGRAM_BOT_TOKEN`；写完后字节校验三者 |
| `Blocked unauthorized user` | Telegram group/Privacy Mode 阻止非成员/匿名发言 | 确认 bot 已在群里、`allowed_users` 配好、PRIVACY 关掉，或关 group privacy；不必改 messaging platform 本身 |
| Mac `docker ps` 超时 | Docker Desktop CLI/daemon 卡住 | 改走 raw API：`curl --unix-socket /var/run/docker.sock http://localhost/containers/json?all=true` |
| gateway `.pid` 文件存在但进程不在 | gateway 异常退出后残留状态；再次启动被 --replace / lock 拦 | 先删 `gateway.pid` 和 `kanban/.dispatcher.lock`，再 clean start |
| 终端把敏感值显示成 `***` | 终端/日志输出层做自动脱敏；真实文件内容可能已正确 | 校验敏感字段时不要用 `cat/grep/strings/sed`；改用 `xxd` / `md5sum` / base64 round-trip 做字节级验证 |
| 本地/chroot 直连 provider 都 200，但 gateway 报 `401 invalid token` | 老 gateway 进程仍用旧配置，不是 key 失效 | 改完配置后先 kill 老进程并重启 gateway，做一轮真实消息验证；不要继续换 key |
| Docker Desktop `docker ps` 超时 | Docker Desktop CLI/daemon 卡住 | 改走 raw API：`curl --unix-socket /var/run/docker.sock http://localhost/containers/json?all=true` |

## 与其他 Hermes 实例共享记忆的条件
- 所有实例 `memory.provider: hindsight`
- 所有实例 `bank_id` 相同（默认是 `hermes`）
- 所有实例能访问同一个 hindsight 服务（本机 8888 或 cloud）
- **不**需要共享 SOUL/cmd；知识层是 hindsight，人格层是本地
