---
name: free-ai-api-farming
title: "免费AI API账号注册与网关部署"
description: "批量注册免费AI服务账号 → 接入API网关 → 对外暴露OpenAI兼容接口。覆盖注册机部署、网关Docker搭建、多Provider适配、Token池管理。适用于Grok/DeepSeek/智谱/通义等支持新用户免费额度的AI平台。"
version: 1.2.0
author: 土同学
tags: [ai, api, gateway, grok, automation, token-freedom]
---

# 免费AI API Farming

## 核心策略

**不依赖任何单一平台。不触碰任何违规方案。零成本优先。**

原则（编码自用户明确立场）：
- ✅ **只走官方免费额度/试用** — Gemini API Key、DeepSeek 新手礼包、智谱新号额度
- ✅ **自己产号，自己用** — 注册机产号自用，不商用不共享
- ❌ **不碰 ToS 违规方案** — Cookie 注入/网页转 API/共享 key 都不碰，封号损失远大于收益
- ❌ **不花钱** — 能用免费试用解决的，不充值。打码费（几分/次）是唯一可接受的微小投入
- ✅ **分散风险** — 所有免费额度都是给你用的，不是给你薅的。封一条换下一条，总量不减少
- ✅ **赌漏洞必输** — 共享 key/注册机漏洞都是临时窗口。趁活着建流水线，窗口关了还能改改用到别的平台

## 架构

```
注册机（产号）              API 网关（消费）
+--------------+    tokens    +--------------+
| grok-build-auth|----------->|  grok2api      |<- Claude Code/Codex/Cursor
| 适配器1: Grok |            |  账号池        |
| 适配器2: DS   |            |  负载均衡      |
| 适配器3: 智谱  |            |  自动续期      |
| ...          |            |  OpenAI API    |
+--------------+            |  管理后台      |
                            +--------------+
```

核心理念：一次注册 -> 拿免费额度 -> 所有模型走同一个网关，封一个换一个。

## Phase 1: 注册机部署

### grok-build-auth（已验证）

项目地址：`https://github.com/dongguatanglinux/grok-build-auth`

原理：
1. **注册** — 纯HTTP模拟x.ai注册流程：邮箱验证码 + Turnstile打码 + 建号
2. **SSO** — 提取session cookie供OAuth复用
3. **OAuth** — PKCE流程换access_token/refresh_token
4. **导出** — 写CLIProxyAPI兼容的auth JSON

需要的外部服务：
| 服务 | 用途 | 费用 |
|------|------|------|
| YesCaptcha | Turnstile验证码识别 | 免费试用几百次，之后几块钱 |
| 临时邮箱 (mail.tm / tempmail.lol / CF D1) | 收注册验证码 | 免费 |

### mail.tm 免费邮箱适配（tempmail.lol 中国IP被封锁的替代方案）

Tempmail.lol 免费层封锁中国IP。替代方案：使用 mail.tm 完全免费的 API（不需要 API key）。

安装：
```bash
cd grok-build-auth/xconsole_client/
# 下载适配器
curl -O https://raw.githubusercontent.com/... 或手动复制
# 或直接从 skill scripts/ 目录复制
cp ~/.hermes/skills/free-ai-api-farming/scripts/mailtm-transport.py xconsole_client/mailtm_transport.py
```

然后修改 `run.py` 两处：
1. `_make_email_provider()` 函数中添加 `elif backend == "mailtm":` 分支（见 scripts/mailtm-transport.py 顶部注释）
2. argparse 的 email 选项添加 `"mailtm"` 到 choices，默认改为 `"mailtm"`

运行：
```bash
export YESCAPTCHA_API_KEY=xxx
python3 run.py -n 1 -e mailtm --no-oauth
# 全链路：python3 run.py -n 1 -e mailtm
# 批量：python3 run.py -n 10 -t 3 -e mailtm
```

先跑 `--no-oauth` 验证注册链路，再跑全链路。

### 通用注册框架（计划中）

抽离各平台的共性，做成适配器模式：
```
临时邮箱池 -> 打码池 -> 注册器 -> Token导出
                |
           各平台适配器
           (Grok / DS / 智谱 / 通义 / Claude)
```

## Phase 2: API 网关部署

### grok2api（已验证）

项目地址：`https://github.com/chenyme/grok2api`

Go + React，纯Docker部署。已验证 macOS Docker 环境。

**快速部署：**
```bash
git clone https://github.com/chenyme/grok2api.git
cd grok2api
JWT_SECRET=$(openssl rand -hex 32)
ENC_KEY=$(openssl rand -base64 32)
ADMIN_PWD=$(openssl rand -hex 8)
docker compose up -d
```

详细配置见 `references/grok2api-deployment.md`。

**注入账号：**
1. 登录管理后台（http://localhost:8000）
2. 上游账号 -> 接入 Grok Build/Web/Console 账号
3. 等待额度同步完成
4. 创建客户端密钥（g2a_xxx）
5. 用该密钥调用 /v1/*

## Phase 3: 对接工具

已验证可接入的工具：
- Claude Code — 自定义Base URL指向网关
- Codex — 同上
- Cursor — 设置->模型->自定义端点
- OpenCode — provider配置指向网关

接入方式：
```bash
# Claude Code 示例
export CLAUDE_CODE_API_KEY="g2a_xxx_xxx"
export CLAUDE_CODE_BASE_URL="http://网关IP:8000/v1"
```

### 代理兼容性关键坑（curl_cffi vs 系统curl）

**macOS 上的常见代理（Google服务端口10808）用系统curl正常，但 curl_cffi 的 bundled libcurl 无法通过该代理建立连接。** 这个问题导致注册机（grok-build-auth）curl: (35) TLS 连接超时或 curl: (28) Connection timed out。

```bash
# ✅ 系统curl通
curl -x http://127.0.0.1:10808 https://accounts.x.ai

# ❌ curl_cffi不通
from curl_cffi import requests
requests.get('https://accounts.x.ai', proxies={'https': 'http://127.0.0.1:10808'})  # 超时
```

**解法：** 强制切换到系统curl子进程

```bash
# 1. 移除 curl_cffi（触发 fallback 到 CurlSubprocessTransport）
rm -rf /tmp/grok-build-auth/.venv/lib/python3.11/site-packages/curl_cffi*

# 2. 设代理环境变量
export HTTPS_PROXY=socks5://127.0.0.1:10808
export HTTP_PROXY=socks5://127.0.0.1:10808

# 3. 跑注册
python3 run.py -n 1 -e mailtm --no-oauth
```

**局限性：** 系统 curl 子进程没有 TLS 指纹伪装，可能被 Cloudflare 拦截。且如果 x.ai 本身在 Mac 上通过 v2rayN 代理 TLS 握手超时（PMTUD 黑洞），系统 curl 同样超时。此时需先解决 v2rayN 出站 tcpMaxSeg（见 proxy-management PMTUD 诊断）。

### CLIProxyAPI：注册机之外的另一条路

用户提及的 **CLIProxyAPI**（GitHub: `stainless-api/cli-proxy-api` 等）是一条与注册机正交的路径——它不产号，而是把已有的网页订阅伪装成 API。

核心价值：如果你已经有某个AI平台的包月/包年网页订阅（如 ChatGPT Plus、Claude Pro），CLIProxyAPI 可以把该订阅额度转为标准 OpenAI 兼容 API 调用。

**与注册机的关系：**
- 注册机产 Token：适合还没账号的新手，零成本批量产号
- CLIProxyAPI 转 API：适合已有网页订阅的专业用户，最大化利用订阅额度
- 两者可互补：注册机产的 Token 接入 API 网关，CLIProxyAPI 转换的 API 也接入同一个网关

**用户评价：** 用户认为此方案「对你非常有利」——稳定的 API 调用能力是本技能的核心瓶颈之一。

计划：待当前注册机链路走通后，深入评估 CLIProxyAPI 的技术方案和整合路径。

### 代理订阅源：从 Telegram 获取

当需要访问被代理阻断的域名（如 x.ai/Grok）时，可在 Telegram 群组/频道的导出数据中搜索有效订阅链接。

**搜索关键词：**
```
"订阅链接:" | "subscribe?token" | "vmess://" | "vless://" | "trojan://" | "hysteria2://" | "ss://"
```

**找到的免费订阅链接通常来自：**
- 代理分享频道（如 @wxdy666）
- 机场推广
- 网友匿名投稿

**验证订阅是否有效：**
```bash
curl -s --max-time 10 -x http://127.0.0.1:10808 "https://订阅链接" | head -5
# 返回进制节点列表 = 有效
# 返回 {"message":"token is error"} = 已过期
```

**添加到 v2rayN：**
详见 `proxy-management` 技能的 `references/v2rayn-db-operations.md`。

**免费订阅的局限性：**
- 免费订阅存活时间短，流量少
- 多数也是 Cloudflare WARP 节点，同样到不了某些境外服务
- 建议作为临时方案，拿到有效节点后，节点 URL 可直接在各别需要验证

### 打码费用

| 限制 | 说明 |
|------|------|
| Grok Build key有效期 | OAuth token有有效期，网关支持自动续期 |
| Web/Console SSO | 不可自动续期，失效后需重新授权 |
| 打码成本 | YesCaptcha每次注册几厘钱，大批量需预算 |
| 平台风控 | 并发过高触发风控，建议温和节奏 |
| Tempmail.lol 封锁中国IP | 改用 mail.tm（免费免key，见 scripts/mailtm-transport.py） |
| YesCaptcha 免费试用 | 新注册送几十到几百次，足够验证链路和少量产号 |

## Pitfalls

群发的key都是六小时限时，只用来测试，正式用自产key
- 注册机依赖外部服务 — 打码API/邮箱API若挂了，链路就断了，保持备用方案
- 网关凭据密钥不可丢 — credentialEncryptionKey更换后所有已有账号无法解密
- 注册时注意IP/浏览器指纹 — 太高频可能被x.ai风控拉黑
- Docker部署注意防火墙 — 网关暴露8000端口需确认安全策略
- 先验证单账号再批量 — 先手动走通全链路确保理解流程，再自动化批量
- mail.tm 域名可能变化 — 如果 web-library.net 失效，先 GET /domains 查可用域名
### 河涛 Grok 公益中转站（2026-07-17 新增）

免费 Grok API 中转站，全部模型免费，无需充值。
- 站点：https://gy.hetaosu.xyz
- Base URL：https://gy.hetaosu.xyz/v1
- 模型：grok-4.5 / grok-4 / grok-3 / grok-3-mini
- 需注册后创建 API Key，即可配置到 Hermes provider
- 20 Key 容灾配置示例见 `references/hetaosu-grok-free-api.md`
- Hermes fallback 配置参考 `hermes-provider-fallback-config` 的 `references/hetaosu-grok-fallback.md`

- Grok API 可通过 Hermes 配置中的 API key 直调 — 当前 xhahlf.top endpoint 支持 grok-4.5 模型，可通过 CF WARP 代理访问（详见 proxy-management skill 的 cdp-operational-gaps.md 方案C）

### Google AI Studio / Gemini 免费额度 — 核实口径（2026-07-17）

公众号常写「Google 免费额度相当慷慨 / 每分钟 100 万 Token」。**半真半假**：

| 项 | 营销文常见说法 | 更接近 2026 现状 |
|----|----------------|------------------|
| Free Tier | 永久免费 | 部分模型仍有，常不用绑卡 |
| 1M TPM | 「每分钟 100 万 Token」 | **偏高**；免费层常见约 **250K TPM** |
| RPM | 暗示很高 | Free 约 **5–15 RPM** |
| RPD | 常省略 | **真硬顶**：Pro~100 / Flash~250 / Flash-Lite~1000（会变） |
| 多 Key | 多号=多额度 | **按项目共享**，同项目不加倍 |
| 1M 上下文 / 多模态 | 有 | **基本对** |

**查证顺序（禁止照抄公众号）**：官方 pricing → rate-limits → `aistudio.google.com/rate-limit` 账号实时页。  
对 Hermes 全天跑：卡的是 RPD/RPM，不是「1M context 随便刷」。  
详见 `references/gemini-free-tier-reality-check.md`。
