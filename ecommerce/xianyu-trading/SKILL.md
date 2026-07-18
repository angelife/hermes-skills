---
name: xianyu-trading
description: 闲鱼（Goofish）二手交易工作流 — 买前行情调研、卖时商品上架优化、工具链安装与避坑。覆盖价格研究、竞品分析、可用开源工具及其安装陷阱。
tags: [xianyu, goofish, second-hand, trading, marketplace]
---

# 闲鱼二手交易工作流

## 触发条件
- 用户说「帮我看看X在闲鱼什么价」
- 用户说「我想在闲鱼卖/买X」
- 用户分享闲鱼链接要求分析

## 价格调研

### 手动查价（最可靠）
1. 用 web_search 搜索「闲鱼 X 价格」「X 二手价」
2. 无直接数据时，搜索行业文章了解新品定价和市场趋势
3. 综合新旧品差价给出合理区间

**参考定价逻辑：**
- 新品跌价严重的品类（3D打印机、消费电子）：二手价 ≈ 新品价 × 40-60%
- 新品价格稳定品类：二手价 ≈ 新品价 × 60-80%
- 2025-2026 年 3D 打印机二手市场挤压严重（拓竹 A1 mini 新机 999元，入门级二手跌破千元）

### 自动化监控工具

| 工具 | 用途 | 安装状态 | 安装方式 |
|------|------|---------|---------|
| **GooFish-AIMonitor** | AI 选品 + 降价/售罄提醒 | 未成功安装 | Docker Compose，需 Docker Hub 可达 |
| **xianyu-auto-reply** | 多账号智能客服/自动回复 | 未安装 | Python + FastAPI + Playwright |
| **voltwake/xianyu-monitor** | OpenClaw Skill，搜索+推送TG | 未尝试 | macOS + Node.js + Playwright |

## 商品上架优化

### 标题公式
`[核心词] + [属性词] + [场景词] + [信任词]`

示例：`创想三维K1 3D打印机 高速CoreXY 几乎全新 上海徐汇自提`

### 描述结构
1. 第一段：为什么卖（个人闲置/搬家清仓/升级换代 → 增加信任）
2. 第二段：商品详情（成色、参数、使用时长、购入渠道）
3. 第三段：卖点放大（对比新品省多少钱、赠送配件）
4. 第四段：交易条件（包邮/自提/可小刀）

### 图片要求
- 必须有实物拍摄（闲鱼 2025 年底开始严查纯网图）
- AI 可辅助调色/滤镜，不能替代实拍

## 可用开源工具详情

### xianyu-auto-reply（卖家客服）
- GitHub: `GuDong2003/xianyu-auto-reply-fix`（较活跃 fork）
- 功能：多账号管理、AI 自动回复、自动发货确认、Web 管理后台
- 技术栈：Python + FastAPI + SQLite + Playwright
- 部署：Docker Compose 一键
- Python >= 3.12 要求

### GooFish-AIMonitor（市场监控）
- GitHub: `tristanwqy/GooFish-AIMonitor`
- 功能：搜商品→AI 把关→降价提醒→收藏监控
- 技术栈：Python + FastAPI + Playwright + React
- Web UI：127.0.0.1:8000
- 部署：Docker Compose

## 已知安装陷阱

### Docker Hub 连不上
- 症状：`failed to authorize: failed to fetch oauth token` IPv6 重置
- 原因：Docker daemon 通过 IPv6 连 Docker Hub 被重置
- 临时解决：`pip install` 直接跑（不依赖 Docker）
- 彻底解决：配置 Docker daemon 代理 `~/.docker/config.json`

### Python 版本不满足 ≥3.12
- 当前系统有 3.11/3.13/3.14，缺 3.12
- 解决：patch `pyproject.toml` 改 `requires-python = ">=3.11"`

### 闲鱼反爬
- headless Chrome 被直接拦截（"非法访问"）
- 需非 headless 模式 + 真实浏览器指纹
- 登录态需扫码，约 7 天过期

## 闲鱼平台基础信息
- 零门槛：不需要营业执照、保证金
- 流量机制：基于活跃度和好评率，不靠投流
- 支持二手 + 全新商品双赛道
- 违禁词类：高仿/A货/保健品/医疗器械等
