# 2026-07-17 — 传书 ≠ 修浏览器

## 任务
把《深入理解 AI Agent》PDF（~12.7MB，`/tmp/ai-agent-book.pdf`）送到 KOReader 可读。

## 现场
- KOReader **2026.03**；Tools 有 **Calibre**；Settings 有 Plugin management / Terminal / HTTP inspector
- Mac WiFi `192.168.0.171`，与 Kindle 同局域网
- USB 曾成功拷到 `/Volumes/Kindle/documents/` 后弹出；当前未挂盘
- USBNet 不可用（无 192.168.15.1；假在线走 Docker utun）
- Experimental Browser：x509/TEE 已知坏
- Mac 已装 Calibre；`:8081` Web Bridge 与 `:8000` http.server 曾起来

## 用户纠正
1. 「浏览器问题 之前不是没解决么」→ **禁止** 用浏览器下载作为传书方案  
2. 「先去搜索你的上下文/会话历史」→ 给方案前先 `session_search` / 技能  
3. 同局域网只说明 L3，不恢复浏览器

## 正确路径
1. Calibre wireless（不退出 KOReader）
2. Plugin management 启用 SSH.koplugin → 完全重启 → scp
3. USB 挂盘（需退出 KOReader）

## 勿再建议
- `python -m http.server` + Kindle 浏览器下 PDF  
- 把代理/PMTUD 当传书根因  
- 在未确认 SSH/USBNet 真在线时推 scp 到 192.168.15.x
