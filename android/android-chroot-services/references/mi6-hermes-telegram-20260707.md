# Mi6 Hermes Telegram 部署记录（2026-07-07）

## 已证实可行的组合
- rootfs：Mi8 chroot 直传到 Mi6 `/data/local/tmp/chroot/debian`
- chroot 修复：Magisk su 0 下 bind `/dev` 并确认 `/dev/null /dev/zero /dev/urandom` 可见
- Hermes：chroot 内 venv 安装 `hermes-agent==0.18.0`
- PTB：`python-telegram-bot==21.11.1` + `httpx==0.28.1`

## 关键故障链
1. `HTTPXRequest unexpected keyword httpx_kwargs` → PTB 20.8 与 Hermes 0.18.0 不匹配
2. 代理超时 → `.env` 里 `HTTP_PROXY/HTTPS_PROXY/SOCKS_PROXY` 写死 `192.168.50.98:10808`
3. 超时解决后出现 `telegram.error.InvalidToken` → token 被 Telegram 拒绝

## 已验证命令
- Hermes 环境变量检查：`grep -i proxy /proc/$(pidof hermes)/environ | tr '\0' '\n'`
- 代理可达性：`curl -o /dev/null -w "%{http_code} %{time_total}s\n" --max-time 10 -x socks5://192.168.1.8:10808 https://api.telegram.org`
- Hermes 进程检查：`ps -A | grep hermes | grep -v grep`

## 下次部署要做的
1. `.env` 里通写作 `192.168.1.8:10808`
2. PTB 最低不要低于 21.10
3. `.env` 修改后重起前必须确认 gateway.pid / gateway.lock 已清理
4. 只抓新日志后做消息收发验证
