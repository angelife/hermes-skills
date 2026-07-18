# ADB Reverse + SOCKS5 代理 — 给离线 Android chroot 容器上网

## 场景

chroot 容器无公网（WiFi 不可用 / 纯 cellular 无 IPv4 / 无外网路由），
但仍需从 chroot 内访问互联网（npm/git/OAuth/API）。

典型场景：为水同学（Mi6）在 chroot 里安装 npm 包 / 跑 OAuth login，
而手机本身没有可路由的外部 IP。

## 架构

```
Mac (hermes agent)
  ├─ :10808 (v2rayN SOCKS5 代理 — 有公网出口)
  │
  ├─ ADB reverse tcp:10808 tcp:10808
  │     (Mac 的 10808 端口通过 ADB 映射到 Android 的 127.0.0.1:10808)
  │
  └─ adb -s <serial> shell su 0 chroot /data/... /bin/bash
       └─ export HTTPS_PROXY=socks5h://127.0.0.1:10808
          └─ curl / npm / agently-cli 等走代理出去
```

## 步骤

### 1. Mac 侧 — 确认代理 + 建 ADB reverse

```bash
# 确认代理在监听
lsof -nP -iTCP:10808 -sTCP:LISTEN

# 建 reverse（已存在会自动跳过或报 port already forward）
adb -s <serial> reverse tcp:10808 tcp:10808

# 验证
adb -s <serial> reverse --list
# → UsbFfs tcp:10808 tcp:10808
```

### 2. chroot 侧 — 设代理 env 后再操作

```bash
chroot /data/local/tmp/chroot/<distro> /bin/bash -l
export HTTP_PROXY=socks5h://127.0.0.1:10808
export HTTPS_PROXY=socks5h://127.0.0.1:10808
export ALL_PROXY=socks5h://127.0.0.1:10808
export http_proxy=$HTTP_PROXY
export https_proxy=$HTTPS_PROXY
export all_proxy=$ALL_PROXY

# 测通
curl -sS -m10 -o /dev/null -w '%{http_code}' https://auth.agent.qq.com/
# → 301 或 200（非超时）= 代理通
```

### 3. 把命令嵌成单行（适合从 Mac 侧 adb shell 单条执行）

```bash
adb -s <serial> shell "su 0 -c '
export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
export HTTP_PROXY=socks5h://127.0.0.1:10808
export HTTPS_PROXY=socks5h://127.0.0.1:10808
export ALL_PROXY=socks5h://127.0.0.1:10808
timeout 25 agently-cli auth login > /tmp/auth.out 2>&1 &
sleep 12
cat /tmp/auth.out
'"
```

## pitfall

| 问题 | 表现 | 修复 |
|------|------|------|
| ADB reverse 冲突 | `adb: error: cannot reverse tcp:10808 tcp:10808: port already forward` | 先删旧的：`adb -s <serial> reverse --remove tcp:10808` 再建 |
| DNS 解析绕不开代理 | `curl: (6) Could not resolve host` | 用 `socks5h://`（h=hostname 也走代理），不用 `socks5://` |
| 代理被 .env 覆盖 | chroot 内 Hermes 启动后 `HTTP_PROXY` 被 `/root/.hermes/.env` 写死 | 不要在 chroot 的 .env 里写代理，或确保与 ADB reverse 的地址一致 |
| chroot /etc/resolv.conf 是 symlink 到 systemd-resolved | `No such file or directory` | 删掉 symlink，写纯文本 `/etc/resolv.conf`：`nameserver 8.8.8.8` |

## 典型成功输出

```
# curl 验证
proxy:301

# agently-cli auth login
请点击以下链接登录并授权邮箱：
https://agent.qq.com/page/oauth?oauth_type=device&user_code=uc_xxxxxxxxx
```