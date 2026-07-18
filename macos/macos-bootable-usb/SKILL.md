---
name: macos-bootable-usb
description: Create bootable USB drives on macOS — download ISOs, handle SourceForge/Cloudflare issues, write via dd/osascript, troubleshoot common errors (Invalid argument, Permission denied).
---

# Bootable USB Drive Creation (macOS)

Write bootable OS images to USB on macOS.

## Preferred Tools

| Tool | When to use |
|------|-------------|
| **aria2c** (`brew install aria2`) | Large ISOs >500MB — multi-thread, resume support, handles flaky connections |
| **curl** | Quick small downloads, trivial cases |
| **osascript + Terminal** | Run `sudo dd` without a TTY — opens a real Terminal.app window for password entry |
| **dcfldd** (`brew install dcfldd`) | Alternative to dd when `dd` gives "Invalid argument" on /dev/rdisk* — may also fail if root cause is USB controller incompatibility |
| **osascript `do shell script with administrator privileges`** | Opens GUI password dialog (no Terminal needed). For `dd` only — does NOT work with `asr restore` (ISO not recognized as DMG). |

## Workflow

### 1. Download the ISO

```bash
# Preferred: aria2c (reliable for large files)
aria2c -x 4 -s 4 --max-tries=10 --continue=true \
  --dir=/tmp --out=my-image.iso \
  "<url>"

# Fallback: curl with user-agent
curl -L --max-time 600 \
  -H "User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36" \
  -o /tmp/my-image.iso "<url>"
```

**⚠️ CRITICAL — Verify before writing:** Spent 30+ minutes debugging `dd: Invalid argument` when the real cause was a 65KB HTML page instead of the 2.3GB ISO. **Always run `file /tmp/my-image.iso` before `dd`.** Expected output: `ISO 9660 CD-ROM filesystem data`. If it says `HTML document` or `ASCII text`, the download failed — fix the download, don't try to `dd` it.

**⚠️ SourceForge pitfall:** SourceForge's `/download` redirect often returns an HTML page instead of the ISO. This happens more often through proxy/CGNAT IPs. Verify with `file /tmp/my-image.iso` before any write. If HTML:
- **Through local proxy:** `aria2c --all-proxy="http://127.0.0.1:10808" --user-agent=... --referer=https://sourceforge.net/ <url>` (works when Mac has xray/v2ray)
- Using user-agent + referer: `aria2c --user-agent="Mozilla/5.0" --referer="https://sourceforge.net/" <url>`
- Direct mirror URL from `curl -v -L --head <url> | grep location`
- Download on the target machine (less likely to be Cloudflare-blocked)
- **Internet Archive** (`archive.org/download/<project>/<image>.iso`) — often NOT blocked when SourceForge is. ATV9 example: `archive.org/download/androidtv-x86/ATV-9-X86-Techinfo-k4.19.105-64bit.iso` (933MB, downloaded 3.9MiB/s without proxy)\n- TechSpot, GitHub releases
- **Last resort:** Open in user's browser and download manually

### 2. Identify USB device

```bash
diskutil list external
# Look for (external, physical) — typical names: /dev/disk4
diskutil info /dev/diskX | grep -E "Disk Size:|Device / Media Name:|Protocol:"
```

### 3. Write the image

**Method A: osascript + Terminal (recommended — handles sudo)**

```bash
diskutil unmountDisk /dev/diskX 2>/dev/null
osascript -e '
tell application "Terminal"
  activate
  do script "sudo dd if=/tmp/my-image.iso of=/dev/rdiskX bs=1m status=progress; sync; echo DONE"
end tell
'
```
The user types their password in the Terminal window.

**Method B: Direct sudo (requires TTY)**  
Use this when you have a real terminal (not Hermes' non-interactive shell):

```bash
diskutil unmountDisk /dev/diskX 2>/dev/null
sudo dd if=/tmp/my-image.iso of=/dev/rdiskX bs=1m status=progress
sync
```

**Method C: dcfldd (if dd gives "Invalid argument")**

```bash
brew install dcfldd
sudo dcfldd if=/tmp/my-image.iso of=/dev/rdiskX bs=1M status=on
```

### 4. Verify

After writing:
```bash
diskutil eject /dev/diskX
# Re-insert, check partition scheme
diskutil list external
file -s /dev/diskX  # Should show "DOS/MBR boot sector" or similar
```

**⚠️ Verify ISO is hybrid (USB-bootable) vs CD-only before dd:**
```bash
file /tmp/image.iso
# Hybrid:  "DOS/MBR boot sector" + "ISO 9660 CD-ROM"     → OK for dd
# CD-only: "ISO 9660 CD-ROM filesystem data" (no MBR)    → dd to USB will FAIL to boot

# Confirm with fdisk:
fdisk /tmp/image.iso 2>/dev/null | grep Signature
# 0xAA55 = hybrid (has valid MBR, OK for dd)
# 0x0    = CD-only (empty partition table, NOT OK for dd)
```

**Fix for CD-only ISOs** — extract files to a bootable FAT32 partition instead:
```bash
# 1. Mount the ISO
hdiutil attach /tmp/cd-only.iso
# Mount point may have a suffix like "20200621_0506 1" (with space)
VOL=$(ls /Volumes/ | grep -v macos | head -1)
echo "ISO at: /Volumes/$VOL/"
ls "/Volumes/$VOL/"  # verify: should show boot/ efi/ kernel/ system.sfs etc.

# 2. Partition USB as MBR + FAT32 (works WITHOUT sudo on macOS)
diskutil partitionDisk /dev/diskX 1 MBR FAT32 NAME 100%

# 3. Copy all ISO contents
cp -a "/Volumes/$VOL/" /Volumes/NAME/
sync

# 4. Mark partition active (bootable) — REQUIRED for legacy BIOS
diskutil unmountDisk /dev/diskX
printf "flag 1\nwrite\nexit\n" | sudo fdisk -e /dev/rdiskX
# NOTE: The error "could not open MBR file /usr/standalone/i386/boot0: No such file or directory"
# is HARMLESS on modern macOS — the `flag 1` and `write` commands succeeded, 
# it just couldn't find the Apple boot0 firmware file which is irrelevant here.

# 5. After flag, the partition is marked active. For UEFI boot, the EFI/BOOT/BOOTx64.EFI
# files on the FAT32 partition are auto-detected — this already works.
# For legacy BIOS, a blinking cursor at boot means the MBR bootstrap code is missing.

# 6. If legacy BIOS shows blinking cursor (no boot entry), install MBR bootstrap code:
#    ❌ brew install syslinux — REMOVED from Homebrew (2025+). Do NOT attempt.
#    ✅ Download syslinux tarball directly from kernel.org:
#      curl -L -o /tmp/syslinux-6.03.zip "https://mirrors.edge.kernel.org/pub/linux/utils/boot/syslinux/syslinux-6.03.zip"
#      unzip -o /tmp/syslinux-6.03.zip -d /tmp/syslinux/
#      sudo dd if=/tmp/syslinux/bios/mbr/mbr.bin of=/dev/rdiskX bs=440 count=1
#    Option A: Extract MBR from a known hybrid ISO (e.g. official Android-x86 9.0)
#      dd if=/path/to/hybrid.iso bs=440 count=1 of=/tmp/hybrid_mbr.bin 2>/dev/null
#      sudo dd if=/tmp/hybrid_mbr.bin of=/dev/rdiskX bs=440 count=1
#    Option B: Install syslinux partition boot sector — needs Linux environment
#      Boot any Linux live USB on target machine, then:
#      sudo syslinux --install /dev/sdX1
#    ⚠️ Full details in references/syslinux-no-brew-workaround.md

diskutil eject /dev/diskX
```

## Troubleshooting

| Error | Cause | Fix |
|-------|-------|-----|
| `dd: /dev/rdiskX: Invalid argument` | macOS raw device write issue — often caused by disk in bad state or wrong ISO | Try `diskutil eraseDisk ExFAT TEMP GPT /dev/diskX` first to reset partition table; then `dd` to `/dev/rdiskX`; or try `/dev/diskX` (block device) instead; or use dcfldd |
| `dd: /dev/rdiskX: Invalid argument` even after erase, on known-problematic USB (e.g. Kingston DataTraveler 3.0) | USB bridge controller HARDWARE incompatibility with macOS kernel. dd writes 0 bytes. NOT fixable by dcfldd, different bs values, block devices, or any macOS workaround. | 1️⃣ Use FAT32 + file copy approach (no raw write needed). 2️⃣ Write boot on target machine if it runs Linux (`sudo syslinux --install /dev/sdX1`). 3️⃣ Switch to GPT + UEFI (see Pitfalls) to avoid MBR writes entirely. |
| `dd: /dev/rdiskX: Permission denied` | Need root | Use osascript Terminal method or `sudo` with real TTY |
| `hdiutil: attach failed - image not recognized` | ISO is hybrid format or not a valid disk image | Use `dd` directly (doesn't need mounting); verify ISO with `file` |
| `asr restore: Could not validate source` | `asr` expects DMG, not ISO | Convert with `hdiutil convert -format UDRW` first, or use `dd` instead |
| ISO downloaded as HTML (65KB) | SourceForge/Cloudflare redirect | Use aria2c with user-agent, or direct mirror URL |

## Pitfalls

- **Load this skill FIRST** before starting any USB creation task. All the troubleshooting steps and workarounds are documented here. Starting without loading leads to trial-and-error and repeated failures.
- **💡 CRITICAL WORKFLOW: When stuck after trying a documented approach once → consult web-ai-cdp-bridge (ChatGPT/Gemini).** The user explicitly expects this. Do NOT try 5+ blind workarounds. Summarize the problem, what you tried, and ask for the best path. This is a first-class requirement, not a fallback—the user expresses frustration ("智商不在线") when I keep hitting the same wall without asking for help.
- **GPT + UEFI alternative: If MBR writes fail** (Invalid argument, Resource busy, no sudo), use GPT partition scheme instead. UEFI firmware reads the partition table directly and boots from EFI/BOOT/BOOTx64.EFI on the FAT32 partition — no MBR boot code needed. Create with: `diskutil partitionDisk /dev/diskX 1 GPT FAT32 NAME 100%`. The EFI/boot/BOOTx64.EFI files from the ISO work as-is. This only works on UEFI-capable machines (most x86 hardware from ~2010+). ⚠️ Old hardware (pre-2012, Celeron T3500 era) may have hybrid BIOS/UEFI — try both partition schemes.
- **`diskutil partitionDisk` MBR has NO boot code.** The MBR created by macOS `partitionDisk` contains only the partition table (bytes 446-511). The boot code area (bytes 0-445) is empty. This means even with an active partition and correct VBR, Legacy BIOS will show a blinking cursor. You MUST write MBR bootstrap code separately (from syslinux mbr.bin or hybrid ISO MBR).
- **SYSLINUX needs native Linux to run `syslinux --install`.** Just copying ldlinux.sys + ldlinux.bin + writing the boot sector is NOT enough. The actual `syslinux` binary patches ldlinux.sys with FAT chain location data that the boot sector needs to find it. BPB merge + ldlinux.sys on root = blinking cursor. Only `syslinux --install /dev/sdX1` from a native Linux environment works reliably.
- **If the target machine itself runs Linux, use it for the final syslinux install step.** This avoids needing Docker, a Linux live USB, or fighting macOS dd issues.
- **When stuck, consult ChatGPT/Claude via the web-ai-cdp-bridge skill.** The user explicitly expects this workflow: don't keep trying blind workarounds — summarize the problem and ask for guidance.
- **Always verify the download** with `file <iso>` before writing. An HTML page in disguise wastes 5+ minutes. Also check size matches Content-Length from server.
- **`file` is your first line of defense** — if it says "HTML document" after a download, don't touch `dd`. Fix the download first.
- **`diskutil zeroDisk` is very slow** (31GB can take 30+ min). Use `diskutil eraseDisk` (seconds) instead if you just need a clean partition table.
- **`diskutil partitionDisk /dev/diskX 1 MBR FAT32 NAME 100%`** works WITHOUT sudo for external USB on macOS — useful when you can't get root.
- **Proxy download for Cloudflare-blocked sites**: When SourceForge blocks direct access (Cloudflare), download through local proxy (xray/v2ray on localhost:10808). aria2c: `--all-proxy="http://127.0.0.1:10808"`. curl: `-x http://127.0.0.1:10808`.
- **`/dev/rdiskX` is the raw character device** (faster writes). `/dev/diskX` is the block device (slower but sometimes more compatible).
- **Unmount before writing** — always `diskutil unmountDisk /dev/diskX` first or macOS will block the write.
- **After a failed dd, the disk may be in a bad state.** Run `diskutil eraseDisk ExFAT TEMP GPT /dev/diskX` to reset before retrying.
