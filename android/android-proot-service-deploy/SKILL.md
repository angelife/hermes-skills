---
name: android-proot-service-deploy
description: 将服务部署到 Android 的 proot Linux 容器中直接运行。用于解决 pacman 不可用/签名卡死时的兜底路径，以及系统服务在 proot 中“看起来启动了其实没监听”的问题。技能提供静态包获取、压包解包到 rootfs、前台/后台运行、宿主机到容器内的服务可达性验证方法。
tags: [android, proot, server, services]
---

# Android proot Service Deploy

## When to Use
- Android 已 Root，已有 proot 容器，但 pacman/GPGME 无法走通
- 目标不是完整系统，而是跑几个常驻服务（AList / aria2 / nginx / httpd / sshd / aliyundrive / 等）
- 设备只有蜂窝或单根 USB 做 ADB，不希望依赖用户手动在手机上操作安装

## Rootfs Choice Rule
不要默认把现有容器换成 Debian/Ubuntu，也不要因为在 chroot 里一次报 `/dev/null` 缺失就立刻切 proot。Mi6 的经验表明：很多时候是 `/dev` 目录不存在、bind 目标错误，或没有先挂载 `/proc /sys`；真正的 chroot 前置条件没满足，不等于内核限制。正确顺序是：
1. `getenforce` 或读取 SELinux enforcing 状态
2. `mount | grep <rootfs>` 确认 bind 挂上了
3. 宿主机 `ls -l <rootfs>/dev/null` 验证
4. chroot 内 `ls -l /dev/null`
只有上述都做完后仍缺 `/dev/zero /dev/urandom`，才记录“本设备 chroot 不可行”并切 proot。Debian proot 只有在“按最小 Linux userland 装且后续走 apt”时才可能更稳；在 Android + Magisk + proot 里，Debian 同样会遇到 DNS、GPGME、网络栈差异问题。切换 rootfs 只有在以下条件都满足时才值得做：用户明确要求、宿主机带宽充足、且切换后目标服务栈明显更容易跑起来。否则应继续在当前 chroot 里走正式 Linux 环境。

## Core Architecture
Android host → Magisk Root → proot static binary → Linux rootfs → services

## Prefer Static Binaries First
在 proot 容器里优先用静态或近似静态的二进制包，不要死磕 host-side 的 package manager。常见来源：

- GitHub Releases 最新版：`https://github.com/<owner>/<repo>/releases/latest/download/<asset>`
- `mirror.archlinuxarm.org` 的 `extra/` `community/` 目录可直接拿跨运行时的 `.pkg.tar.zst`
- 清华大学 tuna `github-release` 镜像若 404，试 `npmmirror`、原始 GitHub、其他镜像站点按顺序回退

## Deployment Path Convention
- 机器原生解压包进宿主机可直接访问的 rootfs 路径：`/data/local/tmp/arch/opt/services/<name>/`
- 运行方式是 `/data/local/tmp/proot-arm64 -r /data/local/tmp/arch <绝对 guest 路径>`，不要依赖 `$PATH`、当前目录或 `--force-bin-dir` 默认寻址
- 数据目录与日志目录在同目录下的 `data/`、`logs/`

## Running / Daemonizing Pattern
proot + 无 systemd 时不能用 systemctl。可靠做法：

1. 建立独立日志目录
2. 前台启动验证
3. 选项 A：使用项目自带的 daemon 子命令
4. 选项 B：使用 `(服务 &)` 放到 proot shell 里悬空或使用 `nohup`/`setsid` 让父级 proot 正常退出

示例通用运行模式：

```
/data/local/tmp/proot-arm64 \
  -r /data/local/tmp/arch \
  /bin/bash -lc '
    export HOME=/root
    cd /opt/services/alist
    /opt/services/alist/alist server >> /opt/services/alist/logs/alist.log 2>&1
  '
```

## Verification Pattern
必须按三层验证，不能只执行主命令就认为成功：

1. Binary check
   ```
   /data/local/tmp/proot-arm64 -r /data/local/tmp/arch /opt/services/alist/alist version
   ```
2. Inside-container localhost check
   ```
   /data/local/tmp/proot-arm64 -r /data/local/tmp/arch /bin/bash -lc 'curl -I -sS --max-time 5 http://127.0.0.1:5244'
   ```
3. Host/device outside check（这步最容易被跳过）
   - 把服务 bind 到容器内 0.0.0.0 可访问
   - 从另一个 proot shell 或宿主机访问 `http://<device_ip>:<port>`

## Known Pitfalls

| ID | Symptom | Fix |
|---|---|---|
| P1 | `start --force-bin-dir` 后 port 不通 | 该子命令有时是 silent start 但未落盘；用带日志的前台模式或 daemon 子命令 |
| P2 | 包内 tar 时 `Child died with signal 11` | 常是 tar 版本/参数/runner 不一致；直接使用绝对路径 tar 并确保 `cd` 到 guest 内目录 |
| P3 | `tar` 文件在 guest 和 host 里混淆 | 明确写绝对路径或先 `cd` 到正确目录；不要混合 host tar 和 guest tar |
| P4 | GitHub 下载时 SSL 断开 | 换镜像站点后再一圈请求；不要以为镜像不可用就放弃 |
| P5 | `127.0.0.1` 通但手机 IP 不通 | 优先查服务是否真的 bind 到 `0.0.0.0`；再查 ADB over TCP 端口转发/防火墙 |
| P6 | 服务可达性诊断顺序错乱 | **必须先做本地 self-test**：`adb shell curl -I http://127.0.0.1:<port>/`，再做 `curl -I http://<device_ip>:<port>/`。只有本机都通了，才排查 Mac→手机路径。跳过这一步会误把“服务未启动/未绑定”判断成“路由器/防火墙问题”。 |
| P7 | Alist 503 / 密码不对 | 首次启动才打印初始 admin 密码，之后只存哈希不可逆。若 `data/config.json` 不存在或首次启动被中断，会出现 503。必须在前台启动日志里抓 `initial password is:`，并立即改密码。 |
| P8 | proot + debian apt `socket (13: Permission denied)` | 根因是 `apt >=1.5` 的 `_apt sandbox` 降权与 proot ptrace 伪造 uid 不兼容，不是 DNS/权限/挂载。一行绕过：`apt update -o APT::Sandbox::User=root`，或写入 `/etc/apt/apt.conf.d/99no-sandbox`。更稳的是换真 chroot。 |

## Minimal AList Example
1. 下载
   ```
   curl -fL -o /data/local/tmp/arch/opt/services/alist.tar.gz https://github.com/AlistGo/alist/releases/latest/download/alist-linux-arm64.tar.gz
   ```
2. 解压
   ```
   mkdir -p /data/local/tmp/arch/opt/services/alist
   tar -xzf ... -C /data/local/tmp/arch/opt/services/alist
   ```
3. 运行
   ```
   /data/local/tmp/proot-arm64 -r /data/local/tmp/arch /opt/services/alist/alist server --force-bin-dir
   ```
4. 取初始密码
   ```
   /data/local/tmp/proot-arm64 -r /data/local/tmp/arch /opt/services/alist/alist admin
   ```

## Workflow for User’s Preferred Directness
- 默认操作；不要每步开头汇报“我先确认”。
- 可并行执行无关检查与下载
- 只在确认性失败持续时报告阻塞；不为了安全兜底而反复征得同意
- 结果只报告三层验证中的失败层，其余默认通过

## 上游参考资料
- `references/proot-alist-dropbox.md`：压包失败及 GitHub/镜像回退记录
- `references/proot-path-caveats.md`：proot 绝对路径 + daemon 注意事项
