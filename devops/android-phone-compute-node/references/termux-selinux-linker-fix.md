# Termux SELinux Linker Namespace Fix (LineageOS 14)

## Symptom

Termux opens fine but **crashes on Enter** — the shell process exits immediately with:

```
F linker  : CANNOT LINK EXECUTABLE "/data/data/com.termux/files/usr/bin/bash":
            library "libreadline.so.8" not found: needed by main executable
```

No SELinux denial (`avc: denied`) appears in logcat for the library access — the linker's internal namespace check silently returns "not found" before any SELinux file access check.

## Diagnosis Protocol

### Step 1: Confirm SELinux is the root cause

```bash
# Check current mode
adb shell getenforce  # → "Enforcing"

# Temporarily set permissive
adb shell setenforce 0
# → Open Termux, tap Enter → shell works immediately

# Re-enforce
adb shell setenforce 1
# → Termux crashes again on Enter
```

If `setenforce 0` → works, `setenforce 1` → fails, the answer is SELinux.

### Step 2: Check that Termux binaries are not corrupted

```bash
# Manually run bash with LD_LIBRARY_PATH from a root shell
adb shell "PATH=/debug_ramdisk:\$PATH su -c \
  'LD_LIBRARY_PATH=/data/data/com.termux/files/usr/lib \
   /system/bin/linker64 /data/data/com.termux/files/usr/bin/bash -c \"echo HELLO\"" 
# → Expected: "HELLO" (no crash)

# Run the EXACT same command as the Termux user via run-as
adb shell "run-as com.termux env \
  LD_LIBRARY_PATH=/data/data/com.termux/files/usr/lib \
  /system/bin/linker64 /data/data/com.termux/files/usr/bin/bash -c 'echo HELLO'"
# → Expected: "CANNOT LINK EXECUTABLE" (the crash)
```

The difference: `adb root`/`su -c` runs in `u:r:su:s0` domain where LD_LIBRARY_PATH works. `run-as` runs in `untrusted_app_27` domain where it's blocked.

### Step 3: Verify lib placement strategies don't help

```bash
# Strategy A: Copy libs to /data/local/tmp/lib (shell_data_file context)
adb shell "cp /data/data/com.termux/files/usr/lib/libreadline.so.8.2 /data/local/tmp/lib/"
adb shell "ln -sf libreadline.so.8.2 /data/local/tmp/lib/libreadline.so.8"

# Then set LD_LIBRARY_PATH=/data/local/tmp/lib — still FAILS
# The linker namespace restriction is per-process-type, not per-file-label

# Strategy B: Copy libs next to the executable
adb shell "cp /data/data/com.termux/files/usr/lib/libreadline.so.8.2 \
  /data/data/com.termux/files/usr/bin/"
# Android's bionic linker does NOT search $ORIGIN (unlike glibc) — still FAILS
```

### Step 4: Confirm via process tree

```bash
# Set permissive
adb shell setenforce 0
# Launch Termux, type Enter
adb shell ps -ef | grep bash
# → u0_a182  24762  24724  ... linker64 /data/data/com.termux/files/usr/bin/bash --login

# Re-enforce — the ALREADY-RUNNING bash survives
adb shell setenforce 1
# → bash PID 24762 is still alive

# But NEW Termux sessions crash
# → Only the bash started under Permissive mode lives
```

## Root Cause

**Android bionic linker API 24+ behavior**: On Android 7.0+, the dynamic linker ignores `LD_LIBRARY_PATH` for executables whose linker namespace has the `no_ld_library_path` restriction. The `untrusted_app_27` SELinux domain on LineageOS 14 has this restriction enabled, preventing any dynamically-linked Termux binary (bash, python, apt) from finding its private libraries.

This is NOT:
- A file permission issue (libraries are readable)
- A file context issue (shell_data_file vs app_data_file doesn't matter)
- A binary corruption issue (binaries execute correctly in `su` domain)
- An SELinux avc denial (the linker rejects the path before it checks SELinux)

Key evidence:
- `setenforce 0` → everything works (namespace restriction disabled)
- `setenforce 1` → broken (namespace restriction enforced)
- No `avc: denied` entries for library files in Enforcing mode
- `/system/bin/linker64` respects LD_LIBRARY_PATH in `su` domain but not in `untrusted_app_27`

## Fix (login script via Magisk su)

```bash
# As root
su -c 'cat > /data/data/com.termux/files/usr/bin/login << "ENDSCRIPT"
#!/data/data/com.termux/files/usr/bin/dash
export HOME=/data/data/com.termux/files/home
export TERM=xterm-256color
export LD_LIBRARY_PATH=/data/data/com.termux/files/usr/lib
exec /debug_ramdisk/su -c "
  cd /data/data/com.termux/files/home
  exec /data/data/com.termux/files/usr/bin/bash --login
"
ENDSCRIPT
chmod 755 /data/data/com.termux/files/usr/bin/login
APP_UID=$(stat -c "%u" /data/data/com.termux/)
chown $APP_UID:$APP_UID /data/data/com.termux/files/usr/bin/login'
```

## Resulting Process Tree (healthy)

```
com.termux (u0_a182, untrusted_app_27)
  └─ login script → dash (u0_a182, untrusted_app_27)
      └─ su (u0_a182, untrusted_app_27)  ← Magisk setuid binary
          └─ bash (root, su domain)       ← LD_LIBRARY_PATH works
              └─ python, apt, etc.
```

## Alternative: setpriv from adb root

For package management (apt/pkg rejects root), use `setpriv --keep-groups` from `adb root`:

```bash
WRAPPER="env HOME=/data/data/com.termux/files/home \
  PREFIX=/data/data/com.termux/files/usr \
  TMPDIR=/data/data/com.termux/files/usr/tmp \
  LD_LIBRARY_PATH=/data/data/com.termux/files/usr/lib \
  PATH=/data/data/com.termux/files/usr/bin:/system/bin"
APP_UID=$(adb shell stat -c "%u" /data/data/com.termux/)
adb shell "$WRAPPER setpriv --reuid=$APP_UID --regid=$APP_UID --keep-groups \
  /data/data/com.termux/files/usr/bin/apt install -y python"
```

## Tested On

- Device: Xiaomi Mi 8 (dipper)
- Android: LineageOS 14 (Android 14, userdebug)
- Kernel: 4.9.337-perf
- Magisk: v30.7
- Termux: v0.118.3+github-debug
