---
name: huo_bridge
description: >
  火同学(Mac)HTTP Bridge — 让云端木同学经 cloudflared 隧道远程派活到火同学本机执行。
  协议对齐 Federation Hub 消息格式（GET /capabilities, POST /tasks, GET /tasks/{id}），
  动作白名单分级、Bearer 认证、异步任务、审计。适用于：木同学需远程在火同学上跑 NLM /
  查 gateway / git / adb / 构建等场景。部署在火同学本机，不由木同学托管。
version: 1.0.0
author: 木同学 (QwenPaw cloud agent) + angelife 架构定稿
tags: [infrastructure, 火同学, bridge, 远程执行, agent-federation, cloudflared]
---

# 火同学 HTTP Bridge（huo_bridge）

木同学(云端)无法直接 SSH 进火同学（cloudflared quick tunnel 需客户端，沙箱装不上）。
本技能提供**火同学本机 HTTP 命令桥**，经 cloudflared 暴露，木同学 curl 调，实现远程派活。

## 架构

```
木同学(云端) ──curl──→ cloudflared tunnel ──→ 火同学:8899 (bridge.py)
                                      ↓
                              本地执行(白名单动作)
                                      ↓
                              结果回传木同学
```

## 部署（在火同学 Mac 上，由土同学/用户操作，木同学不托管）

```bash
# 1. 从 hermes-skills 取脚本
#    git clone 后位于 infrastructure/huo_bridge/scripts/bridge.py
#    或 curl 直取 raw 文件

# 2. 生成随机 token（这就是认证密码）
TOK=$(python3 -c "import secrets;print(secrets.token_hex(16))")
echo "$TOK"   # 把这个发给木同学

# 3. 启动 bridge（默认 8899，调火同学实际工作区路径）
python3 bridge.py --port 8899 --token "$TOK"

# 4. 用 cloudflared 暴露（HTTP 模式，非 ssh://）
cloudflared tunnel --url http://127.0.0.1:8899
# 把生成的 *.trycloudflare.com 地址发给木同学
```

木同学侧调用：
```bash
# 探能力
curl -s -H "Authorization: Bearer $TOK" <地址>/capabilities
# 派活（异步）
curl -s -X POST -H "Authorization: Bearer $TOK" -H "Content-Type: application/json" \
  -d '{"id":"u1","action":"git_status","args":{},"timeout":30}' <地址>/tasks
# 取结果
curl -s <地址>/tasks/u1
```

## 协议（对齐 Federation Hub，未来 HTTP→WS→MQ 复用）

请求：`{"id":"uuid","action":"...","args":{},"timeout":30}`
返回：`{"id":"uuid","ok":true,"stdout":"...","stderr":"","duration_ms":512}`

端点：
- `GET /capabilities` → 自报 hermes/gateway/adb/nlm/git 能力
- `POST /tasks` → 入队，返 `{"task_id","status":"running"}`
- `GET /tasks/{id}` → 查结果（异步，可轮询）
- `GET /health` → ok

## 动作白名单（分级，禁裸 shell）

允许（按等级）：
- Read: `git_status` `ps` `df` `gateway_status` `nlm_help`
- Build: `git_pull` `hugo_build`
- Service: `gateway_restart`（默认禁用，需显式启用）
- Device: `adb_devices` `adb_pull`

禁止（根本无对应动作，永不可达）：
- Dangerous: `sudo` `rm` `diskutil`
- Interactive: `bash` `zsh` `ssh`

> 无 `POST /exec{"cmd":...}` 接口 —— 不暴露任意 shell。

## 安全

- 仅经 HTTPS(cloudflared)；Bearer Token(≥128bit)；参数校验；全审计(`~/bridge_audit.log`)
- 白名单锁死破坏能力；token 泄漏也干不了 rm/sudo
- 不用时关隧道；token 定期换
- 隐私：执行结果经公网到木同学，与 Hindsight 同级；敏感数据慎跑

## 已知未知（不猜）

- NLM CLI 具体格式未知 → `nlm_help` 动作先探测 `which nlm`，探明后补 `nlm_query` 动作
- 火同学实际工作区路径(`~/workspace`/`~/hugo-site`)为占位，按实机改
- Federation Hub 是否已有实现未知 → 本桥协议对齐其消息格式，不依赖其存在

## 中期演进

火同学改跑 `hermes-bridge-agent` 主动 WebSocket 连 Federation Hub（outbound，不需公网 IP/客户端），
本桥的 task 消息格式直接复用。见 `infrastructure/n1-edge-anchor` 相关规划。
