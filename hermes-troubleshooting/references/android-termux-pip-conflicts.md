# Android/Termux: psutil & cryptography Conflicts

## The Two Broken Packages

Two pip packages break Hermes on Android/Termux. **Remove both entirely** (not downgrade, not patch):

| Package | Symptom | Root cause | Fix |
|---------|---------|------------|-----|
| **psutil ≥ 7.x** | `NotImplementedError: platform android is not supported` at gateway startup, blocks Telegram connection | psutil 7.x explicitly checks `sys.platform` and refuses to load on Android | `pip3 uninstall -y psutil; rm -rf /data/data/com.termux/files/usr/lib/python3.13/site-packages/psutil*` |
| **cryptography ≥ 46.x** | `AttributeError: module has no attribute 'hashes'` at runtime | Rust-built C extensions incompatible with Termux Bionic libc | `pip3 uninstall -y cryptography` |

## Why Removing Works

Both Hermes and Telegram-bot libraries import these packages inside `try/except ImportError` blocks:

```python
try:
    import psutil
except ImportError:
    # graceful fallback — no crash
```

Removing the package makes the import raise `ModuleNotFoundError`, which is caught. Leaving a BROKEN package installed (one that imports but then fails) causes a hard crash that `except ImportError` cannot catch.

## Stale Stub After Uninstall

If `pip3 uninstall` leaves a partial module behind, `import psutil` succeeds but returns an empty/broken module:

```python
>>> import psutil
>>> psutil.pid_exists(1)
AttributeError: module 'psutil' has no attribute 'pid_exists'
```

This produces the error `module 'psutil' has no attribute 'pid_exists'` — NOT the usual `platform android is not supported`. Fix:

```bash
find /data/data/com.termux/files/usr/lib/python3.13 -name "*psutil*" -exec rm -rf {} +
rm -rf /data/data/com.termux/files/usr/lib/python3.13/site-packages/__editable__.psutil*
rm -rf /data/data/com.termux/files/usr/lib/python3.13/site-packages.bak
```

Then verify `import psutil` raises `ModuleNotFoundError`.

## Verification

```bash
python3 -c "import psutil" 2>&1  # ModuleNotFoundError ✓
python3 -c "from telegram.ext import Application; print('OK')"  # OK ✓
```

## Related: Hermes has a built-in Android psutil patcher

Hermes ships `hermes_cli/psutil_android.py` which can download psutil 7.2.2 source, patch `_common.py` to recognize Android, and build it. This works on systems with a C compiler + Rust. On Termux, building psutil from source fails (no rustc/gcc). The reference is useful when building on a full Linux system for cross-deployment.
