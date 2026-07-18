# FuturePPO Bulk Probe Guard

## 故障表现

New API 渠道配置正确（abilities 有、base_url 正确、models 匹配），但所有请求返回：
```
channel error (channel #2, status code: 403): bad response status code 403
```
日志详情：
```
该ip已被封禁，原因：bulk probe guard: ip 116.237.138.88 requested 8 distinct models in 60s (last_user 7010, offense 1)
```

## 根因

上游 `api.futureppo.top`（Cloudflare 代理）有 **bulk probe guard** 防护：
- 同 IP 在 60 秒内请求 **8 种不同模型** → 触发临时 IP 封禁（403）
- 发生在批量测试/模型发现场景（如循环测 `deepseek-v3.2`, `gemini-3.1-flash-lite-preview`, `openrouter/free`, `gpt-5.5` 等）
- IP 级封禁：Docker 容器通过 NAT 共享宿主机的公网 IP

## 影响范围

- 被封后所有模型请求都返回 403，不论用哪个 key
- 即使通过 v2rayN SOCKS5 代理（出口 IP 相同）也不可逃逸
- Docker 容器（bridge 模式出口 IP = 宿主机公网 IP）会被统一封禁

## 修复

### 短期

等待封禁自动解除（通常 5-60 分钟）。封禁间隔内避免继续请求。

### 长期

**不要在 New API 渠道上做批量模型探测。** 先用宿主机直测（`curl` 不带容器）确认模型名后，再一次性配好渠道。渠道配置好后只请求实际要用到的模型。

### 备选

如果经常需要批量测试，考虑：
- 给 Docker 容器配置独立出口 IP（`--network host` 模式或独立代理）
- 在请求间加延迟（`sleep 5`）避免集中探测