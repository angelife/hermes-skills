# proot 路径陷阱

## 关键：`/` 是 bind mount 到 Android `/`，不是容器 image
因此：
- 容器 `/opt/services/...` 实际落在宿主机的 `/data/local/tmp/arch/opt/services/...`
- 绝对路径 `/opt/services/alist/alist` 在 guest 内正确，但 host shell 的 `cd /opt/services` 会失败
- proot 命令内如果要重定向日志到 `/opt/services/...`，写法必须用绝对路径 + 先 `mkdir -p`

## 启动参数必须含 rootfs
不要试图直接执行 guest 二进制，必须显式 `-r /data/local/tmp/arch`
示例：
- 正确：`/data/local/tmp/proot-arm64 -r /data/local/tmp/arch /opt/services/alist/alist server --force-bin-dir`
- 错误：`/data/local/tmp/proot-arm64 -r /data/local/tmp/arch /data/local/tmp/arch/opt/services/alist/alist server`（proot 误算路径）

## `--force-bin-dir` 的副作用
某些 alist 版本中该参数会尝试以 bin 目录作为 data dir，可能访问到 `/usr/lib/data/config.json` 这类宿主路径。替代做法：
- 指定 `--data /opt/services/alist/data`
- 或用环境变量 `ALIST_HOME=/opt/services/alist/data`
- 或用 `cd` 到 bin 目录下，不带 `--force-bin-dir`

## 服务 bind 0.0.0.0 / port 公网可达
proot 容器内进程与宿主机共享 network namespace；`127.0.0.1:5244` 在容器里能通，不代表宿主机端口通。必须：
- 让服务 bind `0.0.0.0` 或宿主机 IP
- 从宿主另一 shell 或同一设备 IP 访问，验证 `192.168.1.26:5244`

## 压包 segfault
`tar -xzf ...` 在 proot 容器内的 tar 子进程有时 segfault。host shell 先 `cd` 再解压通常更稳。
