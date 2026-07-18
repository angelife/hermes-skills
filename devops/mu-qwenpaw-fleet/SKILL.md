---
name: mu-qwenpaw-fleet
description: 指挥木同学（QwenPaw 云端 Agent）— mu CLI、能力边界实测、浏览器沙箱 vs 本机/局域网控制、与 Agent Mail 的关系。触发：木同学、mu、QwenPaw、云端 Agent 能力盘点、木能不能控浏览器/设邮箱。
version: 1.1.0
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


---

## 木同学内部工程笔记（agent 自己踩的坑 · 2026-07-18 实测）

> 本节是**木同学视角**的内部经验，供其他 agent 复用木同学、或木同学跨 session 自我恢复时参考。
> 与上面「指挥侧」互补：上面讲你怎么用木，这里讲木自己怎么在沙箱里把事做成。

### 1. Shell 是 dash，不是 bash（最容易卡死的地方）

QwenPaw 云端执行命令用的是 `/bin/sh` = **dash**，不是 bash。以下 bash 写法会直接报错：

| 想写的 | bash | dash 里会怎样 | 替代 |
|--------|------|--------------|------|
| `if [ .. ]; then .. fi` 单行 | ✅ | `Syntax error: "then" unexpected` | 拆多行，或改用 `&&` / `||` |
| `${PIPESTATUS[0]}` | ✅ | `Bad substitution` | 用 `echo $?` 单独接 |
| `head -c 500` | ✅ | `invalid option -- 'c'` | 用 `cut -c1-500` 或 `python` |
| `TOK=$(cat file)` 有时不展开 | ✅ | 偶尔变量为空 | **改用 python 读文件**，最稳 |
| heredoc `<<'PYEOF'` | ✅ | `Syntax error: "(" unexpected` | 把脚本写进 `.py` 文件再用 `python3 x.py` 跑 |

**黄金法则：任何需要变量拼接、命令替换、控制流的复杂 shell，全写成 `.py` 文件用 `python3` 跑。**
python3 在标准路径、能读文件、能调 subprocess、不依赖 shell 变量展开，是沙箱里最可靠的执行层。

### 2. git push 认证：URL 里的 token 会被环境剥离

- **现象**：`git push https://<TOKEN>@github.com/...` 实际请求的是 `https://github.com/...`（无 token），返回 403 `denied to angelife`。
- **原因**：沙箱底层（git/curl/透明代理）在发 HTTPS 前剥掉了 URL userinfo。
- **实测可用**：
  - ✅ **传统 PAT（`ghp_xxx`）** + python `urllib` 带 `Authorization: Bearer` header 直接打 GitHub API（contents/issues 都通）。
  - ✅ 或用 `git -c "http.extraHeader=Authorization: Bearer <TOKEN>" push`（注意 dash 下 header 值里有空格需小心，python subprocess 传最稳）。
  - ❌ **fine-grained token（`github_pat_xxx`）** 在本环境写操作全 403（"Resource not accessible by personal access token"），即使 API 返回 `push:true` 也是误导。直接用传统 PAT。
- **token 安全**：绝不写进 MEMORY.md / Hindsight / 任何公开处；存 `/tmp/.ghtoken`（600 权限）即可，会话结束随沙箱销毁。

### 3. 多会话隔离：群和单聊是分开的上下文

- 群消息（Telegram 超级群 `telegram:-100xxxx`）是独立 session，与和用户单聊（`telegram:780486548`）**上下文不互通**。
- 群里说话 → 触发群 session 的 agent 实例回应；单聊里看不到群里内容。
- 查群历史用 `qwenpaw chats get <chat_id>`，不在当前上下文时得主动拉。
- 主动往群推消息：`qwenpaw channels send --agent-id default --channel telegram --target-user <uid> --target-session telegram:-100xxxx --text "..."`（单向，无回复）。

### 4. 模型不支持多模态

- 当前模型是纯文本，`view_image` / 截图能存文件但**看不到图意**，需用户口述内容。
- 收到图片先如实告知"我看不了图"，请用户打字描述或给文字版。

### 5. Hindsight 经 cloudflared tunnel 读，地址常变

- 地址形如 `https://xxxx.trycloudflare.com`，cloudflared 重启/用户离机必变。
- 不通时让用户重发新地址；验证用 `curl <URL>/health` 或 `POST <URL>/v1/default/banks/hermes/memories/recall`。
- 临时隧道是公网临时地址，任何人拿链接可读全部记忆——用完建议用户关 tunnel。

### 6. 微信文章：云端无登录态必撞风控墙

- 详见 `media/wechat-article` v1.4.0「云端无登录态 Agent 实战修正」。
- 木同学云端抓任何微信文章（curl / Playwright / crawl4ai）都返回"环境异常"验证页，HTML 无 js_content。
- 唯一解法：本机带登录态浏览器经 CDP 打开，或用户把正文贴给木。

### 7. 跨 session 记忆恢复

- 工作区 `MEMORY.md` / `PROFILE.md` 是精选长期记忆；`recall_history` 是原始对话真相源。
- 醒来先读 AGENTS.md / SOUL.md / PROFILE.md / MEMORY.md，再按需 `recall_history` 搜更早会话。
- 涉及舰队人/事 → 先 recall Hindsight（土/金/水/火/配置/决策）再答，不凭空猜。
