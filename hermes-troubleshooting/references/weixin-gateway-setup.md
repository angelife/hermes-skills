# Hermes Gateway WeChat 设置流程

通过 `hermes gateway setup` 交互式向导添加 WeChat 适配器。

## 前置条件
- Hermes Gateway 已安装运行
- `pip install aiohttp cryptography`
- 一个可用的个人微信账号

## 步骤

1. **启动向导**：`hermes gateway setup`（必须在 PTY 模式下运行）
2. **选择 WeChat**：在编号列表中 Weixin/WeChat 是第 3 项，用 `process submit` 发送 `3`
3. **确认扫码**：提示 "Start QR login now? [Y/n]" — 发送 `Y`
4. **获取二维码 URL**：从进程日志中提取类似 `https://liteapp.weixin.qq.com/q/7GiQu1?qrcode=xxx&bot_type=3` 的链接
5. **用户扫码**：将链接发给用户在微信中打开，扫码确认
6. **凭证保存**：成功登录后 `account_id` 和 `token` 自动保存到 `~/.hermes/.env`

## 二维码生命周期

- 有效期约 2 分钟
- 过期后无法刷新，必须杀死进程（`process kill`）重新运行向导
- 每次重新运行会生成新的二维码 URL

## 已知限制

- WeChat 适配器使用腾讯 iLink Bot API（机器人身份），不是个人微信号
- 群聊消息通常收不到（iLink 限制）
- 仅私聊（DM）可靠工作
- 相比 Telegram/Discord，WeChat 适配器的功能集受限

## 故障排查

| 症状 | 原因 | 解决 |
|------|------|------|
| "database disk image is malformed" 查询失败 | SQLCipher WHERE/ORDER BY/DESC 触发编译 bug | Python 子进程 ASC 全量输出 + Python 层过滤 |
| 二维码过期 | 二维码有效期约 2 分钟 | 重启向导生成新码 |
| iLink POST HTTP 4xx/5xx | Token 失效或网络问题 | 重新运行向导扫码 |
