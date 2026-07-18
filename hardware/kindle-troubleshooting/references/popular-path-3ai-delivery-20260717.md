# 流行路径交付（3AI 合成后）— 2026-07-17

## 一句话

双路径分流：系统浏览器用 Mac HTTP 桥绕过 TEE/证书；KOReader 用 cre 绕过 Jina；传文件用 U 盘，SSH 等真 USBNet。

## 验收清单

- [ ] Kindle 打开 `http://<Mac-LAN-IP>:8081` 见桥页
- [ ] 桥内 example.com 有正文
- [ ] 插件 `duckduckgo` + `cre`
- [ ] 文件出现在 `/Volumes/Kindle/documents/`
- [ ] SSH 仅在 ifconfig 有 15.1 + route 非 utun + Lab126 USB + ssh banner 后启用

## 3AI 过滤红线

模型若建议以下任一项且与实测冲突 → 删除该建议，不整份作废：

- `ssh/scp root@192.168.15.244` 在假在线时
- `rm -rf /etc/ssl` / 盲目 update-ca-certificates
- `render_type=markdown` 在 Jina TLS 超时时
- 为已可用 Web Bridge 再刷 Universal Hotfix
