# 五行舰队 · Agent Mail 会话快照

日期：2026-07-18（水同学闭环 + 木邮箱决策后更新）

## 绑定（已验证）

| 同学 | 邮箱 | 设备 | 状态 |
|------|------|------|------|
| 土 | chan8927@agent.qq.com | Mac | ✅ OAuth；macOS keychain；可对 `angelife.t@gmail.com` 发简报并收回复 |
| 水 | chan1526@agent.qq.com | Mi6 `ca00a222` debian chroot | ✅ CLI 1.0.10 linux-arm64；encrypted file keychain；`shui-mail` 包装；收信「接入成功」 |

官方限制：同机只能 1 身份 → 土/水必须分设备。  
配额约 **2 邮箱/微信账号 → 土+水已满**。

## 木同学（明确不做独立 Agent Mail）

- 形态：QwenPaw 云端，非本机 Hermes
- 远程指挥：**已有** `mu`（OpenBridge → Chrome 对话页）
- 邮箱：额度满 + 无 shell 装 agently-cli；且**邮箱≠控制权**
- 能力边界见 skill `mu-qwenpaw-fleet` / `references/capability-audit-2026-07-18.md`

## 水同学闭环路径（实操）

1. Mac `npm pack` 元包 + `agently-cli-linux-arm64`
2. `adb push` → chroot `/tmp`，**安装脚本文件化**（避免嵌套引号）
3. `HOME=/root` + `npm install -g`（先 arm64 后主包）
4. `adb reverse tcp:10808` + chroot 代理
5. `auth login` 拿 device OAuth URL → OpenBridge 打开已登录 agent.qq.com 完成授权
6. `+me` / `message +list` 验收；wrapper：`/usr/local/bin/shui-mail`

## 管理端

- OpenBridge 操作 `https://agent.qq.com`
- 侧栏「管理邮箱地址」→「新建邮箱地址」
- 金/火再开邮箱：需**新微信账号或提额** + **独立设备**，禁止在 Mac 上二次 login 覆盖土 token

## Mac / 水技术点

- 元包 alone 不够，需平台包（darwin-x64 / linux-arm64）
- token 约 1h，可 `auth refresh`
- 发信：`--body-file ./x.html`（相对路径）；两阶段 `ctk_*`
- 用户常用收件箱：`angelife.t@gmail.com`（双向已通）

## 存档

- `土同学工作档案/Agent-Mail-水同学接入-20260718.md`

## 用户决策

- 先开两个：土 + 水（非全员）
- 土 chan8927 / 水 chan1526
- 木：先能力盘点；远程指挥走 `mu`，不优先开邮箱
