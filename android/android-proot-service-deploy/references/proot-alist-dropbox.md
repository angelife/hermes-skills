# proot + alist 压包失败及 GitHub/镜像回退记录

## 环境
- 宿主：Mi8 / dipper / Magisk Root / ADB over TCP `192.168.1.26:5555`
- proot 二进制：`/data/local/tmp/proot-arm64`
- Arch rootfs：`/data/local/tmp/arch`

## 现象 1：`tar -xzf alist.tar.gz` 报 `Child died with signal 11`
- 原因：压包文件本身正常（gzip -t / file 均通过），但容器内 tar 子进程直接 segfault
- 修复：不要用 `cd` 到 guest 目录后再 `tar -xzf`；改成在 host/shell 层先 `cd /data/local/tmp/arch/opt/services/alist && tar -xzf alist.tar.gz -C .`，或解压到独立子目录

## 现象 2：GitHub 下载不稳定
- `curl -fL https://github.com/AlistGo/alist/releases/latest/download/alist-linux-arm64.tar.gz` 成功（~40MB）
- `curl -fL https://github.com/aria2/aria2/releases/download/release-1.37.0/aria2-1.37.0-linux-arm64.tar.gz` 多次失败：先 EOF/SSL 错误，再 connection timed out
- 已验证不可用：
  - `github.moeyy.xyz`（容器内 DNS 不通）
  - `https://mirrors.tuna.tsinghua.edu.cn/github-release/aria2/aria2/`（404）
  - `https://cdn.npmmirror.com/binaries/aria2/`（404）
- 已成功镜像源：
  - `http://dl.fedoraproject.org/pub/epel/8/Everything/aarch64/aria2/aria2-1.36.0-1.el8.aarch64.rpm`（302，但最终返回 HTML 非 rpm；aria2 RPM 路径在该站点不通）
  - `https://github.com/aria2/aria2/releases/expanded_assets/release-1.37.0` 直连超时

## 做法
1. 先走 GitHub 直连
2. 失败后回退 tuna github-release、npmmirror cdn
3. 最后回退到宿主 Mac 先下载、再 `adb push`，避免在 Mi8 蜂窝上重复浪费流量

## 教训
不要连续同一 URL 重试超过 2 次；换源或 delegate 到宿主机都比继续阻塞有效。
