# Mi6 chroot deployment notes

Device: Mi6 (ca00a222), Android aarch64, Magisk root, screen broken, touch disabled.
Deployed: Debian 12 Bookworm ARM64 rootfs in `/data/local/tmp/chroot/debian/`.

## Verified working mount sequence under Magisk

```bash
su 0
D=/data/local/tmp/chroot/debian
mkdir -p $D/dev $D/proc $D/sys
mount --bind /dev $D/dev
mount --bind /proc $D/proc
mount --bind /sys $D/sys
chroot $D /bin/sh -lc 'ls -l /dev/null /dev/zero /dev/urandom && python3 --version && pip3 --version'
```

Critical: use `/bin/sh`, not `/bin/bash`. Also, if early mount verification looks partial, test again from inside chroot; host-side `ls` can mislead.

## SELinux reading quirk

Early `getenforce` reported `Disabled`; `dmesg` later showed `permissive=0` enforcement and property-set denials. Trust chroot-side behavior over `getenforce` text.

## Time skew issue

Chroot inherits device time; here it was ~17 days behind and broke APT release validation with `not valid yet`. If date cannot be changed via `date -s` or `setprop persist.sys.time`, use `Acquire::Check-Valid-Until=false` for apt updates, but prefer fixing clock.

## Hermes install flow inside chroot

- `python3 -m venv /root/.hermes/venv`
- `pip install hermes-agent`
- For Telegram: explicitly verify `python-telegram-bot` is present. This session found `hermes-agent[telegram]` install path left PTB uninstalled; manual `pip install python-telegram-bot==20.8` was required.
- Conflict signature seen: `HTTPXRequest.__init__() got an unexpected keyword argument 'httpx_kwargs'` with PTB 20.8 + hermes-agent 0.18.0. Do not blindly reinstall dependencies on this; log the exact pairing first.

## Hermes process behavior: host vs chroot (2026-07-07)

Running `hermes gateway run` from **inside** chroot vs from the **host** side produces different outcomes:

| Behavior | Host process | Chroot process |
|----------|-------------|----------------|
| `.env` auto-load | ✅ Inherits | ❌ Must be explicit |
| SIGTERM stability | Normal | **Unstable** (reparented to PID 1) |
| environ propagation | Full | Minimal |

**Chroot SIGTERM log**:
```
Shutdown context: signal=SIGTERM under_systemd=yes parent_pid=1
```

**Fix**: Prefer host-side start. If host `/root/` is read-only, use chroot + explicit exports (see `hermes-android-deploy` skill).

**Note**: chroot `/bin/sh` is dash, not bash. Use `. .env` not `source .env`.

## Runtime housekeeping

- Old Termux Hermes + chroot Hermes running same bot token caused locking/conflict risk. Always `ps -ef | grep hermes`, kill all instances, then clear `gateway.lock` and `gateway.pid` before restarting.
- If gateway log only shows `Another gateway instance is already running`, the new start never reached Telegram init. That is a lifecycle artifact, not a Telegram config failure.

## Key paths

- chroot: `/data/local/tmp/chroot/debian/`
- Herme