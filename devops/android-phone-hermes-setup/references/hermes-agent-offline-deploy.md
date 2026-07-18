# Hermes Agent 离线部署依赖（Termux aarch64）

## hermes-agent 0.17.0 包结构（重要变化）

**主入口不是 `hermes_agent`**，是 `hermes_cli` 扁平结构。`hermes_agent-0.17.0.dist-info/top_level.txt`：

```
acp_adapter, agent, batch_runner, cli, cron, gateway,
hermes_bootstrap, hermes_cli, hermes_constants, hermes_logging,
hermes_state, hermes_time, mcp_serve, model_tools, plugins,
providers, run_agent, tools, toolset_distributions, toolsets,
trajectory_compressor, tui_gateway, utils
```

所有模块扁平安装到 `site-packages/`，**无嵌套 `hermes_agent/` 目录**。

- ❌ `import hermes_agent` → `ModuleNotFoundError`
- ✅ `from hermes_cli import main` 或 `python3 -m hermes_cli.main`
- ✅ `import hermes_cli` → 正常

hermes-cli 二进制脚本：`/data/data/com.termux/files/usr/bin/hermes = hermes_cli.main:main` console_scripts 入口。

## 依赖树（hermes-agent 0.17.0）

```
hermes-agent 0.17.0
├── openai==2.24.0
├── httpx[socks]
├── rich==14.3.3
├── pyyaml==6.0.3
├── ruamel.yaml==0.18.17
├── pydantic==2.13.4  ← 需要 pydantic-core (C ext)
├── fastapi<1,>=0.104.0
├── uvicorn[standard]<1,>=0.24.0
├── python-multipart<1,>=0.0.9
├── ptyprocess<1,>=0.7.0
├── Pillow==12.2.0
├── python-telegram-bot[webhooks]  ← Telegram 消息平台
├── discord.py[voice]
├── aiohttp==3.13.4
├── slack-bolt / slack-sdk
├── croniter==6.0.0
├── PyJWT[crypto]
├── jinja2
├── tenacity
├── requests
├── packaging
└── psutil
```

## C 扩展依赖（需要特殊处理）

| 包 | 版本 | 处理 |
|---|---|---|
| pydantic-core | 2.46.x | [Eutalix/android-pydantic-core](https://github.com/Eutalix/android-pydantic-core) 预编译 aarch64 wheel |
| cryptography | — | Termux apt 安装，或删除（hermes 核心不需要，telegram 需要但可 mock） |

## Python 环境（Termux .deb 路径）

清华源：`https://mirrors.tuna.tsinghua.edu.cn/termux/apt/termux-main/`

路径格式：`pool/main/<首字母>/<包名>/<包名>_<版本>_aarch64.deb`

关键包（python 3.13.13）：
```
pool/main/p/python/python_3.13.13-1_aarch64.deb
pool/main/p/python-pip/python-pip_26.1.2_all.deb
pool/main/g/gdbm/gdbm_1.26-1_aarch64.deb
pool/main/liba/libandroid-posix-semaphore/libandroid-posix-semaphore_0.1-4_aarch64.deb
pool/main/liba/libandroid-support/libandroid-support_29-1_aarch64.deb
pool/main/libb/libbz2/libbz2_1.0.8-8_aarch64.deb
pool/main/libc/libcrypt/libcrypt_0.2-6_aarch64.deb
pool/main/libe/libexpat/libexpat_2.8.2_aarch64.deb
pool/main/libf/libffi/libffi_3.5.2-2_aarch64.deb
pool/main/libl/liblzma/liblzma_5.8.3-1_aarch64.deb
pool/main/libs/libsqlite/libsqlite_3.53.2-1_aarch64.deb
pool/main/n/ncurses/ncurses_6.6.20260307+really6.5.20250830_aarch64.deb
pool/main/n/ncurses-ui-libs/...
pool/main/o/openssl/openssl_1:3.6.3_aarch64.deb
pool/main/r/readline/readline_8.3.3-2_aarch64.deb
pool/main/z/zlib/zlib_1.3.2-1_aarch64.deb
```

## pydantic 版本兼容

Android 预编译 pydantic-core 最高 2.46.3。hermes-agent 0.17.0 的 pydantic 2.13.4 要求 `pydantic-core>=2.46.4`。

**方案 A**：在 Mac venv 用 pydantic 2.10.x 重新打包（兼容 pydantic-core 2.46.3）

**方案 B**：绕过版本检查（见 hermes-offline-install-method.md 中的 patch 方法）

## Termux apt 锁死处理

当后台 apt 进程持有 dpkg 锁导致 Termux pkg/apt 无法执行：

1. 找出锁进程：`adb shell "su -c 'cat /data/data/com.termux/files/usr/var/lib/dpkg/lock-frontend'"` → PID
2. root 杀进程：`adb shell "su -c 'kill -9 <PID>; killall apt apt-get dpkg 2>/dev/null'"`
3. 清锁文件：`adb shell "su -c 'rm -f /data/data/com.termux/files/usr/var/lib/dpkg/lock-frontend /data/data/com.termux/files/usr/var/lib/dpkg/lock /data/data/com.termux/files/usr/var/cache/apt/archives/lock'"`
4. 重试

注意：`run-as com.termux` 无法删除这些锁文件（权限不够），必须用 `su -c`。

## 完整离线部署流水线摘要

```
Mac: python3.13 venv → pip install hermes-agent
Mac: tar czf hermes-deps.tgz (exclude *.so, pip, setuptools, _distutils_hack)
Mac: adb push hermes-deps.tgz /sdcard/Download/
Mac: adb shell "su -c 'cp /sdcard/Download/hermes-deps.tgz /data/data/com.termux/files/home/; chown 10194:10194 ...'"
手机: su -c 'tar xzf ... -C $P/lib/python3.13/site-packages/'
手机: su -c 'curl -4sL -o /data/local/tmp/pydantic-core.whl https://github.com/...; unzip -qo ...'
手机: su -c 'echo \"#!/bin/bash...\" > /data/data/com.termux/files/usr/bin/hermes; chmod +x ...'
手机: hermes version
```

完整 Step-by-Step 见 `references/hermes-offline-install-method.md`