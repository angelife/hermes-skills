# 系统建成进度 + 服务监管（2026-07-17）

## 用户目标（原话）

- 把更多服务放进 `http://IP:28080/` 监管
- 对照 `https://angelife.github.io/knowledge-architecture/v2/` 一目了然看各部分状况
- **项目进度完美体现**：每天干到哪里了；最终目的是把系统完全建成

## 数据源

| 用途 | 路径 |
|------|------|
| 架构完成度蓝图 | `angelife.github.com/hugo-site/layouts/_default/architecture-v2.html` 完成度明细 |
| 今日日报 | `~/Documents/Obsidian Vault/每日工作记录/YYYY-MM-DD.md` |
| 共享 TODO | 同目录 `_TODO.md` |
| 会话任务 | `~/.hermes/state/active/task.yaml` |
| 晚课 | `~/.hermes/state/evening-score-*.md` |
| 阻塞/待拍板 | `~/.hermes/CREATIVE.md`、`morning-decision-queue.md` |
| 自检分 | `~/.hermes/state/self_check/scores.json` |
| 局域网 IP | `~/.hermes/state/lan-ip.json` |

## 服务探针清单

| 服务 | 端口 | 组 |
|------|------|-----|
| Dashboard | 28080 /health | 核心 |
| OpenBridge | 10088 | 核心 |
| Hindsight | 8888 | 核心 |
| 代理 SOCKS | 10808 | 网络 |
| OpenCLI | 19825 | 网络 |
| Kindle Bridge | 8081 / | Kindle |
| Calibre OPDS | 8089 /opds | Kindle |
| 书单 HTTP | 8091 / | Kindle |
| 联邦 Hub | 28081 /status | 舰队 |

## 验收样例（本机会话）

- build ~74%（planned~67 + live~85）
- services 7/9（Hub 常未跑不算面板坏）
- 首页段落齐全；`/api/status` 有 layers + services

## 相关技能

- `lan-ip-auto-sync` — 换网后 URL 展示
- `unified-self-check` — 写 scores.json
- `hermes-cron-design` — cron 模型漂移「有啥用啥」
