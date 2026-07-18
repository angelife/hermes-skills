# Kingston DataTraveler 3.0 — macOS dd: Invalid argument

> Session evidence: 2026-07-15, MacBook Pro Intel, macOS 15.7, Kingston DataTraveler 3.0 31GB USB 3.0

## Symptom

```
sudo dd if=/tmp/hybrid_mbr.bin of=/dev/rdisk4 bs=440 count=1
dd: /dev/rdisk4: Invalid argument
1+0 records in
0+0 records out
0 bytes transferred
```

This is NOT affected by:
- Using `/dev/disk4` (block device) → "Resource busy" instead
- Using `dcfldd` → same error
- Using different `bs` values → same error
- `diskutil zeroDisk` → "Operation not supported"
- Erasing with `diskutil eraseDisk ExFAT` → dd still fails
- `osascript do shell script with administrator privileges` → same error

## Root Cause

macOS kernel's USB mass storage driver rejects write requests to certain USB bridge controllers at the transport layer. The Kingston DataTraveler 3.0 uses a bridge chip (likely Phison or Skymedi) that macOS's I/O Kit cannot negotiate correctly for raw writes. This is a hardware-level incompatibility on this specific Mac + USB combination.

`diskutil partitionDisk` works because it goes through Disk Arbitration's privileged IOChannel, which bypasses the raw device write path.

## Workarounds That Work

1. **FAT32 + file copy** (no raw writes needed):
   ```bash
   diskutil partitionDisk /dev/diskX 1 MBR FAT32 NAME 100%
   # mount ISO, cp files
   # Then handle bootloader on a real Linux machine
   ```

2. **GPT + UEFI** (bypasses MBR entirely):
   ```bash
   diskutil partitionDisk /dev/diskX 1 GPT FAT32 NAME 100%
   # copy files + EFI/BOOT/BOOTx64.EFI
   # Boots on UEFI systems without any raw writes
   ```

3. **Do bootloader install on the target machine** (if it runs Linux):
   Plug USB into target → `sudo syslinux --install /dev/sdX1`

4. **Different USB drive** — select one with a different bridge controller.

## What's NOT Blocked

Despite the dd failure, these operations work without sudo:
- `diskutil partitionDisk /dev/diskX 1 MBR FAT32 NAME 100%` ✅
- `diskutil eraseDisk ExFAT NAME GPT /dev/diskX` ✅
- File copy/modification on the mounted volume ✅
- `diskutil eject /dev/diskX` ✅

## Quick Test

To confirm this is the same hardware issue (not permissions or disk state):
```bash
sudo dd if=/dev/zero of=/dev/rdiskX bs=512 count=1
# Returns "Invalid argument" with 0 bytes transferred
# Even on a just-erased disk
```

If the above fails with 0 bytes, no macOS workaround will change the outcome.
