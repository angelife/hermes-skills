# PMTUD 黑洞诊断 — x.ai TLS 握手卡住 (2026-07-16)

## 症状
- `curl -x http://127.0.0.1:10808 https://accounts.x.ai` → CONNECT 200, TLS ClientHello 发出后 30s 超时
- 同代理 Google/GitHub 正常
- 手机同节点正常打开 x.ai
- `curl -4` 仍卡（已排除 IPv6）
- `curl --tls-max 1.2` 仍卡
- `openssl s_client -proxy` 也卡住

## 根因
**路径 MTU / PMTUD 黑洞**，非代理/节点/证书问题。

Docker 网桥 (172.18.0.0/16) + CF 优选隧道封装后，有效路径 MTU 低于 1500。TLS 1.3 ClientHello 是首个较大的应用层包，触发 DF 但 ICMP need-frag 回不来 → TCP 假死 30s。

## 诊断过程
1. 自行硬试 20+ 次失败 → 用户批评"少撞多问"
2. web_search 搜到 Arch Linux 论坛 + Unix SE 同一症状 → 指出 MTU
3. Grok API 分析: PMTUD 黑洞，建议 tcpMaxSeg:1360
4. OpenBridge 问 ChatGPT: IPv6 优先但 MTU 也确认，openssl s_client 测试
5. 两份资料喂 NLM → NLM 统一方案: IPv4 测试 → TLS1.2测试 → tcpMaxSeg 修复

## 修复方案（需用户决策）
在 v2rayN 当前节点的 streamSettings 加 sockopt:
```json
"streamSettings": {
  "sockopt": {
    "tcpMaxSeg": 1360,
    "tcpNoDelay": true
  }
}
```
若 1360 失效, 依次试 1280 → 1200。

## 来源
- Grok 分析: `~/Documents/Obsidian Vault/土同学工作档案/xai-tls-mtu-诊断.md`
- ChatGPT 分析: `~/Documents/Obsidian Vault/土同学工作档案/xai-tls-chatgpt-分析.txt`
- NLM 合成: `~/Documents/Obsidian Vault/土同学工作档案/nlm-pmtud-合成方案.md`
