---
name: android-tv-install
description: Install Android TV / Google TV x86 on old laptops or mini PCs to repurpose as TV boxes. Covers version selection, ISO download, USB creation, and installation.
---

# Android TV / Google TV x86 — Old PC to TV Box

Convert a legacy x86 laptop or mini PC into an Android TV box for media consumption.

## Which Version to Pick

| Version | Interface | Google Services | Size | Best For |
|---------|-----------|----------------|------|----------|
| **GTV14** | Google TV (modern UI) | ✅ Built-in | 2.3 GB | Newer hardware (2015+) |
| **ATV14** | Android TV (leanback) | ❌ | 2.4 GB | Clean install, add Gapps manually |
| **GTV11** | Google TV | ✅ Built-in | 2.3 GB | **Older hardware (Celeron/Atom), best balance** |
| **ATV11** | Android TV | ❌ | 2.3 GB | Legacy hardware, lighter |
| **ATV9 (Internet Archive)** | Android TV | ❌ | 933 MB | **Very old hardware (<2012, GMA 4500M, 2GB RAM)** — lightest, best compatibility |

**Recommendation for old hardware (< 2015, ≤2GB RAM, GMA/CedarView GPU):**
→ **GTV11** or **ATV11** (Android 11 based, lighter than 14, still has modern app support)

## Minimum Hardware

- CPU: 1.2 GHz dual-core 64-bit or better (Celeron T3500 ✅)
- RAM: 1 GB minimum, 2 GB recommended
- GPU: 64 MB VRAM minimum (GMA 4500M ✅)
- Storage: 8 GB free for installation
- BIOS: Legacy or UEFI (CSM recommended for very old hardware)

## Download

Source: https://sourceforge.net/projects/androidtv-x86-64/files/

**Download issues (Cloudflare block):** SourceForge may block automated downloads from certain IP ranges. If `curl`/`aria2c` return HTML instead of ISO:
- **CRITICAL: Always `file atv.iso` before writing.** If it shows "HTML document" instead of "ISO 9660", the download failed. Fix the download, don't try to dd it.
- Use the user's browser (Chrome/Firefox) to download directly
- Download on the target Linux machine itself (less likely to be blocked)
- On Mac with local proxy (xray/v2ray): `aria2c --all-proxy="http://127.0.0.1:10808" <url>` — ⚠️ proxy may be SLOW on restricted networks (20KB/s) or drop large files. Try direct connection first.
- Use a direct mirror URL instead of SourceForge's /download redirect
- Alternative sources: **Internet Archive** (`archive.org/details/androidtv-x86`) has ATV9 (933MB) and ATV8 (861MB) — much smaller than SourceForge versions, ideal for old hardware and works when Cloudflare blocks SourceForge.
  - Direct download: `curl -L -o atv9.iso "https://archive.org/download/androidtv-x86/ATV-9-X86-Techinfo-k4.19.105-64bit.iso"`
  - ATV9 was downloaded at 3.9MiB/s via direct connection (no proxy needed)
  - Other files: `ATV-9-x86 Tech info Chrome 23.06.2022...iso` (1GB, with Chrome), `ATV_9_x64-Kern4x-n-5x_Mesa_21.1_2023-12-16.iso` (1.4GB, newer kernel)

```bash
# Attempt automated download (may fail due to Cloudflare)
aria2c -x 4 -s 4 --user-agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36" \
  --referer="https://sourceforge.net/" \
  --dir=/tmp --out=atv.iso \
  "https://downloads.sourceforge.net/projects/androidtv-x86-64/files/GTV11/GTV11-x86_64-MRDTeam-V36T-260520.iso"

# Alternative: direct mirror URL (may need timestamp token)
curl -L -o atv.iso "https://sourceforge.net/projects/androidtv-x86-64/files/GTV11/GTV11-x86_64-MRDTeam-V36T-260520.iso/download"

# Internet Archive (no Cloudflare, fast direct download)
curl -L -o atv9.iso "https://archive.org/download/androidtv-x86/ATV-9-X86-Techinfo-k4.19.105-64bit.iso"
```

## USB Creation

### On macOS

**Problem:** `dd` to `/dev/rdisk4` may fail with `Invalid argument` on some USB drives. This is a macOS kernel-level issue with the raw character device on certain USB controllers.

**Working approach (after format fails):**

1. Format the USB as FAT32 first:
   ```bash
   diskutil partitionDisk /dev/disk4 1 MBR FAT32 ATV11 100%
   ```

2. Write the ISO via Terminal.app (for interactive sudo):
   ```bash
   diskutil unmountDisk /dev/disk4
   sudo dd if=/tmp/atv.iso of=/dev/rdisk4 bs=1m status=progress
   sync
   ```

3. If `dd` to `/dev/rdisk4` still fails with `Invalid argument`:
   - **Use `osascript` to open Terminal.app** which provides an interactive TTY for sudo:
     ```bash
     osascript -e 'tell application "Terminal" to do script "sudo dd if=/tmp/atv.iso of=/dev/rdisk4 bs=1m status=progress; sync"'
     ```
   - Or try the block device `/dev/disk4` instead of raw `/dev/rdisk4`
   - Or use `dcfldd` (install via `brew install dcfldd`) — note: `dcfldd` may also give "Invalid argument" if the real issue is the disk state
   - Or wipe the disk first: `diskutil eraseDisk ExFAT UDISK GPT /dev/disk4`

4. After writing, eject:
   ```bash
   diskutil eject /dev/disk4
   ```

### On Linux (target machine)

Simple, no sudo issues:
```bash
# Find USB device
lsblk
# Write ISO (assuming /dev/sdX)
sudo dd if=atv.iso of=/dev/sdX bs=4m status=progress && sync
```

### Pitfalls

0. **Load this skill FIRST** before starting installation. All USB creation,
   troubleshooting, and workaround info is documented here.
   **When stuck, consult ChatGPT via web-ai-cdp-bridge skill** instead of
   trial-and-error — the user explicitly expects this workflow.

1. **CD-only vs hybrid ISO (critical)** — ATV9 from Internet Archive is a **pure CD-ROM ISO** (`file atv9.iso` shows `ISO 9660 CD-ROM filesystem data`, `fdisk -l` shows empty partition table / `Signature: 0x0`). dding it to USB will produce "operating system not found" because BIOS sees no boot sector. **Official Android-x86 ISOs ARE hybrid** (DOS/MBR boot sector with proper partition table) and work with dd. How to detect CD-only:
   ```bash
   file atv.iso
   # Hybrid: "DOS/MBR boot sector" + "ISO 9660" → OK for dd
   # CD-only: just "ISO 9660 CD-ROM" → NOT OK for dd
   
   fdisk /tmp/atv9.iso 2>/dev/null | grep Signature
   # 0xAA55 = hybrid (has MBR)  |  0x0 = CD-only (no MBR)
   ```
   **Fix for CD-only ISOs:** Extract files to a FAT32 partition instead of raw dd:
   ```bash
   # 1. Mount the ISO on macOS
   hdiutil attach /tmp/atv9.iso
   # Mount point may have a suffix like "20200621_0506 1" (with space)
   VOL=$(ls /Volumes/ | grep -v macos | head -1)
   ls "/Volumes/$VOL/"  # verify: boot/ efi/ kernel/ system.sfs etc.

   # 2. Partition USB as MBR + FAT32 (works WITHOUT sudo on macOS)
   diskutil partitionDisk /dev/diskX 1 MBR FAT32 ATV9 100%

   # 3. Copy all ISO contents
   cp -a "/Volumes/$VOL/" /Volumes/ATV9/
   sync
   # The EFI boot files (efi/boot/BOOTx64.EFI) are now on the USB.
   # For UEFI systems, this is already enough — boot and it works.

   # 4. For legacy BIOS: mark partition active, then install MBR bootstrap
   diskutil unmountDisk /dev/diskX
   printf "flag 1\nwrite\nexit\n" | sudo fdisk -e /dev/rdiskX
   # NOTE: harmless "could not open MBR file /usr/standalone/i386/boot0" may appear.

   # 5. CRITICAL: SYSLINUX needs native Linux to work.
   #    Installing SYSLINUX on a FAT32 partition requires running
   #    `syslinux --install /dev/sdX1` from a Linux environment.
   #    This is the ONLY reliable approach — BPB merge + ldlinux.sys
   #    copy + boot sector write is NOT sufficient (verified 2026-07-15).
   #    The `syslinux` tool patches sector location data into ldlinux.sys
   #    that the boot sector needs to find it. On Mac:
   #    ❌ brew install syslinux — REMOVED from Homebrew. Do NOT attempt.
   #    🟢 Download syslinux tarball from kernel.org (for MBR only):
   #      curl -L -o /tmp/syslinux-6.03.zip "https://mirrors.edge.kernel.org/pub/linux/utils/boot/syslinux/syslinux-6.03.zip"
   #      unzip -o /tmp/syslinux-6.03.zip -d /tmp/syslinux/
   #      sudo dd if=/tmp/syslinux/bios/mbr/mbr.bin of=/dev/rdiskX bs=440 count=1
   #    🟢 Best path: target machine runs Linux? Plug USB in and run:
   #      sudo pacman -S syslinux  # or apt install syslinux
   #      sudo syslinux --install /dev/sdX1
   ```
   Or use `isohybrid` (from syslinux) to convert the ISO (note: may fail on some ISOs).

2. **sudo password on macOS** — non-interactive terminal can't read sudo password. Use `osascript` to spawn Terminal.app, or pipe via the GUI auth dialog (`do shell script "..." with administrator privileges`).

3. **dd: Invalid argument on /dev/rdiskX** — This happens when the USB has a damaged or confused partition table, OR on certain USB controllers (e.g. Kingston DataTraveler 3.0) when macOS kernel rejects the raw write even after a clean `diskutil eraseDisk`. Workarounds:
    - Erase disk first: `diskutil eraseDisk ExFAT TEMP GPT /dev/diskX`
    - Try `/dev/diskX` (block device) instead of `/dev/rdiskX` (raw character)
    - Use `dcfldd` (brew install dcfldd) — but note: same "Invalid argument" if the root is USB controller incompatibility, not dd variant
    - As last resort: use the FAT32 + file copy approach instead of dd
    - ⚠️ **Kingston DataTraveler 3.0 specific**: This can be a HARDWARE incompatibility with macOS. dd writes 0 bytes, NOT fixable by any macOS workaround. Use GPT+UEFI (pitfall 5) or do boot install on a Linux machine. See macos-bootable-usb references/kingston-datatraveler-invalid-argument.md.

4. **Download gets HTML instead of ISO** — SourceForge blocks with Cloudflare. Verify with `file atv.iso` (should show "ISO 9660 CD-ROM", not "HTML document"). Internet Archive is a reliable fallback.

5. **UEFI vs Legacy boot** — Very old hardware (pre-2012, Celeron T3500) may only support Legacy BIOS. Use MBR partition scheme on USB, not GPT.\n   - **If MBR writes fail on macOS** (Invalid argument on Kingston DataTraveler, etc.): switch to GPT partition scheme + UEFI. Create with `diskutil partitionDisk /dev/diskX 1 GPT FAT32 NAME 100%`, then copy ISO files. The `efi/boot/BOOTx64.EFI` from the ISO works as-is on UEFI. Try the laptop's F12 boot menu — if it offers both "USB HDD" (Legacy) and "UEFI: USB", pick the UEFI entry.\n   - On hybrid BIOS/UEFI systems (most ~2010 laptops), the legacy boot path stops working when the USB has a GPT partition table, while the UEFI path works. Vice versa for MBR. **Try both partition schemes.**

6. **SD card + USB reader** — Old BIOS may not support booting from SD card readers. Use a real USB flash drive.

7. **Slow Live CD performance** — Live USB mode on Android TV x86 over USB 2.0 is very slow. This is normal; install to hard disk for acceptable speed.

## Installation

1. Boot from USB → select **Installation - Android TV to harddisk**
2. Select target drive (internal HDD/SSD, not USB)
3. Choose filesystem: **ext4** (recommended)
4. Confirm with Yes
5. After install: reboot, remove USB
6. **Fix stuck at QR code / checking updates screen:**
   ```
   Ctrl+Alt+F1 → console
   pm disable com.tosanthony.tv.networkprovider    # fixes QR code loop
   pm disable com.google.android.tungsten.setupwraith  # fixes update check loop
   Ctrl+Alt+F7 → back to UI
   ```

## Post-Install Tips

- **Enable ARM compatibility** (for Android apps that need ARM libs):
  Copy `houdini9_y.sfs` to USB → plug into ATV → `cp houdini9_y.sfs /system/etc` → `enable_nativebridge` → `reboot`
- **Remote control**: Use a wireless air mouse (with gyroscope) or a standard USB keyboard with a dongle
- **TV apps**: Install 星火电视, 乐看电视, or other IPTV apps via sideloaded APKs or Play Store (GTV versions only)

## Alternative: Kodi on Linux (Arch/Manjaro) TV Kiosk

When Android TV x86 isn't suitable (weird GPU, user wants Linux server dual-use, or Android TV has compatibility issues), install **Kodi** on the existing Linux system as a full-screen TV interface.

### Target Use Case
- Old laptop serves dual purpose: **TV media center** (plugged into screen) + **headless server** (SSH remote maintenance)
- Interface must be simple for elderly users — Kodi's 10-foot UI meets this
- Linux desktop can still be used via SSH, while the display shows only Kodi

### Prerequisites
- Arch Linux or Manjaro installed (tested on Celeron T3500, kernel 7.1.3)
- SSH access to the machine
- x86_64, Intel GPU (i915 driver)

### Step 1: SSH Connection Setup

```bash
# Test connectivity first
ping -c2 192.168.1.X
ssh user@192.168.1.X
```

### Step 2: Passwordless Sudo (for automated maintenance)

```bash
echo "user ALL=(ALL) NOPASSWD:ALL" | sudo tee /etc/sudoers.d/user
```

This allows remote management without interactive password prompts — required for automated maintenance via agent.

### Step 3: Install Kodi

```bash
# Arch/Manjaro
sudo pacman -S kodi

# Verify
which kodi-standalone
# Kodi Media Center 21.x

# Check GPU driver — must have i915 loaded
lspci -k | grep -A 2 VGA
# Kernel driver in use: i915  ← required
```

### Step 4: Configure Auto-Login

```bash
sudo mkdir -p /etc/systemd/system/getty@tty1.service.d

cat << "EOF" | sudo tee /etc/systemd/system/getty@tty1.service.d/autologin.conf
[Service]
ExecStart=
ExecStart=-/usr/bin/agetty --autologin user --noclear %I $TERM
EOF
```

Replace `user` with the actual username. This makes the machine boot straight to a logged-in terminal on tty1.

### Step 5: Kodi Auto-Start

**Option A — .xinitrc + startx (simplest):**

```bash
cat > ~/.xinitrc << "EOF"
#!/bin/sh
exec kodi-standalone
EOF
chmod +x ~/.xinitrc

# In ~/.bash_profile — auto-start on tty1 only:
cat >> ~/.bash_profile << "EOF"
if [ "$(tty)" = "/dev/tty1" ]; then
    exec startx
fi
EOF
```

**Option B — systemd service (when no X session is pre-started):**

```bash
cat << "SERVICE" | sudo tee /etc/systemd/system/kodi.service
[Unit]
Description=Kodi Media Center
After=network.target systemd-user-sessions.service sound.target

[Service]
User=user
Group=user
Type=simple
PAMName=login
ExecStart=/usr/bin/kodi-standalone
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
SERVICE

sudo systemctl enable kodi.service
```

### Step 6: System Health Check (post-setup)

```bash
uname -a              # kernel
uptime                # uptime + load
df -h / /boot         # disk space
free -h               # memory
```

### Pitfalls

| Issue | Cause | Fix |
|-------|-------|------|
| `pacman: unable to lock database` | Previous update interrupted | `sudo rm /var/lib/pacman/db.lck` |
| `mirror URL rejected: Bad hostname` | TUNA mirror sometimes rejects proxy-sourced requests | Switch to Aliyun: `echo -e "Server = https://mirrors.aliyun.com/archlinux/\$repo/os/\$arch" \| sudo tee /etc/pacman.d/mirrorlist && sudo pacman -Syy` |
| `sudo: a terminal is required` | SSH session without TTY | Set passwordless sudo (Step 2) |
| Kodi starts but shows no display | X server conflicts | Only run on tty1; disable other display managers |

### Post-Setup: Chinese Locale (Critical)

Kodi's default font does NOT support Chinese characters. Setting language to Chinese without changing the font first causes garbled text (乱码).

**Correct order:** Install language pack → Change font to Arial → Switch language.

```bash
# 1. Download & install Chinese Simplified language pack
curl -L -o /tmp/zh_cn.zip \
  "https://mirrors.kodi.tv/addons/omega/resource.language.zh_cn/resource.language.zh_cn-11.0.101.zip"
mkdir -p ~/.kodi/addons
cd ~/.kodi/addons && unzip -qo /tmp/zh_cn.zip

# 2. Set font to Arial FIRST (before language change)
sed -i 's|<setting id="lookandfeel.font" default="true">Default</setting>|<setting id="lookandfeel.font">Arial</setting>|' \
  ~/.kodi/userdata/guisettings.xml

# 3. Set language to Chinese
sed -i 's|<setting id="locale.language" default="true">resource.language.en_gb</setting>|<setting id="locale.language">resource.language.zh_cn</setting>|' \
  ~/.kodi/userdata/guisettings.xml

# 4. Set country/timezone
sed -i 's|<setting id="locale.country" default="true">.*</setting>|<setting id="locale.country">China</setting>|' \
  ~/.kodi/userdata/guisettings.xml
```

**Kodi 21 Omega** uses `resource.language.zh_cn` at the `omega` addon repository path. Check the latest version at `https://mirrors.kodi.tv/addons/omega/resource.language.zh_cn/`.

### Post-Setup: Audio (PulseAudio)

```bash
# Install PulseAudio
sudo pacman -S --noconfirm pulseaudio pulseaudio-alsa alsa-utils

# In Kodi guisettings.xml:
sed -i 's|<setting id="audiooutput.audiodevice" default="true">Default</setting>|<setting id="audiooutput.audiodevice">PULSE:Default</setting>|' \
  ~/.kodi/userdata/guisettings.xml
sed -i 's|<setting id="audiooutput.channels" default="true">1</setting>|<setting id="audiooutput.channels">2</setting>|' \
  ~/.kodi/userdata/guisettings.xml
```

### Post-Setup: Chinese Subtitles Plugin

Install the Kodi ChineseSubtitles addon (supports SubHD and Zimuku):

```bash
git clone --depth=1 https://github.com/qzydustin/service.subtitles.chinesesubtitles.git /tmp/chinesesubtitles
cp -r /tmp/chinesesubtitles ~/.kodi/addons/service.subtitles.chinesesubtitles
cp -r /tmp/chinesesubtitles/repository.chinesesubtitles ~/.kodi/addons/
```

### Post-Setup Checklist

Before declaring "done" and rebooting:

- [ ] `sudo systemctl is-enabled sshd` — SSH must survive reboot
- [ ] `sudo systemctl restart sshd` — can you reconnect?
- [ ] No conflicting autostart mechanisms (pick ONE: .bash_profile OR systemd service, not both)
- [ ] Audio output actually works: `speaker-test` or Kodi's audio test
- [ ] Screen saver disabled for TV use: `sed -i 's|screensaver.mode.*|screensaver.mode"></setting>|'`

### User Experience
- Boot → auto-login → Kodi full-screen (TV interface, big icons, remote/keyboard control)
- SSH works in background for remote maintenance at any time
- Alt+F2 switches to terminal for emergency access
- The machine can serve as both a TV and a server simultaneously
