# ATV9 (CD-only ISO) USB Boot Fix

**Problem:** ATV9 from Internet Archive (`ATV-9-X86-Techinfo-k4.19.105-64bit.iso`) is a
pure CD-ROM ISO, NOT hybrid. `file atv9.iso` shows `ISO 9660 CD-ROM filesystem data`
without `DOS/MBR boot sector`. `fdisk` shows `Signature: 0x0` (empty partition table).

dding this ISO to USB gives "operating system not found" on legacy BIOS.

## Detection

```bash
file atv9.iso
# CD-only: "ISO 9660 CD-ROM filesystem data" (no "DOS/MBR boot sector")
fdisk /tmp/atv9.iso 2>/dev/null | grep Signature
# 0x0 (not 0xAA55) = CD-only
```

## Fix: FAT32 + file copy + SYSLINUX

### On macOS (step by step)

```bash
# 1. Mount ISO
hdiutil attach /tmp/atv9.iso
VOL=$(ls /Volumes/ | grep -v macos | head -1)
echo "ISO at: /Volumes/$VOL/"  # typically "20200621_0506 1" (with space)

# 2. Partition USB as MBR + FAT32 (works WITHOUT sudo)
diskutil partitionDisk /dev/diskX 1 MBR FAT32 ATV9 100%

# 3. Copy files
cp -a "/Volumes/$VOL/" /Volumes/ATV9/
ls /Volumes/ATV9/  # verify: boot/ efi/ kernel/ system.sfs etc.

# 4. Mark partition active (bootable)
diskutil unmountDisk /dev/diskX
printf "flag 1\nwrite\nexit\n" | sudo fdisk -e /dev/rdiskX
# The "could not open MBR file /usr/standalone/i386/boot0" error is HARMLESS

# 5. UEFI boot already works (EFI/BOOT/BOOTx64.EFI files are copied)
# For legacy BIOS, install MBR + partition boot sector (see below)

## 6. SYSLINUX Partition Boot Sector

**CRITICAL — Read this first. BPB merge alone does NOT work.**

Running `syslinux --install` does more than writing the boot sector.
It also patches the boot sector with the cluster location of `ldlinux.sys`
on the actual formatted filesystem. Without this patching, the boot sector
CANNOT find ldlinux.sys and the system shows a blinking cursor.

**The BPB merge approach (Python) documented below will NOT make the USB
bootable.** It was tested extensively in session 20260715 — files were
correct, BPB was correct, ldlinux.sys was present — but legacy BIOS still
showed a blinking cursor.

**The ONLY reliable fix:** Run `sudo syslinux --install /dev/sdX1` from a
native Linux environment. The target machine running Linux is ideal.

See the `macos-bootable-usb` skill's `references/syslinux-no-brew-workaround.md`
for:

- **brew install syslinux is REMOVED** from Homebrew (2025+)
- **Downloading syslinux tarball** directly from kernel.org (avoids brew)
- **MBR bootstrap write**: `sudo dd if=mbr.bin of=/dev/rdiskX bs=440 count=1`
- **BPB merge (Python)**: Read VBR → merge BPB → write patched ldlinux.bin
- **isohybrid** for CD→hybrid conversion (may fail on some ISOs)
- **Simplest path**: Boot any Linux live USB on target machine, then
  `sudo syslinux --install /dev/sdX1`
- **Target machine runs Linux?** Plug USB in, `sudo pacman -S syslinux` (Arch/manjaro),
  then `sudo syslinux --install /dev/sdX1`
```

## Hardware Notes

- **Lenovo Celeron T3500 (~2010)**: Legacy BIOS only. Needs MBR bootstrap + SYSLINUX.
- **F12 boot menu**: Works on Lenovo even without BIOS password.
- **Kingston DataTraveler 3.0**: Known `dd: Invalid argument` issue on macOS.
  Use FAT32 + file copy instead.
- **Installing to hard disk**: After booting from USB → "Installation - Android TV to harddisk"
  → choose ext4 → internal HDD. Much faster than Live USB mode.
