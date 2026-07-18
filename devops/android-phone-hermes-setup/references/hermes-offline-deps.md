# Hermes 离线依赖清单（Termux aarch64）

从 Mac (x86_64, Python 3.13) venv 通过 pip install hermes 后提取的依赖树。

## 核心依赖（全部 pure Python，可从 venv site-packages 直接打包）

```
hermes==0.9.1
annotated-types==0.7.0
attrs==26.1.0
cachetools==7.1.4
certifi==2026.6.17
cffconvert==2.0.0
charset-normalizer==3.4.7 (有 pure wheel, 但有 .so 兜底)
click==8.4.2
docopt==0.6.2
frozendict==2.4.7
idna==3.18
jsonschema==3.2.0
oauthlib==3.3.1
pycparser==3.0
pydantic==2.13.4
pydantic-settings==2.14.2
pykwalify==1.8.0
pyld==2.0.4
pyparsing==3.3.2
pyrsistent==0.20.0
python-dateutil==2.9.0.post0
python-dotenv==1.2.2
requests==2.34.2
requests-oauthlib==2.0.0
ruamel.yaml==0.17.40 (pure, 但 ruamel.yaml.clib 是 C 扩展)
six==1.17.0
toml==0.10.2
typing-extensions==4.15.0
typing-inspection==0.4.2
urllib3==2.7.0
```

## C 扩展依赖（需要单独处理）

| 包 | 版本 | 处理方式 |
|---|---|---|
| pydantic-core | 2.46.3 | 用 [Eutalix/android-pydantic-core](https://github.com/Eutalix/android-pydantic-core) 的预编译 wheel |
| PyNaCl | 1.6.2 | Hermes 核心不需要（telegram/discord 功能可选） |
| lxml | 6.1.1 | cffconvert 需要，但 Hermes 核心不用 |
| cffi | 2.0.0 | PyNaCl 的依赖，hermes core 不需要 |
| charset-normalizer | 3.4.7 | 有 pure fallback wheel (py3-none-any)，直接用 wheel 安装 |
| ruamel.yaml.clib | — | ruamel.yaml 有 pure fallback（纯 Python 模式），不用 .clib |

## Python 环境（Termux .deb）

通过 root shell + HTTP proxy 从清华源下载：

```
https://mirrors.tuna.tsinghua.edu.cn/termux/apt/termux-main/

# 包列表：
python_3.13.13-1_aarch64.deb             # 4.3MB
python-pip_26.1.2_all.deb                # 1.1MB
gdbm_1.26-1_aarch64.deb                  # 147KB
libandroid-posix-semaphore_0.1-4_aarch64.deb
libandroid-support_29-1_aarch64.deb
libbz2_1.0.8-8_aarch64.deb
libcrypt_0.2-6_aarch64.deb
libexpat_2.8.2_aarch64.deb
libffi_3.5.2_aarch64.deb
liblzma_5.8.3_aarch64.deb
libsqlite_3.53.2_aarch64.deb
ncurses_6.6.20260307+really6.5.20250830_aarch64.deb
ncurses-ui-libs_6.6.20260307+really6.5.20250830_aarch64.deb
openssl_1:3.6.3_aarch64.deb
readline_8.3.3_aarch64.deb
zlib_1.3.2_aarch64.deb
```

## pydantic 版本兼容性

关键：Android 预编译 pydantic-core 最高 2.46.3。pydantic 2.13.x 要求 >=2.46.4。

**方案 A**：在 Mac venv 装 pydantic 2.10.x（兼容 pydantic-core 2.46.3）后重新打包

**方案 B**：绕过版本检查
```python
# 注释掉 pydantic/version.py 中第 94 行的 raise
```

建议方案 A，因为方案 B 可能有 API 不兼容（_migration.py import 失败）。