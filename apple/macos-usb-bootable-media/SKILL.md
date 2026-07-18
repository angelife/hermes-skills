---
name: macos-usb-bootable-media
description: >-
  Create bootable USB drives on macOS — download ISOs, find USB devices, write with dd, handle the
  headless sudo limitation via osascript + Terminal.app, verify writes, and eject safely.
  Covers all OS/ISO types: Linux, Android-x86, Windows, recovery images.
---

# macOS Bootable USB Media

Create bootable USB drives from ISOs on macOS. The key challenge is `sudo dd` requires an
interactive TTY, which headless agents don't have — solved via `osascript` to open a real
Terminal window.

## Workflow

### 1. Download the ISO

Prefer `aria2c` for large files — it handles retries, multi-connection, and supports resumption:

```bash
aria2c -x 4 -s 4 --max-tries=10 --continue=true \
  --user-agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36" \
  --referer="https://sourceforge.net/" \
  --dir=/tmp --out=<name>.iso \
  "<download-url>"
```

For SourceForge, use `downloads.sourceforge.net/project/...` as the direct mirror URL
(not the `/download` redirector which needs cookies).

If `aria2c` is not installed:
```bash
brew install aria2
```

For small files (<500MB), plain `curl -L --max-time <N>` works.

### 2. Identify the USB device

```bash
diskutil list external
# Look for (external, physical) — usually /dev/disk4
diskutil info /dev/disk4  # confirm size matches your USB stick
```

Ignore internal disks (disk0), synthesized volumes (disk1), and disk images (disk2-3).

### 3. Unmount (do not eject)

```bash
diskutil unmountDisk /dev/disk4
```

This keeps the device registered (still at `/dev/rdisk4`) but unmounts any volumes.

### 4. Write the ISO — headless sudo workaround

`sudo dd` requires an interactive terminal. On macOS, bypass this by popping open a
Terminal.app window via `osascript`:

```bash
osascript -e '
tell application "Terminal"
  activate
  do script "diskutil unmountDisk /dev/disk4 2>/dev/null; \
    sudo dd if=/tmp/<iso>.iso of=/dev/rdisk4 bs=4m status=progress; \
    sync; echo ===== DONE ====="
end tell
'
```

The user sees a Terminal window with the `dd` running and types their sudo password there.
**Do NOT use** `sudo -S` or echo password — that is insecure and macOS SIP rejects it.

After the write completes, the device is automatically ejected by `diskutil eject` at end,
or you can prompt the user to eject manually:
```bash
diskutil eject /dev/disk4
```

### 5. Verify (optional)

```bash
# Check partition table changed
diskutil list external

# Read first sector — hybrid ISO should show boot data
dd if=/dev/rdisk4 bs=512 count=1 2>/dev/null | strings | head -3
```

## Pitfalls

- **`sudo dd` silently fails in headless context** — `sudo: a terminal is required to read the password`.
  Always use `osascript` to open a Terminal.app window; never try `-S` or piped password.
- **`osascript` can time out if the user dismisses the dialog** — check the device after
  the command returns to verify write happened. Use `diskutil list external` and look for
  changed partition scheme.
- **SD card readers are unreliable for boot** — Many BIOS/UEFI don't recognize `SD/MMC`
  via USB reader as a bootable device. Use a real USB flash drive (DataTraveler, etc.).
- **`diskutil partitionDisk` works WITHOUT sudo on external USB** — macOS allows\n  non-root users to repartition removable media. Use this for FAT32 + file copy approach\n  when raw `dd` fails (e.g. Kingston DataTraveler 3.0 \"Invalid argument\").\n- **Hybrid ISOs** (like Android-x86) must be written raw with `dd`, not extracted as files\n  to a FAT32 partition. Only a raw write preserves the hybrid MBR that makes it bootable.\n  **Exception:** CD-only ISOs (no MBR, `Signature: 0x0`) cannot be dd'd — extract files\n  to FAT32 + install SYSLINUX instead. See `macos-bootable-usb` skill for CD-only fix.
- **Large downloads can be interrupted** — use `aria2c --continue=true` for resumption.
  Plain `curl` does not resume interrupted downloads reliably on SourceForge.
- **SourceForge downloads** use `Location` redirects. Pass the direct mirror URL
  (`downloads.sourceforge.net/project/...`) to curl/aria2c, not the `/download` front page URL.

## Related

- `macos-app-troubleshooting` — if the USB write triggers macOS permission dialogs
- `computer-use` — for physically interacting with disk utility GUI (last resort)
