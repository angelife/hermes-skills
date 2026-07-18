# Hermes Offline Install on Android (No-Network Method)

## When to Use This Method

The phone has NO internet access (WiFi broken, no SIM, USB-C in device mode connected to Mac).
Termux `apt-get`/`pkg` cannot reach any mirror.
- macOS can't do RNDIS host (no kext on Apple Silicon)
- gnirehtet segfaults on macOS
- Termux user-space socker() blocked by SELinux

## Prerequisites

- ADB connection working
- Phone rooted (Magisk)
- Termux installed (with basic toolchain from initial APK)
- Mac has hermes in a Python 3.13 venv

## Architecture

```
Mac (x86_64 or ARM64)
  ├── mitmproxy HTTP CONNECT proxy (port 1080)
  ├── pip download / venv hermes   →  pure Python .tgz
  └── ADB reverse port 1080        →  phone root shell downloads .deb

Phone (aarch64, Termux)
  ├── root + proxy → curl .deb from mirror
  ├── Termux dpkg install python + pip
  └── tar xzf pure Python tgz → site-packages
```

## Step-by-Step

### 1. Start proxy on Mac

```bash
# If not installed
brew install mitmproxy

mitmdump --listen-port 1080 --mode regular &
# Verify
curl -x http://127.0.0.1:1080 --cacert ~/.mitmproxy/mitmproxy-ca-cert.pem -s https://ifconfig.me
```

### 2. ADB reverse

```bash
adb reverse tcp:1080 tcp:1080
```

### 3. Phone root downloads Termux .deb packages

```bash
# Install python + pip
adb shell su -c "
export http_proxy=http://127.0.0.1:1080
export https_proxy=http://127.0.0.1:1080
cd /data/local/tmp/termux_deps

# Download python .deb (from Tsinghua mirror — termux.dev domain may time out)
curl -sk --connect-timeout 30 -O https://mirrors.tuna.tsinghua.edu.cn/termux/apt/termux-main/pool/main/p/python/python_3.13.13-1_aarch64.deb

# Download dependencies
for deb_url in \\
  pool/main/g/gdbm/gdbm_1.26-1_aarch64.deb \\
  pool/main/liba/libandroid-posix-semaphore/libandroid-posix-semaphore_0.1-4_aarch64.deb \\
  pool/main/liba/libandroid-support/libandroid-support_29-1_aarch64.deb \\
  pool/main/libb/libbz2/libbz2_1.0.8-8_aarch64.deb \\
  pool/main/libc/libcrypt/libcrypt_0.2-6_aarch64.deb \\
  pool/main/libe/libexpat/libexpat_2.8.2_aarch64.deb \\
  pool/main/libf/libffi/libffi_3.5.2_aarch64.deb \\
  pool/main/libl/liblzma/liblzma_5.8.3_aarch64.deb \\
  pool/main/libs/libsqlite/libsqlite_3.53.2_aarch64.deb \\
  pool/main/n/ncurses/ncurses_6.6.20260307+really6.5.20250830_aarch64.deb \\
  pool/main/n/ncurses-ui-libs/ncurses-ui-libs_6.6.20260307+really6.5.20250830_aarch64.deb \\
  pool/main/o/openssl/openssl_1:3.6.3_aarch64.deb \\
  pool/main/r/readline/readline_8.3.3_aarch64.deb \\
  pool/main/z/zlib/zlib_1.3.2_aarch64.deb; do
  curl -sk --connect-timeout 30 -O https://mirrors.tuna.tsinghua.edu.cn/termux/apt/termux-main/\$deb_url
done
"
```

### 4. Install .deb files with Termux dpkg

```bash
P=/data/data/com.termux/files/usr
adb shell su -c "
export PATH=\$P/bin:/system/bin:/system/xbin
cd /data/local/tmp/termux_deps

# Install dependencies (dpkg must be run via run-as with explicit PATH)
run-as com.termux env PATH=\$P HOME=/data/data/com.termux/files/home \\
  \$P/dpkg -i gdbm_1.26-1_aarch64.deb libandroid-posix-semaphore_0.1-4_aarch64.deb ...
"
```

**Key dpkg wrinkle**: `run-as com.termux` doesn't inherit PATH. Always set it. For packages that prompt (openssl config), pipe yes:

```bash
run-as com.termux env PATH=\$P HOME=... \\
  \$P/bash -c "yes Y | \$P/dpkg --force-confnew -i openssl.deb"
```

### 5. Build pure-Python wheel set on Mac

Python 3.14 can't install hermes (requires <4.0.0,>=3.11). Use python3.13:

```bash
python3.13 -m venv /tmp/hermes-venv
/tmp/hermes-venv/bin/pip install hermes
```

### 6. Package and transfer pure Python

```bash
cd /tmp/hermes-venv/lib/python3.13/site-packages
tar czf /tmp/hermes-full-pure.tgz \\
  --exclude='*.so' --exclude='*.dylib' --exclude='*.abi3.so' \\
  --exclude='__pycache__' --exclude='pip' --exclude='setuptools' \\
  --exclude='_distutils_hack' \\
  .

# Push to phone (use /sdcard/Download/ as bridge, then chown)
adb push /tmp/hermes-full-pure.tgz /sdcard/Download/
adb shell "su -c '
cp /sdcard/Download/hermes-full-pure.tgz /data/data/com.termux/files/home/
chown 10194:10194 /data/data/com.termux/files/home/hermes-full-pure.tgz
'"
```

### 7. Install pydantic-core (C extension) as Android wheel

```bash
curl -sL "https://github.com/Eutalix/android-pydantic-core/releases/download/v2.46.3/pydantic_core-2.46.3-cp313-cp313-linux_aarch64.whl" \\
  -o /tmp/pydantic_core.aarch64.whl

adb push /tmp/pydantic_core.aarch64.whl /sdcard/Download/
adb shell "su -c '
cp /sdcard/Download/pydantic_core.aarch64.whl /data/local/tmp/
P=/data/data/com.termux/files/usr
cd \$P/lib/python3.13/site-packages
unzip -qo /data/local/tmp/pydantic_core.aarch64.whl
'"
```

### 8. Unpack pure Python on phone

```bash
adb shell "su -c '
P=/data/data/com.termux/files/usr
tar xzf /data/data/com.termux/files/home/hermes-full-pure.tgz \\
  -C \$P/lib/python3.13/site-packages/
'"
```

### 9. Patch pydantic version check (if needed)

Android pydantic-core wheel may be v2.46.3 while Mac venv's pydantic expects >=2.46.4:

```bash
adb shell "su -c '
P=/data/data/com.termux/files/usr
export PATH=\$P/bin:/system/bin:/system/xbin
python3 -c "
content = open(chr(34)*3 + chr(47) + chr(100) + ...
...
path = \"/data/data/com.termux/files/usr/lib/python3.13/site-packages/pydantic/version.py\"
content = open(path).read()
content = content.replace(\"raise SystemError(\", \"# raise SystemError(\")
open(path, \"w\").write(content)
print(111, 107)
"
'"
```

Better: write a patch script on Mac and push it:

```python
# /tmp/patch_pydantic.py
import sys
path = "/data/data/com.termux/files/usr/lib/python3.13/site-packages/pydantic/_internal/_core_utils.py"
with open(path) as f:
    content = f.read()
old = "from pydantic_core import validate_core_schema as _validate_core_schema"
new = "_validate_core_schema = lambda s: s  # bypass, not in pydantic_core v2.46.3"
content = content.replace(old, new)
with open(path, "w") as f:
    f.write(content)
print("ok")
```

```bash
adb push /tmp/patch_pydantic.py /sdcard/Download/
adb shell "su -c '
cp /sdcard/Download/patch_pydantic.py /data/local/tmp/
P=/data/data/com.termux/files/usr
export PATH=\$P/bin:/system/bin:/system/xbin
python3 /data/local/tmp/patch_pydantic.py
'"
```

### 10. Handle required C extensions that can't be installed

Hermes CLI entry point imports several modules that load C extensions:

| C extension | Required by | Impact if missing | Workaround |
|---|---|---|---|
| PyNaCl (nacl) | hermes/commands/init/util/connect_github.py | `hermes init` fails | Mock nacl package |
| lxml.etree | pyld (codemeta validator) | `hermes harvest codemeta` fails | Mock validate_codemeta.py |

**Mock nacl**:
```bash
adb shell "su -c '
P=/data/data/com.termux/files/usr
mkdir -p \$P/lib/python3.13/site-packages/nacl/bindings
mkdir -p \$P/lib/python3.13/site-packages/nacl/encoding
# Create mock files (see full content in session transcript)
'"
```

**Mock lxml-dependent codemeta validator**:
```bash
adb shell "su -c '
P=/data/data/com.termux/files/usr
cat > \$P/lib/python3.13/site-packages/hermes/commands/harvest/util/validate_codemeta.py << \"PYEOF\"
def validate_codemeta(json: dict) -> bool:
    return True
PYEOF
'"
```

**Disable plugin entry points** that trigger C extension import during CLI startup:
```bash
adb shell "su -c '
P=/data/data/com.termux/files/usr
cd \$P/lib/python3.13/site-packages/hermes-0.9.1.dist-info/
sed -i \"/^invenio=/s/^/# /\" entry_points.txt
sed -i \"/^invenio_rdm=/s/^/# /\" entry_points.txt
sed -i \"/^rodare=/s/^/# /\" entry_points.txt
sed -i \"/^codemeta=/s/^/# /\" entry_points.txt
sed -i \"/^cff=/s/^/# /\" entry_points.txt
'"
```

### 11. Verify

```bash
adb shell "su -c '
P=/data/data/com.termux/files/usr
export PATH=\$P/bin:/system/bin:/system/xbin
python3 -m hermes --help
python3 -m hermes version
'"
```

## Package Dependency Map

```
hermes 0.9.1
├── pydantic (pure) → pydantic-core (C ext — Android wheel)
├── cffconvert (pure) → ruamel.yaml, jsonschema
├── pykwalify (pure)
├── pyld (pure) → lxml (C ext — Termux python-lxml .deb)
├── PyNaCl (C ext — mockable)
├── requests (pure)
├── toml, click, docopt (pure)
└── pyparsing, frozendict, cachetools... (pure)
```

## Key Pitfalls

1. **清华源路径**：`/termux/apt/termux-main/pool/main/p/python/...` — 不是 `/termux/pool/...`
2. **dpkg PATH 必须显式设置**：`run-as com.termux` 不继承环境变量
3. **pydantic / pydantic-core 版本匹配**：Android wheel 最高 2.46.3，Mac venv 的 pydantic 可能要求 >=2.46.4
4. **entry_points.txt 修改**：Python 会缓存 .dist-info 的 entry points，需要清除 `__pycache__` 或重启进程
5. **run-as vs su**：`run-as com.termux` 受 SELinux 限制，不能创建 socket。root shell (`su -c`) 有完整网络功能但 Termux 的 apt-get 内置 root 保护
6. **手机侧网络**：root shell 走 ADB reverse 端口时需要 HTTP CONNECT 代理（mitmproxy），不能用 SOCKS5（手机侧 SOCKS5 工具不稳定）