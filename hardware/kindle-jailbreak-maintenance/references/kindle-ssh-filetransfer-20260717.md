# Session Reference: KOReader SSH File Transfer Setup (2026-07-17)

## Context

User wanted to transfer the AI Agent book PDF (13.3 MB) to Kindle while in KOReader, without exiting to USB mass storage mode to re-mount.

## Discovery

The Kindle (PW5, KOReader v2026.03) has a built-in SSH plugin at `koreader/plugins/SSH.koplugin/` that runs a patched dropbear SSH server. This works **without** USBNetwork installed — it's part of KOReader itself.

### SSH Plugin Details

From `main.lua`:
- Default port: 2222 (configurable via `G_reader_settings:readSetting("SSH_port")`)
- Key-only auth: enabled via `SSH_key_only_auth` setting (uses `-s` flag)
- No-password mode: enabled via `SSH_allow_no_password` setting (uses `-n` flag)
- Autostart: enabled via `SSH_autostart` setting
- Authorized keys path: `settings/SSH/authorized_keys` (relative to KOReader data dir = `/mnt/us/koreader/`)
- Dropbear binary: `koreader/dropbear` (ELF 32-bit ARM)
- PID file: `/tmp/dropbear_koreader.pid`
- Firewall: opens iptables for the SSH port on Kindle

### Setup Steps (exact commands used)

```bash
# Kindle plugged in via USB, mounted at /Volumes/Kindle/
mkdir -p /Volumes/Kindle/koreader/settings/SSH/
cp ~/.ssh/id_rsa.pub /Volumes/Kindle/koreader/settings/SSH/authorized_keys
diskutil eject /Volumes/Kindle/
```

### Network

- Kindle USBNet IP: 192.168.15.244
- Mac IP: 192.168.15.1
- Ping: 0.26-0.29ms
- Multiple SSH ports open: 22, 222, 2222, 8022 (port 2222 is KOReader's default)

### Key Note

The authorized_keys file must exist **before** the SSH server starts. If the server is already running, it won't pick up a newly written authorized_keys file. The user must restart the SSH server from KOReader menu (Tools → SSH → Stop → Start) after writing the key.
