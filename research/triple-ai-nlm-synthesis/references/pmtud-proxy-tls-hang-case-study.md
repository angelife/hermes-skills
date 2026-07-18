# PMTUD / TLS 握手超时 — NLM 中心制实战案例

## 问题
macOS 通过 v2rayN (xray) HTTP CONNECT 代理到 accounts.x.ai：
- CONNECT 隧道建立成功（HTTP 200）
- TLS ClientHello 发出后无响应，30 秒超时
- 同一代理 Google/GitHub 正常
- 手机（同节点同账号）可正常打开 x.ai
- Docker 网桥 172.18.0.0/16 运行中
- 无 sudo 权限

## 收集渠道（三通道全用）

| 通道 | 方法 | 结果 |
|------|------|------|
| B — 搜索+NLM | web_search "CONNECT tunnel TLS hang macOS Docker" | Arch 论坛/Unix SE 帖：指向 MTU |
| D — Grok API | curl 调 xhahlf.top/v1/chat | 诊断 PMTUD 黑洞 |
| A — 问 ChatGPT | OpenBridge browser_evaluate 提交问题 | 诊断 IPv6 + MTU |

## NLM 中心分析

1. 创建笔记本 `x.ai-TLS握手-PMTUD诊断` (`2fd4863b`)
2. 喂入：Grok 回复 + ChatGPT 回复 + 搜索资料
3. 查询 NLM："分析共识和分歧，出统一方案"

**NLM 输出：**
- 共识：代理/节点正常，问题在 Mac 端 TLS 路径
- 分歧：Grok 说 PMTUD，ChatGPT 说 IPv6 优先
- 综合推荐：先测 IPv4（已排），再测 TLS 1.2，最后改 tcpMaxSeg
- **根因锁定**：PMTUD 黑洞（IPv4 和 TLS 1.2 均卡住，排除 IPv6）

## 修复方案（待用户决策）

在 v2rayN 出站 streamSettings 加：
```json
"sockopt": { "tcpMaxSeg": 1360, "tcpNoDelay": true }
```
若不通降到 1280 → 1200。

## 教训
- 不要改 standalone xray 测试 → 绕经 Docker 桥接无效
- `sockopt` 对 HTTP CONNECT 出站不生效，需改隧道出站
- NLM 给出统一方案后直接执行，不要自己综合
- 所有诊断材料→NLM→执行→存档 Obsidian

存档位置：`~/Documents/Obsidian Vault/土同学工作档案/`
- `xai-tls-mtu-诊断.md`（Grok）
- `xai-tls-chatgpt-分析.txt`（ChatGPT）
- `nlm-pmtud-合成方案.md`（NLM）
