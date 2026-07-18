# 木同学能力盘点 · 2026-07-18

经 `mu` 发送编号问题，要求分点禁寒暄后的**自述 + 其侧实测**（外网 curl 200 / `192.168.1.1` 不可达 / himalaya 未装）。

## 工具

- 浏览器：`browser_use` — start/open/navigate/click/type/screenshot/snapshot/fill_form/press_key/drag/hover/select_option/eval/console_messages/network_requests/pdf/cookies_*/connect_cdp/stop
- 系统 Chromium：`/usr/bin/chromium`（Playwright 管理）
- 可选：`browser_visible`、`browser_cdp`（连本机已开 CDP 的 Chrome，需用户侧放行）

## 资源

- 工作区：`/run/csi/mount-root/nas/.../workspaces/default`（可写）
- 外网：通
- 局域网：不通
- 邮件：himalaya skill 有、二进制无、账号无 → **未接入**

## 用户侧误判纠正

1. 「能控浏览器」→ 云端沙箱，非本机  
2. 「设邮箱=远程控制」→ 否；远程指挥已有 `mu`  
3. 独立 QQ Agent Mail → 当前 2 邮箱额度已满（土+水）；木也不是合适的 agently-cli 宿主  

## 指挥验收命令

```bash
mu status
mu send "【能力盘点-请只答这N点】...纯中文分点，不要寒暄。"
# 等 30–60s
mu read
```
