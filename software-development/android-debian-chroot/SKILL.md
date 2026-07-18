---
name: android-debian-chroot
description: "Deploy Debian rootfs as chroot on a rooted Android device. Covers rootfs extraction, chroot mounting, and basic config."
tags:
  - android
  - debian
  - chroot
  - rootfs
  - mi8
---

# Android Debian chroot

## When to Use
User asks to install Debian as chroot on a rooted device like Mi8. Skips A/B/C options; use the preferred LXC-then-docker-then-mmdebstrap path.

## Prerequisite
Search prior sessions for this target first, especially when user mentions previous full install followed by factory reset. Rebuild from history, not from assumptions.

## Rootfs priority
1. LXC images site for Bookworm arm64
2. Docker export
3. Mac mmdebstrap as debootstrap fallback

## Proven Mac→phone flow
```bash
# Download LXC rootfs.xz to Mac /tmp
curl -L -o /tmp/debian-rootfs.tar.xz "https://images.linuxcontainers.org/images/debian/bookworm/arm64/default/<date>/rootfs.tar.xz"

# Convert xz→tar on Mac to avoid Android tar missing xz support
xz -dc /tmp/debian-rootfs.tar.xz > /tmp/debian-rootfs.tar

# Push and extract into clean dir
adb push /tmp/debian-rootfs.tar /data/local/tmp/
adb shell 'mkdir -p /data/local/tmp/debian && cd /data/local/tmp && tar xf debian-rootfs.tar -C debian'
```
Ignore hardlink permission errors; verify with `ls /data/local/tmp/debian/etc`.

## resolv.conf pitfall
Fresh rootfs may ship `/etc/resolv.conf` as a broken symlink pointing to `/run/systemd/resolve/stub-resolv.conf` (which doesn't exist in chroot). Writing to it returns "No such file or directory" even though the parent directory exists.
```
# Fix: remove symlink first, then write real file
adb shell 'rm /data/local/tmp/debian/etc/resolv.conf'
adb push resolv.conf /data/local/tmp/debian/etc/
```
Alternatively, write via `chroot ... /bin/sh -c 'cat > /etc/resolv.conf'` if direct adb shell redirection still inherits the shell's "Read-only file system" mapping.

## Phone network prerequisite
`apt update` will silently fail if phone has no mobile data and no WiFi. Check before configuring chroot:
```bash
adb shell 'ping -c 2 -W 3 mirrors.aliyun.com'
```
If DNS fails, ask user to connect WiFi first.

## Configure rootfs
- Remove broken resolv.conf symlink before writing real file
- Write `resolv.conf`, apt sources (AliDNS mirror), sandbox off, runtime dirs
- Prefer writing through chroot context when direct writes fail

## Chroot enter
```
su -c "mount -t proc proc /data/local/tmp/debian/proc"
su -c "mount -t sysfs sysfs /data/local/tmp/debian/sys"
su -c "mount -o bind /dev /data/local/tmp/debian/dev"
su -c "chroot /data/local/tmp/debian /bin/sh -lc <cmd>"
```
Use `/bin/sh` to skip `/etc/profile id: command not found` noise inside chroot.

## Pitfalls
- After factory reset: chroot dir and app configs are gone; reinstall from history
- Docker Hub TLS timeout: fix mirror then restart Docker Desktop
- Phone offline breaks apt: verify WiFi first
- Writing resolv.conf fails if target is broken symlink: remove link before writing
- zgz format: Mac tar may not handle .tar.gz through adb shell properly; prefer uncompressed `.tar`

## Magisk-root chroot notes
Don't treat chroot as impossible just because early `/dev` binds look partial. On some Mi-class devices with Magisk, `su 0` mount bind may appear empty on first try; the real test is chroot visibility of `/dev/null`, `/dev/zero`, `/dev/urandom`.

Correct order under `su 0`:
```bash
D=/data/local/tmp/chroot/debian
mkdir -p $D/dev $D/proc $D/sys
mount --bind /dev $D/dev
mount --bind /proc $D/proc
mount --bind /sys $D/sys
chroot $D /bin/sh -lc 'ls -l /dev/null /dev/zero /dev/urandom && python3 --version && pip3 --version'
```
Use `/bin/sh`, not `/bin/bash`, inside chroot; `/bin/bash` may not exist in minimal rootfs.

Pitfall: if helpers like `setenforce` report one value and `getprop`/`dmesg` show another, trust the mount evidence in chroot over the escaping `getenforce` text.

## Hermes chroot install notes
- Prefer chroot over proot once `/dev` mounts are confirmed; this session shows chroot can work on Mi6 where earlier attempts failed due to incomplete bind, not kernel incompatibility.
- Install Hermes into chroot venv: `python3 -m venv /root/.hermes/venv`, then `pip install hermes-agent`. For Telegram confirm `python-telegram-bot` actually installed; `Requirement already satisfied` from `hermes-agent[telegram]` can still leave PTB absent.
- Runtime pitfall: HG8155. If Telegram session startup sequence fails from telegram close in previous session, gateway can retain state. To force clean start, stop gateway, remove runtime locks, then start.
- Verified Telegram dependency pair for Hermes `0.18.x` on chroot: `python-telegram-bot>=21.10,<22` + `httpx~=0.28`. After upgrading PTB, clear Hermes/Telegram plugin `__pycache__` before restarting gateway; stale `.pyc` can keep the old incompatible signature alive.
- If logs show `HTTPXRequest.__init__() got an unexpected keyword argument 'httpx_kwargs'`, treat it as a dependency mismatch, not a network/token issue. Stop retrying `hermes gateway run` and verify the installed PTB signature first.
- Startup detach under adb shell: `nohup`/`&` wrapper scripts are brittle inside chroot. Preferred pattern: `terminal(background=true)` to run the chrooted `hermes gateway run` directly from the tool layer.

## Writing config files
Direct `adb shell 'echo ... > path'` sometimes fails due to Magisk permission mapping. Reliable order:
1. Try direct adb shell redirection
2. If blocked, write via script file `adb push` + `adb shell 'sh script.sh'`
3. If still blocked, use `su -c "chroot ... /bin/sh -c 'cat > /path'"` to write from inside chroot
