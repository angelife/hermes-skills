# HUAWEI Cloud AI Shell — Session Details

## Env Vars (auto-configured)

| Variable | Description |
|----------|-------------|
| `HW_ACCESS_KEY` | Huawei Cloud temporary AK |
| `HW_SECRET_KEY` | Huawei Cloud temporary SK |
| `HW_SECURITY_TOKEN` | Temporary security token (expires with session) |
| `PROXY_URL` | WebSocket control channel URL for container orchestration |

## PROXY_URL Parsed

```text
wss://control-service-green.cn-north-4.huaweicloud.com:8443/v1/devenvcontrol/register/{instance_id}?register_code={code}
```

- Instance ID: `e5cf15d45941449895ca5bced7fbc46c` (example — changes per session)
- Port: 8443 (control) and 8443 (data, different IP)
- Protocol: WebSocket (wss://)

## devenvd Details

| Property | Value |
|----------|-------|
| Path | `/usr/.devenv/devenvd` |
| Version | 1.7.1 |
| Flags | `-f` (config file), `--set` (set parameter) |
| PID | 22 |
| Owner | Infrastructure (NOT user-serviceable) |
| Autostart | Yes — container base image includes it |
| Uptime | Reports container image lifetime, NOT session lifetime |

## Network Connections at Rest

Two ESTABLISHED WebSocket connections:
1. Control channel: `container:57588 → 192.171.192.75:8443`
2. Data channel: `container:60416 → 192.171.201:8443`

## Model Availability (Xunfei MaaS, via API key)

| Model ID | Size | Status |
|----------|------|--------|
| `xopqwen36v35b` | 36B Qwen | ❌ Free promo expired 2026-07-01 |
| `xop35qwen2b` | 2B Qwen | ✅ Always free |
| `xophunyuan7bmt` | 7B Hunyuan (Tencent) | ✅ Always free |
| `xop3qwen1b7` | 1.7B Qwen | ✅ Always free |

## Keepalive — 夏虫 (Cattle) Pattern

The ONLY browser-independent keepalive method is Tampermonkey script. The `devenvd` heartbeats are for infrastructure orchestration — they do NOT prevent session container destruction.

Official policy: *"Beta期间，AI Shell创建的容器每次连接使用时长为6小时，到期后会立即销毁此台容器。再次启动时，会为您创建一台全新的容器。"*

**Recommended: cattle pattern ("夏虫").** See main SKILL.md for the philosophy. Backup/restore scripts are available at `templates/xia-backup.sh` and `templates/restore.sh` under this skill directory. The user named this node **夏虫** (summer insect — lives at most 6 hours, never sees winter).
