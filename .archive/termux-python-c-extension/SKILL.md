---
name: termux-python-c-extension
description: How to install Python packages with C extensions (pyyaml, numpy, etc.) on Android/Termux via ADB — handles dpkg in Termux, libyaml dependency, pip build isolation traps, and offline install workflows when device has no network.
category: devops
---

# Termux Python C Extension Install

## Problem
PyPI wheels for C extension packages (PyYAML, numpy, etc.) are `manylinux`/`musllinux` — pip on Android rejects them as unsupported platform. `pip install --no-binary :all:` triggers build isolation which needs to download build deps (setuptools, cython, flit_core) from PyPI — but Termux may not have pypi.org in DNS, or the ADB reverse proxy may drop CONNECT connections.

## Diagnosis Flow

1. **Check device network first**: `adb shell ping -c 2 -W 3 <gateway_ip>`. If "Network is unreachable", the device has NO network — not a pip problem, it's a WiFi/network problem. Fix network before touching pip.

2. **Check routing table**: `adb shell "ip route show"`. Common traps:
   - `default dev dummy0` — default route points to dummy interface (no carrier)
   - `rmnet_data0/1` UP but no default route — cellular data may be blocked or USB tethering not configured
   - `rndis0 NO-CARRIER` — USB tethering interface exists but hasn't been enabled on phone

3. **Check if `pkg` works as root**: On modern Termux, `pkg` is explicitly disabled in root for safety. Error: "Cannot run 'pkg' command as root". Use `dpkg -i` instead.

4. **Check if dpkg is in PATH**: In root shell, `dpkg` is not in PATH. Must use full path: `/data/data/com.termux/files/usr/bin/dpkg` with `TERMUX_PREFIX` exported.

## Solutions (in priority order)

### 1. pkg install termux-native-package
```bash
# In termux (non-root user context, NOT su -c)
pkg install python-yaml   # Termux packages built for Android
```
Only works if device has network AND pkg is accessible (not in root shell).

### 2. dpkg install .deb manually
```bash
# On host: download .deb
curl -L -o python-yaml.deb "https://packages.termux.dev/apt/termux-main/pool/main/p/python-yaml/python-yaml_6.0.3-1_aarch64.deb"

# Push to device
adb push python-yaml.deb /sdcard/Download/

# Install via termux dpkg (full path)
adb shell "export TERMUX_PREFIX=/data/data/com.termux/files/usr && export PATH=\$TERMUX_PREFIX/bin:\$TERMUX_PREFIX/usr/bin:\$PATH && /data/data/com.termux/files/usr/bin/dpkg -i /sdcard/Download/python-yaml.deb"
```
Note: URL may be 404 — check Termux package index for exact version/path.

### 3. Pure Python pyyaml — copy from host (recommended when offline)
When device has NO network and cannot compile, copy pyyaml's pure Python source from host Mac to device's site-packages.

Steps:
1. On host, install pyyaml if not already: `pip3 install pyyaml`
2. Find yaml package: `python3 -c "import yaml, os; print(os.path.dirname(yaml.__file__))"`
3. Pack pure Python files (no .so): `cp <yaml_dir>/*.py /tmp/yaml_pure/ && cd /tmp/yaml_pure && tar czf /tmp/yaml_pure.tar.gz *`
4. Push to device: `adb push /tmp/yaml_pure.tar.gz /data/local/tmp/yaml_pure.tar.gz`
5. On device, unpack to site-packages:
   ```bash
   SP=/data/data/com.termux/files/usr/lib/python3.13/site-packages/
   rm -rf $SP/yaml/  # remove old pyyaml
   cd $SP/
   tar xzf /data/local/tmp/yaml_pure.tar.gz
   ```
6. **cyaml.py should be the original** (with bare `from yaml._yaml import ...` and NO try/except). The `yaml/__init__.py` wraps `from .cyaml import *` in its own try/except, so `import yaml` still works. `__with_libyaml__` gets set to False.
7. **Verify `from yaml import CSafeLoader`**: If cyaml raises ImportError, CSafeLoader won't be in `yaml` namespace. `getattr(yaml, "CSafeLoader", None)` returns None. Hermes skill_utils.py uses this exact pattern, so it falls back to SafeLoader correctly.
8. **If you need `from yaml import CSafeLoader` to succeed**, create a modified cyaml.py:
   ```python
   try:
       from yaml._yaml import CParser, CEmitter
       # ... real C class definitions ...
   except ImportError:
       from .loader import SafeLoader
       class CBaseLoader(SafeLoader): pass
       class CSafeLoader(SafeLoader): pass
       class CFullLoader(SafeLoader): pass
       class CUnsafeLoader(SafeLoader): pass
       class CLoader(SafeLoader): pass
       class CBaseDumper(SafeLoader): pass
       class CSafeDumper(SafeLoader): pass
       class CDumper(SafeLoader): pass
   ```
   Note: must inherit from `SafeLoader` (not define bare stubs) so `yaml.load(text, Loader=CSafeLoader)` works — SafeLoader's `__init__(self, stream)` is inherited.
9. Clear pycache: `find $SP/yaml -name "*.pyc" -delete; rm -rf $SP/yaml/__pycache__`
10. Test: `python3 -c "import yaml; print(yaml.__version__); from yaml import SafeLoader; print(yaml.safe_load('name: test'))"`

### 4. Pure Python stub (emergency fallback)
When no network AND no build tools available, drop a minimal pure-Python yaml module at the site-packages path. Must implement at minimum: `safe_load`, `load`, `dump`, `SafeLoader`, `SafeDumper`.

## Post-install Termux-user Remediation

Whenever any package gets installed in Termux via `su -c` (root context), the resulting files in `/data/data/com.termux/files/usr/` get owned by `root:root` with mode bits matching what the installer prescribed — sometimes `755`, often `700` for shared libraries. This is *silent* on ADB (which runs commands as root) but breaks every terminal session in the Termux app itself.

**Symptom:**
- `hermes --version` works from `adb shell` but fails inside Termux with `bad interpreter: Permission denied`
- After the `hermes` binary itself is fixed, `ImportError: dlopen failed: library "libssl.so.3" not found` (or `libpython3.13.so`, etc.) follows — because Python loads `libssl.so.3` from the Termux prefix via dynamic linking, and that file is also `root:root 700`
- `ls -la $TP/lib/lib*.so*` shows `root root -rwx------`

**One-shot fix** — run after every `su -c pip install` / `su -c dpkg`:

```bash
# Get Termux user's UID
TERMUX_UID=$(adb shell dumpsys package com.termux | awk '/userId/{print $1}' | tail -1)
# On LineageOS/Mi6 this is 10188; on AOSP it's 10x. Verify manually.

# chown with -h so symlinks themselves get fixed too
echo "Re-chowning Termux prefix to UID $TERMUX_UID..."
adb shell su -c "
  chown -hR $TERMUX_UID:$TERMUX_UID /data/data/com.termux/files/usr/bin \
                                       /data/data/com.termux/files/usr/lib \
                                       /data/data/com.termux/files/usr/include \
                                       /data/data/com.termux/files/usr/libexec
  chmod 755 /data/data/com.termux/files/usr/bin/* \
            /data/data/com.termux/files/usr/lib/lib*.so* 2>/dev/null
"
```

**Verify as the right user** — *do not* just run `hermes --version` from ADB, that always works. Use:

```bash
adb shell su -c "su 10188 -c '/data/data/com.termux/files/usr/bin/hermes --version'"
```

If that still says `command not found`, the PATH is wrong — go to the next step.

**Login-shell PATH workaround** — `su 10188 /system/bin/sh` only sees the framework PATH (`/system/bin`, etc.), not Termux's. To test interactively or run a script as the Termux user from ADB:

```bash
adb shell su 10188 /data/data/com.termux/files/usr/bin/bash -l -c 'export PATH=$PATH:/data/data/com.termux/files/usr/bin; hermes --version'
```

If the bash login shell is available, use it; if not (some LineageOS builds), fall back to:

```bash
adb shell 'su 10188 /data/data/com.termux/files/usr/bin/bash -c "
  export PATH=/data/data/com.termux/files/usr/bin:/data/data/com.termux/files/usr/bin/applets
  export HOME=/data/data/com.termux/files/home
  export LD_LIBRARY_PATH=/data/data/com.termux/files/usr/lib
  <your-command-here>
"'
```

Always prefer running this validation after every `su -c <install>`. Otherwise the first terminal session the user opens post-install will look broken for no apparent reason.

## Android Gateway Troubleshooting

### psutil blocks Telegram connection
When Hermes gateway fails to connect Telegram with a `NotImplementedError: platform android is not supported` error in `psutil/__init__.py`, the package is incompatible with Android and must be removed:
```bash
# Kill gateway first
pkill -9 -f "hermes_cli"
# Remove psutil
rm -rf /data/data/com.termux/files/usr/lib/python3.13/site-packages/psutil*
# Restart gateway
hermes gateway run
```
Do NOT try to upgrade psutil — it will never work on Android.

### pydantic-core version mismatch
Pydantic 2.13.4 requires pydantic-core >= 2.46.4. Termux ships 2.46.3 by default. Error: `pydantic-core version (2.46.3) is incompatible with the current pydantic version, which requires 2.46.4`.
**Fix**: Upgrade pydantic-core via wheel file from Mac host (see "Offline install workflows" above). pip on Android will reject `manylinux` wheels by default — use the `unzip` + `adb push` + manual extraction method.

### Gateway blocks its own restart
The gateway process SIGTERMs its own child processes including any shell spawned inside it. Running `hermes gateway restart` from within a gateway shell will deadlock. Always kill the gateway PID first in a separate command, wait, then restart.

### Always-on screen for persistent gateway
When a phone runs Hermes gateway as a server:
1. Set `screen_off_timeout` to max: `su -c 'settings put system screen_off_timeout 2147483647'` (Android rejects -1)
2. Enable stay-on-while-charging: `su -c 'settings put global stay_on_while_plugged_in 3'`
Without these, the phone will sleep, cut WiFi, and disconnect the gateway.

### ADB shell timeout when gateway is hung
When the gateway is stuck (old pydantic, missing key, etc.), all ADB shell commands will hang/timeout. The device may still show `device` in `adb devices` but `adb shell` blocks forever. **Solution**: `adb disconnect <device>:<port>` then `adb connect <device>:<port>` and wait 3-5 seconds before retrying. If still stuck, user must manually `pkill -9 -f "hermes_cli"` in the Termux app.

## Pitfalls (continued — see also `android-phone-hermes-setup` skill for gateway troubleshooting, ADB reconnection, screen always-on, gateway self-deadlock, psutil removal, and pydantic-core upgrade workflows)

- **`su -c` root shell has broken DNS** — Termux's DNS settings (nameservers, search domains, proxy configuration) are stored in `~/.termux/termux.properties` and `/data/data/com.termux/files/usr/etc/resolv.conf`, but `su -c` runs in root context which may not inherit these. When `curl`/`pip` inside `su -c` fails with `NameResolutionError` but works in Termux user context, this is the cause. **Workaround**: Run network commands as the Termux user via `su -u <uid> -c 'command'` or use `run-as com.termux sh -c '...'` instead of `su -c`.
- **Android 15 App data directory policy**: Termux app must be launched at least once before ADB can access its data directory. Before installing Termux via ADB, user must tap the Termux icon on the device.
- **Simple proxy for HTTPS**: A raw TCP proxy (simple_proxy.py style) does NOT support HTTPS CONNECT tunneling. pip uses CONNECT for PyPI. Use mitmproxy, cntlm, or a proper HTTP proxy.
- **Root vs Termux user**: `su -c` runs as root, but Termux packages are owned by termux user (UID 10188). Commands like `pkg` explicitly refuse to run as root. Use `/data/data/com.termux/files/usr/bin/dpkg` for dpkg operations.
- **DNS on Android**: Termux may not have DNS configured. `getaddrinfo` fails for pypi.org. Check with `ping` or `nslookup` first.
- **Proxy port mismatch**: ADB reverse maps phone port to host port. If proxy listens on 8080 but ADB reverse maps 9999->8080, pip `--proxy http://127.0.0.1:9999` is correct for phone-side.
- **pip build isolation downloads build deps**: Even `--no-binary :all:` triggers build isolation which downloads setuptools/cython/flit_core from PyPI. Use `--no-build-isolation` to skip this.
- **tar extract creates wrong path**: When tar contains `yaml/*.py` (not `yaml/` directory), extracting creates flat files in destination instead of `yaml/` subdirectory. Fix: tar with `cd $PYAML_DIR && tar czf file.tar.gz yaml/` (include top-level dir name).
- **cyaml.py ImportError**: Original cyaml.py has bare `from yaml._yaml import ...` with no try/except. The `yaml/__init__.py` wraps `from .cyaml import *` in its own try/except, so `import yaml` still works. But `from yaml import CSafeLoader` will fail. Use getattr pattern or modified cyaml.py as above.
- **Stub class must inherit from SafeLoader**: If cyaml fallback defines `class CSafeLoader: pass`, calling `yaml.load(text, Loader=CSafeLoader)` will fail because no `__init__` accepts `stream` argument. Always inherit from SafeLoader for fallback stubs.
- **`su -c pip install` makes everything root-owned mode `700`** — see "Post-install Termux user remediation" below. After ANY pip/apt step run via `su -c`, Termux shell will start failing with `bad interpreter` or `dlopen failed: library not found` even though everything still works from ADB. Re-run the chown block before reporting "broken".
- **`stat -c '%u'` doesn't work on Android ToyBox** — error is `stat: illegal option -- c`. Hardcode Termux's UID (typically 10188; verify with `dumpsys package com.termux | grep userId`) instead of trying to discover it.
- **`chown -R` does NOT update symlink ownership** — must pass `-h` (`chown -hR`) so `libssl.so` itself becomes `u0_a188:u0_a188` instead of staying `root:root`. Otherwise dlopen rejects the path even after the underlying `libssl.so.3` has been chowned.