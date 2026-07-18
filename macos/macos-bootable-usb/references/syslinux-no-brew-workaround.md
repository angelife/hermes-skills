# SYSLINUX on macOS — 2026 Status

## brew install syslinux no longer works

`brew install syslinux` → "No available formula with the name 'syslinux'". This formula was
removed from Homebrew core. Do NOT attempt it.

## Alternatives (verified in session 20260715)

### 1. Download syslinux tarball directly

```bash
curl -L -o /tmp/syslinux-6.03.zip \
  "https://mirrors.edge.kernel.org/pub/linux/utils/boot/syslinux/syslinux-6.03.zip"
unzip -o /tmp/syslinux-6.03.zip -d /tmp/syslinux/
```

Extracted files at `/tmp/syslinux/bios/`:
- `mbr/mbr.bin` — MBR bootstrap code (440 bytes, write to /dev/rdiskX)
- `core/ldlinux.bin` — Partition boot sector (512 bytes, needs BPB merge)
- `core/ldlinux.sys` — SYSLINUX loader (copy to FAT32 root)
- `com32/elflink/ldlinux/ldlinux.c32` — SYSLINUX library

### 2. Write MBR bootstrap

```bash
sudo dd if=/tmp/syslinux/bios/mbr/mbr.bin of=/dev/rdiskX bs=440 count=1
```

This writes only to the MBR area (first 440 bytes), NOT the partition boot sector.
Does NOT affect FAT32 partition data.

### 3. Extract MBR from hybrid ISO (fallback)

If syslinux tarball can't be downloaded, extract MBR from any known hybrid ISO:

```bash
dd if=/path/to/hybrid.iso bs=440 count=1 of=/tmp/hybrid_mbr.bin 2>/dev/null
sudo dd if=/tmp/hybrid_mbr.bin of=/dev/rdiskX bs=440 count=1
```

Official Android-x86 9.0 ISOs are hybrid and work for this.

### 4. Install syslinux partition boot sector

This requires the `syslinux` Linux binary which can't run directly on macOS.
Solutions:
a) **Docker**: `docker run --privileged --rm --device=/dev/diskX:/dev/sda alpine:latest sh -c "apk add syslinux && syslinux --install /dev/sda1"`
   ⚠️ Docker may be blocked by Hermes security (mkfs/dd blocklist).
b) **Linux live USB**: Boot any Linux live USB on the target machine, then run
   `sudo syslinux --install /dev/sdX1` where sdX1 is the FAT32 partition.
c) **Target machine itself**: If the target machine already runs Linux (e.g. Manjaro),
   plug the USB in and run `sudo syslinux --install /dev/sdX1` directly.

### 5. Why dd ldlinux.bin corrupts FAT32

`ldlinux.bin` is a raw 512-byte boot sector template. The FAT32 first sector (VBR)
contains a BPB (BIOS Parameter Block) at bytes 11-89 with filesystem geometry
unique to each partition. dd'ing ldlinux.bin directly overwrites the BPB with
dummy values, corrupting the filesystem.

The proper `syslinux --install` tool:
1. Reads the existing VBR → saves the BPB (bytes 11-89)
2. Writes ldlinux.bin → restores bytes 11-89 from saved BPB
3. Patches ldlinux.bin with FAT chain location of ldlinux.sys
4. Creates ldlinux.sys on the filesystem at a specific cluster

### 6. BPB merge approach (Python, manual)

If you have ldlinux.bin and cannot run the native syslinux binary, the
partition boot sector can be patched manually with Python. This IS what
`syslinux --install` does internally.

**Actual verified workflow (from session 20260715):**

```bash
# Step 1: Read current VBR from partition (need sudo via TTY)
# Open a real Terminal.app window via osascript:
osascript -e 'tell application "Terminal" to do script \
  "sudo dd if=/dev/rdiskXs1 bs=512 count=1 of=/tmp/vbr.bin"'
# User types password in the Terminal window. VBR saved to /tmp/vbr.bin.

# Step 2: Merge BPB from actual VBR into ldlinux.bin
python3 -c "
v = bytearray(open('/tmp/vbr.bin', 'rb').read(512))
l = bytearray(open('/tmp/syslinux/bios/core/ldlinux.bin', 'rb').read(512))
l[11:90] = v[11:90]  # Preserve BPB (bytes 11-89)
print(f'BPB saved from partition: {v[11:90].hex()[:32]}...')
open('/tmp/final_ldlinux.bin', 'wb').write(l)
"

# Step 3: Write merged boot sector back (need sudo)
osascript -e 'tell application "Terminal" to do script \
  "sudo dd if=/tmp/final_ldlinux.bin of=/dev/rdiskXs1 bs=512 count=1; sync"'
```

⚠️ Important:
- **Must use `osascript + Terminal.app` for sudo** — opens a real TTY
  where the user can type their password. The non-interactive Hermes shell
  cannot do `sudo`.
- Reading the VBR also needs sudo — same osascript pattern.
- The `sudo dd if=/tmp/vbr.bin` read WILL succeed even when `dd` to the same
  device fails with "Invalid argument" (reading is different from writing).

**Verification:**
```bash
# After writing, you should see SYSLINUX strings in the VBR:
sudo dd if=/dev/rdiskXs1 bs=512 count=1 2>/dev/null | strings | grep -i syslinux
```

**Why this works:**
- Bytes 0-2: JMP instruction (overwritten by ldlinux — OK, SYSLINUX needs its own)
- Bytes 3-10: OEM name (overwritten — cosmetic only)
- **Bytes 11-89: BPB (PRESERVED from real partition — critical for FAT32)**
- Bytes 90-509: Boot code (overwritten — this IS the SYSLINUX boot code)
- Bytes 510-511: 0x55 0xAA boot signature (preserved)

**What this does NOT do** (compared to full `syslinux --install`):\n- The real installer patches the boot sector with the FAT chain location\n  of ldlinux.sys, and writes ldlinux.sys at a specific cluster. Without this\n  step, SYSLINUX CANNOT find ldlinux.sys — the boot sector searches for it\n  at a hardcoded sector address that only the installer knows how to compute.\n- **CRITICAL: BPB merge alone does NOT make the USB bootable.** Even with\n  correct BPB + ldlinux.bin + ldlinux.sys on the FAT32 root, the system will\n  show a blinking cursor at boot because the boot sector can't locate\n  ldlinux.sys without the FAT chain information only `syslinux --install`\n  can write.\n- **The ONLY reliable approach is to run `syslinux --install /dev/sdX1`\n  from a Linux environment** (target machine itself, or a Linux live USB).\n  This is the canonical way and should be stated upfront, not as a fallback.\n\n**Timeline of the misleading claim (retracted):**\nEarlier versions of this document claimed the simplified BPB merge approach\n\"usually works\" for Android-x86. Session 20260715 disproved this: the USB\nfiles were correct, BPB was correct, ldlinux.sys was on the root — but the\nold Celeron laptop still showed a blinking cursor. Only `syslinux --install`\nfrom a native Linux environment solves this properly.

### 7. Kingston DataTraveler 3.0 "Invalid argument"

Some USB controllers (Kingston DataTraveler 3.0 specifically) have a macOS
kernel-level incompatibility where `dd` to `/dev/rdiskX` always returns
`Invalid argument` even after `diskutil eraseDisk`. `/dev/diskX` (block device)
has the same issue. Workaround: use FAT32 + file copy approach instead of raw dd.

### 8. isohybrid for CD-only ISOs

The syslinux package includes `isohybrid` and `isohybrid.pl`. The Perl script can
convert CD-only ISOs to hybrid format (adds MBR + partition table):

```bash
perl /tmp/syslinux/bios/utils/isohybrid.pl /tmp/cd-only.iso
```

⚠️ This failed on the Internet Archive ATV9 ISO with
`"unexpected boot catalog parameters"` — the tool has strict format expectations.
Not all CD ISOs are convertible. If it fails, use the FAT32 + file copy approach.

### 9. Proxy mode vs SourceForge downloads

SourceForge downloads kept cutting off (50-200MB then reset). The root cause
was the proxy being in "rule mode" (PAC/gfwlist) — SourceForge traffic was
routed direct, triggering DPI throttling by the GFW.

**Detection:** If `curl -x http://127.0.0.1:10808 -I https://sourceforge.net`
returns `200` but the actual download drops mid-transfer, proxy is in rule mode.

**Fix:** Switch proxy to "global mode" (all traffic through proxy), or configure
xray/v2ray rules to explicitly route SourceForge through the proxy.
Or: download from **Internet Archive (archive.org)** instead — bypasses both
Cloudflare AND GFW throttling. ATV9 example: 933MB at 3.9MiB/s, no proxy needed.
