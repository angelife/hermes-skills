# Kindle PW5 3AI Partial-Channel Case (2026-07-17)

用户指令：`这个问题 你推给3ai 按照流行处理分析解决`

## 通道实绩

| 通道 | 结果 |
|------|------|
| OpenBridge Gemini | 空欢迎页，未成功提交 |
| OpenBridge ChatGPT | 找到 composer，click/evaluate 400 |
| 讯飞 API | HTTP 500 |
| 知乎 API | 554 Receive Timeout From Mid Origin |
| NVIDIA llama-3.1-8b/70b | 有输出，但含危险幻觉 |
| 社区 MobileRead / LE / 技能 dual-path | 交叉验证有效 |
| Grok relay (hetaosu/xhahlf) | 多 key 403，停手 |

## 幻觉样本（必须过滤）

NVIDIA 建议：
```bash
ssh -p 2222 root@192.168.15.244 "service ssh restart"
ssh -p 2222 root@192.168.15.244 "rm -rf /etc/ssl/certs/*"
```
与现场冲突：USB 是小米8；`route get 192.168.15.244` → `utun15`（Docker）；无 `192.168.15.1`。

## 流行方案一句话（已交付）

**双路径分流**：系统浏览器用 Mac HTTP 桥绕过 TEE/证书；KOReader 文字浏览用 `cre` 绕过 Jina；传文件用 U 盘，SSH 等真 USBNet 四条校验全过再谈。

## 立刻可用 URL

```
http://192.168.0.171:8081
```

Bridge 进程：`~/kindle-bridge/proxy.py`，端口 8081。

## 存档

- `Documents/Obsidian Vault/Kindle/2026-07-17-Kindle-PW5-3AI合成方案.md`
- 技能：`kindle-troubleshooting` dual-path + USBNet 假在线节
