---
name: xianyu-selling-tools
description: 闲鱼二手交易工具链 — 智能客服自动回复、商品行情监控、价格追踪。覆盖 GitHub 开源项目选型、部署方式对比、避坑记录。
trigger: 用户提到闲鱼、二手交易、卖东西、auto-reply、监控降价、GooFish
---

# 闲鱼二手交易工具链

## 场景分类

| 场景 | 推荐项目 | 技术栈 |
|------|---------|--------|
| **智能客服**（卖家自动回消息） | `xianyu-auto-reply` 系列 | Python + FastAPI + Playwright + WebSocket |
| **行情监控**（搜同款/盯降价） | `GooFish-AIMonitor` | FastAPI + Playwright + React + SQLite |
| **商品监控扩展**（Chrome 插件） | `xianyu-monitor-extension` | Chrome Extension MV3 |
| **多平台发布**（闲鱼+B站+抖音） | `Amplipost` | OpenClaw + Claude Code Hooks |

## 项目详情

### xianyu-auto-reply（智能客服）

多个活跃 fork，推荐：
- `GuDong2003/xianyu-auto-reply-fix` — 较活跃维护
- `uniquecolin/xianyu-auto-reply` — 功能完整

**功能：**
- 多账号扫码登录管理
- AI 自动回复（关键词匹配 + LLM）
- 自动确认发货
- Web 管理后台
- Docker 一键部署

**部署：**
```bash
git clone https://github.com/GuDong2003/xianyu-auto-reply-fix.git
cd xianyu-auto-reply-fix
docker compose up -d
```

### GooFish-AIMonitor（行情监控）

**功能：**
- 关键词搜索 → AI 大模型把关筛对版商品
- 收藏商品降价自动邮件提醒
- 定时扫描，Web 控制台

**部署：**
```bash
git clone https://github.com/tristanwqy/GooFish-AIMonitor.git
cd GooFish-AIMonitor
# 需要 Python ≥3.12 + Docker
cp .env.example .env
docker compose up -d
```

**已知踩坑（2026-07 记录）：**
- Docker Hub 在某些网络环境下 IPv6 连接重置 → 需配代理
- Python ≥3.12 必须（3.11 不可用）
- Xianyu 反爬严格：必须非 headless 浏览器 + 真人扫码登录
- Playwright 需要安装 Chromium browser binary

### xianyu-monitor-extension（Chrome 插件）

纯前端扩展，无需后端。安装即用，适合轻量监控。

## 使用策略

| 需求 | 方案 |
|------|------|
| 卖家自动回复咨询 | `xianyu-auto-reply` |
| 蹲好价/监控降价 | `GooFish-AIMonitor` 或 Chrome 扩展 |
| 市场行情分析 | `GooFish-AIMonitor` 搜索+AI 筛选 |
| 两个都想用 | 分别部署，不冲突 |

## Pitfalls

- 闲鱼用户协议禁止自动化访问，用这些工具自担风险
- 登录态一般 7 天过期，需重新扫码
- Playwright headless 模式会被闲鱼直接拦截（baxia 风控）
- goofish.com 页面结构频繁变动，选择器可能失效
- 免费版 LLM 审核可能不够准，建议配一个便宜的 OpenAI 兼容接口
