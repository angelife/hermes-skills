---
name: pydantic-core-android-fix
description: pydantic-core version mismatch fix on Android Termux
title: pydantic-core Version Mismatch on Android Termux
---

# pydantic-core Version Mismatch on Android Termux

## The Problem

pydantic (e.g. 2.13.4) requires pydantic-core >= 2.46.4. If the installed version is older (e.g. 2.46.3), the gateway crashes at startup with:

```
RuntimeError: Failed to initialize OpenAI client: The installed pydantic-core version (2.46.3) is incompatible with the current pydantic version, which requires 2.46.4.
```

## CRITICAL: Do NOT use PyPI manylinux wheels on Android

**PyPI's `manylinux2014_aarch64` wheel is `linux-gnu` (glibc) ABI.** It will NOT work on Android because Termux uses **bionic libc**, not glibc or musl.

Symptoms of trying to install a manylinux wheel on Android:
```
ImportError: libgcc_s.so.1: cannot open shared object file
# or
ImportError: undefined symbol: __gxx_personality_v0
```

**Eutalix/android-pydantic-core** only supports up to **Python 3.12**. It is no longer maintained.

## Correct Fix Paths

### Path A: Compile from source in Termux (preferred)

Termux ships with Rust/cargo. Use them to compile pydantic-core from PyPI's tar.gz source:

```bash
# Step 1: Get the source URL
# From PyPI page: https://pypi.org/project/pydantic-core/#files
# Look for pydantic_core-2.47.0.tar.gz

# Step 2: Download via Termux curl (user-space, not su)
cd ~
curl -LO https://files.pythonhosted.org/packages/source/p/pydantic-core/pydantic-core-2.47.0.tar.gz

# Step 3: Extract and compile
tar xzf pydantic-core-2.47.0.tar.gz
cd pydantic-core-2.47.0

# Build with maturin (need maturin in Termux)
# If maturin not installed: pip install maturin
export TERMUX_PREFIX=/data/data/com.termux/files/usr
export PATH=$TERMUX_PREFIX/bin:$PATH
maturin build --release
# Output: target/wheels/pydantic_core-2.47.0-cp313-cp313-linux_aarch64.whl

# Step 4: Install the built wheel
pip install target/wheels/pydantic_core-2.47.0-cp313-cp313-linux_aarch64.whl
```

**If maturin not available**: Try `pip install --no-binary pydantic-core pydantic-core==2.47.0`. This downloads tar.gz and uses cargo to build. May take 5-10 minutes.

**Network note**: pip install may timeout on PyPI (DNS issues in su context). If so:
- Download tar.gz manually via Termux curl (user-space has network)
- `pip install /path/to/pydantic-core-2.47.0.tar.gz --no-binary`

### Path B: Downgrade to Python 3.12 (fallback)

If Rust compilation fails or takes too long:

```bash
# Install Python 3.12 in Termux
pkg install python

# Check version — if still 3.13, need to switch
python3 --version

# Switch to 3.12 via termux-change-repo or reinstall
# Then install Eutalix wheel:
curl -sLO "https://github.com/Eutalix/android-pydantic-core/releases/download/v2.47.0/pydantic_core-2.47.0-cp312-cp312-linux_aarch64.whl"
unzip -qo pydantic_core-*.whl -d /data/data/com.termux/files/usr/lib/python3.12/site-packages/
```

## Verify Fix

```bash
adb -s <ip> shell "su -c '
export PATH=/data/data/com.termux/files/usr/bin:\$PATH
/data/data/com.termux/files/usr/bin/python3 -c \"import pydantic_core; print(pydantic_core.__version__)\"
'"
# Should return 2.47.0
```

## Kill and Restart Gateway

```bash
# Kill old process
adb -s <ip> shell "su -c 'pkill -9 -f \\\"hermes_cli\\\"'"

# Start new gateway
adb -s <ip> shell "su -c '
export HOME=/data/data/com.termux/files/home
export PATH=/data/data/com.termux/files/usr/bin:\$PATH
export PYTHONPATH=/data/data/com.termux/files/usr/lib/python3.13/site-packages:\$PYTHONPATH
nohup python3 -m hermes_cli.main gateway run > \$HOME/.hermes/logs/gateway.log 2>&1 &
'"
```

## Root Cause

pydantic-core ships compiled C extensions per platform. Termux on Android ships `cp313` but the wheel may be from an older pydantic release. When pydantic upgrades its minimum pydantic-core requirement, a version mismatch occurs.

## Version Matrix

| pydantic | required pydantic-core |
|----------|----------------------|
| 2.13.4 | >= 2.46.4 |
| 2.12.0 | >= 2.45.0 |
| 2.11.0 | >= 2.43.0 |

Always check `pip3 show pydantic` on the device to see what pydantic version is installed, then look up the matching pydantic-core requirement on PyPI.

## Library ABI Mismatch Reference

| Platform | libc | Compatible wheel ABI |
|----------|------|---------------------|
| Linux (glibc) | glibc | `manylinux2014_aarch64` → `.cpython-313-aarch64-linux-gnu.so` |
| Linux (musl) | musl | `musllinux_1_1_aarch64` → `.cpython-313-aarch64-linux-musl.so` |
| Android (Termux) | bionic | **No PyPI wheel!** Needs: `linux_aarch64` (Eutalix) or compiled from source |

**Key lesson**: `manylinux` wheels on PyPI are NOT Android-compatible. They target glibc-based Linux. Android uses bionic libc. The ABI is different. Always check the .so filename inside the wheel:
- `linux-gnu.so` → won't work on Android
- `linux-musl.so` → won't work on Android
- `linux_aarch64` → may work on Android (Eutalix)