# 闲鱼 GitHub 项目索引（2026-07 查询）

## 智能客服（卖家向）

### xianyu-auto-reply 系列
多个独立项目，功能类似，技术栈统一（Python + FastAPI + Playwright + WebSocket）。

共同功能：
- 多账号扫码登录
- AI 关键词匹配 + LLM 回复
- 自动发货确认
- Web 管理后台
- Docker 一键部署
- 消息实时处理（WebSocket 连接闲鱼服务器）

活跃 fork：
| 项目 | 特点 |
|------|------|
| `GuDong2003/xianyu-auto-reply-fix` | 较活跃维护，修复版本 |
| `uniquecolin/xianyu-auto-reply` | 功能完整，Star 较多 |
| `dikoweii/xianyu-auto-reply-1` | 文件结构清晰，含 utils/ 工具模块 |
| `IAMLZY2018/XianYuAssistant` | 侧重多账号管理 + 扫码登录 |
| `zhinianboke/xianyu-auto-reply` | 早期版本 |

### xianyu-auto-reply 文件结构（参考 `dikoweii/xianyu-auto-reply-1`）
```
├── Start.py                     # 启动入口
├── XianyuAutoAsync.py           # WebSocket 消息处理核心
├── reply_server.py              # FastAPI Web 服务器
├── db_manager.py                # SQLite 数据库管理
├── cookie_manager.py            # 多账号 Cookie 管理
├── ai_reply_engine.py           # AI 回复引擎（支持多种模型）
├── order_status_handler.py      # 订单状态处理
├── item_search.py               # 商品搜索（Playwright 无头模式）
├── qr_login.py                  # 二维码登录
├── secure_confirm_ultra.py      # 自动确认发货
├── static/                      # Web 前端界面
│   ├── index.html
│   ├── js/app.js
│   └── css/
└── docker-compose.yml
```

## 行情监控（买卖双向）

### GooFish-AIMonitor
`tristanwqy/GooFish-AIMonitor` — 最完整的监控方案

架构：Python FastAPI + Playwright + React + Vite + SQLite + Docker

功能：
- 关键词搜索自动抓取
- LLM 二次审核商品对版
- 收藏夹降价监控 + 邮件提醒
- 定时扫描 + 手动刷新
- 全 Web 管理界面
- 数据全本地（127.0.0.1:8000）

部署方式：Docker compose（推荐）或本地 Python 运行

### ai-goofish-monitor（已归档）
`Usagi-org/ai-goofish-monitor` — 功能类似但已归档不维护
同样基于 Playwright + AI，有 Web UI

### GooFish-AIMonitor
`ddCat-main/ai-goofish` — 按关键词自动爬取 + AI 筛选 + 邮件通知

## Chrome 扩展

### xianyu-monitor-extension
`lubei0612/xianyu-monitor-extension` — Chrome Extension MV3
- 轻量，无需后端
- 设置关键词/价格区间
- 自动监控新品 + 卖家分析
- 安装即用

## 多平台发布

### Amplipost
`AlanSong2077/Amplipost` — 基于 OpenClaw + Claude Code
- 同步发布到闲鱼/B站/抖音
- PreToolUse Hook 检查违禁词（高仿/A货等）
- 发布前自动拦截违规内容

## 其他

### xianyu-monitor（OpenClaw Skill）
`voltwake/xianyu-monitor` — macOS 专用，OpenClaw Skill 形式
- 自动搜索 → 去重 → 推 Telegram
- 零成本，不需要 API Key
- 使用 AppleScript 控制 Chrome 地址栏（绕过 baxia 风控）
- 登录态约 7 天有效
- 仅支持 macOS
