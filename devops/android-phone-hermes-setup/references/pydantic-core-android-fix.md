# pydantic-core Version Mismatch on Android Termux

## The Problem

pydantic (e.g. 2.13.4) requires pydantic-core >= 2.46.4. If the installed version is older (e.g. 2.46.3), the gateway crashes at startup with:

```
RuntimeError: Failed to initialize OpenAI client: The installed pydantic-core version (2.46.3) is incompatible with the current pydantic version, which requires 2.46.4.
```

## The Fix

### Step A: Download Android wheel on Mac

```bash
pip3 download --no-deps \
  --platform manylinux2014_aarch64 \
  --only-binary=:all: \
  --python-version 3.13 \
  pydantic-core==2.47.0 \
  -d /tmp/pydantic-wheel
```

This downloads `pydantic_core-2.47.0-cp313-cp313-manylinux_2_17_aarch64.manylinux2014_aarch64.whl` (~2MB).

### Step B: Push to device

```bash
adb -s <ip> push /tmp/pydantic-wheel/pydantic_core-2.47.0-cp313-cp313-manylinux_2_17_aarch64.manylinux2014_aarch64.whl /data/local/tmp/
```

**ADB connection may be unstable** — if `adb push` times out or device is not found:
1. `adb disconnect <ip>` then `adb connect <ip>:5555`
2. Re-check with `adb devices`
3. If still failing, device may have switched WiFi or gone to sleep

### Step C: Install via unzip

```bash
adb -s <ip> shell "su -c '
cd /data/data/com.termux/files/usr/lib/python3.13/site-packages
unzip -qo /data/local/tmp/pydantic_core-*.whl
'"
```

Note: `unzip` is used because `pip` may be broken on the device. The wheel contains the compiled `.so` files directly.

### Step D: Kill and restart gateway

```bash
# Kill old process
adb -s <ip> shell "su -c kill -9 \$(pgrep -f 'python3.*hermes_cli' | head -1)"
# Start new (use gateway run, not start — start requires systemd which Termux lacks)
adb -s <ip> shell "su -c '
export HOME=/data/data/com.termux/files/home
export PATH=/data/data/com.termux/files/usr/bin:\$PATH
export PYTHONPATH=/data/data/com.termux/files/usr/lib/python3.13/site-packages:\$PYTHONPATH
nohup python3 -m hermes_cli.main gateway run > \$HOME/.hermes/logs/gateway.log 2>&1 &
'"
```

### Step E: Verify

```bash
adb -s <ip> shell "su -c '
export PATH=/data/data/com.termux/files/usr/bin:\$PATH
/data/data/com.termux/files/usr/bin/python3 -c \"import importlib.metadata; print(importlib.metadata.version(\"pydantic-core\"))\"
'"
```

Should now return `2.47.0` (or whichever version you installed).

## Why This Happens

pydantic-core ships compiled C extensions per platform. Termux on Android ships `cp313` but the wheel in Termux may be from an older pydantic release. When pydantic upgrades its minimum pydantic-core requirement, a version mismatch occurs.

## Version Matrix

| pydantic | required pydantic-core |
|----------|----------------------|
| 2.13.4 | >= 2.46.4 |
| 2.12.0 | >= 2.45.0 |
| 2.11.0 | >= 2.43.0 |

Always check `pip3 show pydantic` on the device to see what pydantic version is installed, then look up the matching pydantic-core requirement on PyPI.

## Alternative: Upgrade from Source

If the device has network and pip works, just:
```bash
pip3 install --upgrade pydantic-core
```

This only works if:
- Device has working DNS/pip access (not in `su -c` context)
- pip is not broken (see termux-python-c-extension skill for pip repair)