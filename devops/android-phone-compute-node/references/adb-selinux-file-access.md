# ADB Shell & SELinux: 读写 Termux App 数据目录的约束模式

## 场景

通过 ADB shell 从 Mac 管理 Android 设备上的 Termux 环境（金同学/Mi8, Magisk root）。Termux 的数据目录在 `/data/data/com.termux/files/home/`，受 SELinux 保护。

## 各命令效果对照

| 操作 | 命令 | 结果 |
|------|------|------|
| **读取** 任何文件 | `su 0 sh -c 'cat ...'` | ✅ 成功（magisk context 可读） |
| **写入** root 拥有的文件 | `su 0 sh -c 'cat > ... || echo > ...'` | ✅ 成功 |
| **写入** u0_a192 拥有的文件 | `su 0 sh -c 'echo > ...'` | ❌ Permission denied（SELinux 阻止） |
| **写入** app-owned 文件 | `run-as com.termux cp /tmp/src /data/data/.../dest` | ✅ 成功 |
| **执行** Termux 二进制 | `run-as com.termux /data/data/.../usr/bin/python3 ...` | ❌ Permission denied / inaccessible |
| **执行** python3 (root) | `su 0 sh -c 'env HOME=... PATH=... python3 ...'` | ✅ 成功 |
| **后台进程** (root) | `su 0 sh -c 'env ... nohup python3 ... &'` | ✅ 成功 |

## 模式总结

```
读取文件:          su 0 sh -c 'cat <path>'
写 root-owned 文件: su 0 sh -c 'cat > <path>'
写 app-owned 文件:  echo "..." > /data/local/tmp/tmpfile && run-as com.termux cp /data/local/tmp/tmpfile <app-path>
启动 gateway/agent: su 0 sh -c 'env HOME=... HERMES_HOME=... PATH=... nohup python3 -m hermes_cli.main gateway run --force -v > /tmp/log 2>&1 &'
```

## 实战记录（金同学 Mi8, July 2026）

- config.yaml (`/data/data/com.termux/files/home/.hermes/config.yaml`) 由 u0_a192 拥有：无法通过 su 0 直接覆盖，需走 `run-as com.termux cp`
- `.bashrc` 由 root 拥有（因之前用 su 0 写入）：可以直接 su 0 覆盖
- 日志文件需要写到 `/data/local/tmp/` 而非 Termux 数据目录，因为 gateway 进程以 root 运行无法创建 app 目录下的文件
