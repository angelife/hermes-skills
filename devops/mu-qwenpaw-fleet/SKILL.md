---
name: mu-qwenpaw-fleet
description: 指挥木同学（QwenPaw 云端 Agent）— mu CLI、能力边界实测、浏览器沙箱 vs 本机/局域网控制、与 Agent Mail 的关系。触发：木同学、mu、QwenPaw、云端 Agent 能力盘点、木能不能控浏览器/设邮箱。
version: 1.0.0
tags: [mu, qwenpaw, 木同学, fleet, openbridge, cloud-agent]
---

# 木同学 · 云端执行节点（mu / QwenPaw）

木是 **QwenPaw 云端网页 Agent**，不是 Hermes 本机/chroot 实例。指挥通道是 Mac 上的 `mu` CLI（经 OpenBridge 往 Chrome 里 QwenPaw 对话页塞消息）。

## 何时用

- 用户问「木同学能做什么 / 能不能控浏览器 / 能不能设邮箱」
- 用 `mu` 下任务、探活、能力盘点
- 区分「远程指挥」与「Agent 邮箱 / 本机控制」

## 指挥入口（已有）

```bash
mu status          # OpenBridge + 木标签页是否在线
mu "任务内容"       # 发送并等回复
mu send "任务"      # 只发不等
mu read            # 读当前页最新正文
mu config          # ~/.config/mu/config.json
```

- 脚本：`~/.local/bin/mu`
- 依赖：OpenBridge `:10088` + Chrome 已开 QwenPaw chat 标签
- 前缀默认 `[土同学] `

**探活/盘点**：先 `mu status`，再发**编号清单式**问题（要求分点、禁寒暄），`mu read` 截最新段。长任务用 `mu send` + 稍后 `mu read`，避免等回复超时截断。

## 排障：木同学不说话了

用户反馈「木同学刚才还说话突然不说了」时：

1. `mu status` — 确认 OpenBridge + 标签页是否在线
2. `mu read` — 看木同学最后在做什么（可能正在跑长任务：cloudflared tunnel、wechat-reader 实测、脚本执行等）
3. `mu "ping"` — 戳一下看是否响应（发简短指令如 `ping`）
4. 如果 ping 有回复但内容显示木同学在跑长任务 → 等它跑完，或发新指令打断

**常见原因：** 木同学在执行长任务（cloudflared tunnel 建隧道、wechat-reader 实测、Git clone + 依赖安装、脚本执行）时，不会中断当前任务回复新消息。需要等它跑完，或发新指令让它切换上下文。

**QwenPaw session 过期：** `mu status` 显示 `访问链接已失效 - AgentScope Platform` 或 URL 指向 `/login` 而非 `/chat/xxx`，说明 QwenPaw 的网页 session 过期了（通常 2-4 小时无活动后自动登出）。**无法远程重新登录**——需要用户手动在 Chrome 标签页中重新登录 QwenPaw 平台。木同学 session 过期不表示能力出问题，只是登录态掉了，重登即可恢复。

## 能力边界（2026-07-18 实测，以实测为准）

| 能力 | 结果 |
|------|------|
| 浏览器 | ✅ `browser_use`（Playwright Chromium）：navigate/click/type/fill_form/screenshot/snapshot/cookies/connect_cdp 等 |
| 浏览器位置 | **云端沙箱**，不是用户本机 Chrome |
| 外网 | ✅ |
| 局域网 `192.168.x` | ❌ 沙箱隔离 |
| 工作区文件 | ✅ 云端 NAS 路径可读写 |
| Shell/脚本 | ✅ |
| 文档 | ✅ Word/PDF/Excel/PPT |
| 多 Agent / cron | ✅ 可派子任务、定时唤醒 |
| 邮件 | ❌ 未接入（himalaya 框架有，二进制与账号未配） |
| 看图 | ❌ 纯文本；截图可存，图意需用户说 |
| 常驻 | ❌ 按需唤醒；「盯着」只能 cron 周期跑 |

### 一句话定位

**木 = 云端外网执行节点（浏览器自动化 + 文件 + 脚本）**  
**不是** 本机/局域网控制面。  
本机 → 土；手机 ADB → 金/水。

## 常见误解（必纠）

1. **「能控浏览器」≠ 控用户电脑** — 控的是云端 Chromium。
2. **「设邮箱 = 远程控制」≠** — 邮箱是消息通道；远程指挥木已有 `mu`，不依赖邮箱。
3. **给木开 QQ Agent Mail 独立身份** — 当前账号约 **2 邮箱已满**（土+水）；且木无本机 shell，**装不了 agently-cli 做 OAuth 宿主**。若要独立邮箱：新微信账号/提额 + **独立设备** 跑 CLI，或云端配 IMAP/SMTP（公网邮箱），仍进不了局域网。
4. **别用木访问 New API / Hindsight / 舰桥 / ADB** — 它到不了 `192.168.x`。

## 适合派给木的任务

- 公网站登录/填表/抓数/下报表（外网）
- 云端工作区写脚本、跑批、沉淀 skill
- 定时外网巡检（cron）
- 需要浏览器多步交互且不碰内网的活

## 不要派给木的任务

- 本机文件、Docker、v2rayN、本机 Chrome（除非用户主动开 CDP 并 bridge）
- 局域网服务、手机 ADB、金/水 chroot
- 把邮箱当「控权」捷径

## 与 Agent Mail 的关系

见 `agent-mail-fleet`：配额、分设备、两阶段发信。  
木侧：**先问有没有用** → 远程指挥用 `mu`；独立邮箱 ROI 低（额度满 + 无本机 CLI + 非控制面）。

## 参考

- `references/capability-audit-2026-07-18.md` — 能力盘点问答与边界表
- `references/agent-mail-vs-remote-control.md` — 邮箱≠远程控制决策卡
- Agent Mail：skill `agent-mail-fleet`
