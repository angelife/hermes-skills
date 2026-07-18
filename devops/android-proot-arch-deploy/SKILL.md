---
name: android-proot-arch-deploy
description: >
  在已 Root 的 Android 设备上部署 Arch Linux proot 容器，并越过 pacman/GPGME 签名限制安装服务。
  适用场景：没有 chroot 环境 / GPG engine 在 proot 下不可用 / /etc/mtab 为空导致 pacman 无法 commit。
  覆盖网络诊断、pacman.conf 调优、静态包手动安装、Alist/aria2/nginx 最小化部署。
tags:
  - android
  - proot
  - arch-linux
  - root
  - container
---

# Android Proot Arch Deploy

## When to Use

- Android device is already rooted (Magisk root confirmed)
- Goal is to run a thin Arch Linux userland on-device for server/relay/tooling
- Normal `pacman` path is broken inside proot even after `DisableSandboxFilesystem/Syscalls`
- You want Alist / aria2 / nginx or similar self-hosted services without full Android app dependency

## TL;DR decision rule

1. Try proot first.
2. If `pacman-key --init` or package verification fails with gpg/engine errors after 2 distinct fixes, **stop**.
3. Switch to static-binary or source-binary manual install.

## Prerequisites

Before starting, confirm:
- `su 0 -c id` returns `uid=0(root)`
- proot static binary is present at `/data/local/tmp/proot-arm64` or equivalent, chmod 755
- Arch rootfs is extracted under `/data/local/tmp/arch` or `/data/local/arch`
- Host can reach device over ADB over TCP on `192.168.1.26:5555` for recoverability

## Step 1 — Proot launch baseline

Use this exact base command pattern for troubleshooting:

```bash
PROOT_NO_SECCOMP=1 \
/data/local/tmp/proot-arm64 \
-r /data/local/tmp/arch \
-b /proc/self/mounts:/proc/self/mounts \
/usr/bin/bash -lc 'id; uname -a; ls /etc'
```

Out-of-tree mounts shown in host `mountinfo` do not automatically appear inside proot. If a tool needs `/proc`, `/sys`, or `/dev` mounted, create the mountpoint directories in rootfs first:
`mkdir -p /proc /sys /dev/pts /dev/shm`

## Step 2 — Fix network inside container

If `curl / getent hosts` fails only inside proot:

```bash
# Replace dangling /etc/resolv.conf symlink with static nameservers
cat > /data/local/tmp/arch/etc/resolv.conf <<EOF
nameserver 223.5.5.5
nameserver 8.8.8.8
EOF
```

Verify:
```bash
curl -I -sS --max-time 10 https://archlinux.org
```

## Step 3 — Pacman hardening (attempt #1)

Edit `/data/local/tmp/arch/etc/pacman.conf`:

```bash
sed -i \
  -e 's/^#DisableSandboxFilesystem/DisableSandboxFilesystem/' \
  -e 's/^#DisableSandboxSyscalls/DisableSandboxSyscalls/' \
  /data/local/tmp/arch/etc/pacman.conf
```

Create stable `/etc/mtab` so pacman sees mount points:

```bash
cat > /data/local/tmp/arch/etc/mtab <<EOF
rootfs / rootfs rw 0 0
none /proc proc rw 0 0
none /sys sysfs rw 0 0
none /dev tmpfs rw 0 0
none /dev/pts devpts rw 0 0
none /dev/shm tmpfs rw 0 0
EOF
```

## Step 4 — Pacman keyring bootstrap (attempt #2)

Initialize keyring and import Arch Linux ARM master key manually to bypass keyserver:

```bash
pacman-key --init
pacman-key --populate archlinuxarm
```

If `pacman-key --init` still claims `Cannot find the gpg binary`, **ignore the error** and verify:
```bash
gpg --homedir /etc/pacman.d/gnupg --list-keys
```

If keys import and list successfully, the embedded error was false-negative.

## Step 5 — Stop digging on GPGME engine errors

If installing any package yields:

```
GPGME version: X.Y.Z
error: GPGME error: Invalid crypto engine
error: failed to commit transaction (invalid or corrupted package (PGP signature))
```

This is not curable by changing `SigLevel` or reinstalling `gnupg`. It is a proot + GPGME engine mismatch. **Do not iterate further.** Move to Step 6.

## Step 6 — Static-binary / manual-package fallback

Required host-side tools:
- curl, tar, xz, zstd, gzip
- Known-good server binaries or arch package `.pkg.tar.xz` / `.pkg.tar.zst`

Recommended flow for each package:

```bash
pkg_url="<trusted download URL>"
curl -L -o /tmp/pkg.tar.xz "$pkg_url"
tar -xJf /tmp/pkg.tar.xz -C /data/local/tmp/arch/
```

After install, always verify binary presence:
```bash
/data/local/tmp/proot-arm64 -r /data/local/tmp/arch /usr/bin/<binary> --version
```

## Mirror troubleshooting shortcuts

- Host `ping` is not a proot network test. Use `curl -I` inside proot.
- `mirror.archlinuxarm.org` redirects by geography; if redirected host is unreachable from inside proot, swap to:
  - `http://mirror.archlinuxarm.org/aarch64/core/`
  - `https://mirrors.tuna.tsinghua.edu.cn/archlinuxarm/aarch64/core/`
  - HTTPS `mirror.archlinuxarm.org` may fail due to CN SAN mismatch; use HTTP if needed.
- If HTTPS fetch fails with `(60) SSL: no alternative certificate subject name matches`, retry with HTTP or add `-k` only as a last resort.

## Verification checklist (must-pass before declaring Linux deployed)

- [ ] `run-arch.sh`-style proot command returns `uid=0(root)` and a bash prompt
- [ ] `cat /etc/resolv.conf` contains a real nameserver line
- [ ] `curl -I -sS https://archlinux.org` returns HTTP status
- [ ] `/usr/bin/<installed-binary>` exists and prints version inside proot
- [ ] Host ADB connectivity: `adb connect 192.168.1.26:5555` succeeds from Mac

## Pitfalls

1. **Proot mounts are virtual**. Proot does not inherit host mounts. Bind explicit rootfs dirs with `-b`, or pre-create the directories inside rootfs.
2. **`/proc/self/mounts` inside proot is empty even on host where it is populated**. Substitute a static `/etc/mtab` file rather than symlink to `/proc/self/mounts`.
3. **`/etc/resolv.conf` symlinks to systemd-resolved paths**. The target `/run/systemd/resolve/resolv.conf` does not exist in proot. Write a static resolv.conf instead.
4. **`pacman-key --init` false negative**. Error claims missing gpg, but `type -p gpg && gpg --version` shows it exists. Trust the live evidence; the script's error path was stale.
5. **GPGME engine failure is unfixable by SigLevel alone**. Once alpm/ pacman enters the verify path, `SigLevel = TrustAll` does not skip GPGME engine init.
6. **`adb connect` must be recorded and retested after each reboot**. Store `192.168.1.26:5555` in persistent memory; confirm with `adb devices`.
7. **Rootfs path drift**. If `/data/local/arch` vanishes, search for the extracted rootfs under `/data/local/tmp/arch` or `/sdcard/Download/`. Re-specify `-r` accordingly.