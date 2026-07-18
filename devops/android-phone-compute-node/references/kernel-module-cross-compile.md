# Cross-Compiling Out-of-Tree Kernel Modules for Android Phones

Adding a kernel driver (e.g., USB Ethernet chipset) to an Android phone when the driver is not already compiled into the kernel. This is typically needed when the built-in kernel lacks support for a specific USB device (e.g., RTL8153B version 0x6010 on kernel 4.4).

## Prerequisites

- Phone with unlocked bootloader + root (Magisk or userdebug)
- ADB access (USB or TCP)
- Kernel source matching the device's running kernel (same branch/tag)
- Cross-compiler toolchain (aarch64-linux-gnu-gcc, or clang)
- Docker or similar environment to run the toolchain (macOS host typically lacks aarch64 cross compiler)

## Step 0: Verify Module Loading Is Possible

**THIS IS THE MOST IMPORTANT CHECK.** Before spending hours on compilation, verify the running kernel actually supports loading external modules.

```bash
# Check if modules directory exists
adb shell "ls -la /lib/modules/ /vendor/lib/modules/ 2>&1"
# If empty or "No such file or directory" → module loading is DISABLED

# Check kernel config
adb shell "zcat /proc/config.gz 2>/dev/null | grep -E 'CONFIG_MODULES|MODULE_SIG|LOCK_DOWN'"

# Try loading ANY module (even a dummy one) to verify
insmod /data/local/tmp/test.ko
# strace to see the real error:
strace insmod /data/local/tmp/test.ko 2>&1 | grep -E "finit_module|EPERM|ENOEXEC"
```

**Common blockers:**
- `finit_module → EPERM` (Operation not permitted): Kernel has MODULE_SIG_FORCE=y or Lockdown enabled. Out-of-tree modules cannot be loaded without recompiling the kernel.
- `finit_module → ENOEXEC`: Module format error (vermagic mismatch, modversions CRC mismatch, or build structure issue).
- `/lib/modules/` empty or missing: The kernel was compiled with `CONFIG_MODULES=n` (built-in only). No module loading support at all.

**LineageOS kernels typically block module loading** — they compile all drivers as built-in (`=y`) and either disable `CONFIG_MODULES` or enable `CONFIG_MODULE_SIG_FORCE` with a device-specific signing key. If the check shows module loading is impossible, the only path is to recompile the entire kernel with the missing driver built-in (`=y`), not as a module.

## Step 1: Set Up the Kernel Source Tree

```bash
# Clone matching kernel source (e.g. LineageOS kernel for your device)
git clone --depth 1 -b lineage-22.2 https://github.com/LineageOS/android_kernel_xiaomi_sagit.git linux-dir
cd linux-dir

# Copy the running kernel's config
adb shell "zcat /proc/config.gz | base64" | base64 -d > .config

# Or from a saved defconfig:
make ARCH=arm64 <device>_defconfig

# Set up build environment
make ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- prepare modules_prepare
```

## Step 2: Critical Build System Fixes (Kernel 4.4 + GCC 14)

When using GCC 14 (aarch64-linux-gnu-gcc-14) with a kernel 4.4 source tree, two bugs manifest:

### Bug A: MODULE_INFO `unused` attribute overrides `__used`

The `__MODULE_INFO` macro in `include/linux/moduleparam.h` has:

```c
// Buggy (kernel 4.4):
__used __attribute__((section(".modinfo"), unused, aligned(1)))

// Fixed:
__used __attribute__((section(".modinfo"), aligned(1)))
```

The `unused` attribute in the attribute list is parsed as a standalone attribute, and it overrides the earlier `__used` attribute. This causes the compiler to ELIMINATE all MODULE_INFO data (vermagic, license, author, description, aliases) from the compiled object file, even though `__used` is specified.

**Fix:** Remove `unused` from the attribute list:

```bash
sed -i 's/section(".modinfo"), unused, aligned(1)/section(".modinfo"), aligned(1)/' \
  include/linux/moduleparam.h
```

**Verification:** After the fix, the final .ko's `.modinfo` section should contain `vermagic=...`:

```bash
strings drivers/net/usb/r8153b.ko | grep vermagic
objdump -s -j .modinfo drivers/net/usb/r8153b.ko
```

### Bug B: `.mod.c` compiled without `-DMODULE`

The kernel build system for external modules (`M=...`) does not pass `-DMODULE` to the `.mod.c` compilation step. The `.mod.c` file contains:

```c
MODULE_INFO(vermagic, VERMAGIC_STRING);
```

Without `-DMODULE`, the preprocessor takes the `#else /* !MODULE */` branch:

```c
#define __MODULE_INFO(tag, name, info) struct __UNIQUE_ID(name) {}
```

Result: A zero-sized struct replaces the vermagic const char array. The module has NO vermagic, NO license, NO author info, etc.

**Detection:**
```bash
# Preprocess the .mod.c — if you see "struct __UNIQUE_ID_vermagicX {};" instead of
# "static const char __UNIQUE_ID_vermagicX[]", then MODULE is NOT defined:
aarch64-linux-gnu-gcc -E -DMODULE ... file.mod.c | grep UNIQUE_ID
```

**Fix (two options):**

Option A — Pass `-DMODULE` explicitly in KBUILD_CFLAGS_MODULE:
```bash
make ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- \
  M=drivers/net/usb \
  KBUILD_CFLAGS_MODULE="-DMODULE -mcmodel=small" \
  modules
```

Option B — Force-define MODULE in the kernel config:
```bash
# Add to include/generated/autoconf.h or to the compiler flags globally
echo '#define MODULE 1' >> include/generated/autoconf.h
```

## Step 3: Cross-Compiler GOTCHAs

### GCC `-mcmodel=large -fPIC` incompatibility

Kernel 4.4's `arch/arm64/Makefile` adds `-mcmodel=large` to `KBUILD_CFLAGS_MODULE`. This flag is incompatible with `-fPIC` in GCC 14 on aarch64:

```
cc1: sorry, unimplemented: code model 'large' with '-fPIC'
```

**Fix:** Override with `-mcmodel=small`:

```bash
make ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- \
  KBUILD_CFLAGS_MODULE="-mcmodel=small" \
  modules
```

The `large` code model is only needed for very large kernel modules (>128MB text size). For a USB Ethernet driver, `small` is fine.

### UTS_RELEASE double suffix issue

When `CONFIG_LOCALVERSION_AUTO=y` is set AND the kernel source has a `.git` directory with uncommitted changes (or is a shallow clone), `scripts/setlocalversion` adds a `+` suffix ON TOP of the configured `CONFIG_LOCALVERSION`. This results in a doubled suffix:

```
UTS_RELEASE = "4.4.302-perf+-perf+"  # doubled!
```

Instead of the expected:
```
UTS_RELEASE = "4.4.302-perf+"
```

Modules compiled with the wrong UTS_RELEASE fail the vermagic check.

**Fix:** Disable LOCALVERSION_AUTO and force the correct release:
```bash
scripts/config --disable CONFIG_LOCALVERSION_AUTO
echo "#define UTS_RELEASE \"4.4.302-perf+\"" > include/generated/utsrelease.h
chmod 444 include/generated/utsrelease.h  # prevent overwrite
```

## Step 4: Full Build Command (Fixed)

```bash
# Fix bug A (once)
sed -i 's/section(".modinfo"), unused, aligned(1)/section(".modinfo"), aligned(1)/' \
  include/linux/moduleparam.h

# Fix utsrelease (once)
echo "#define UTS_RELEASE \"$(adb shell uname -r)\"" > include/generated/utsrelease.h
chmod 444 include/generated/utsrelease.h

# Build (applies -DMODULE for bug B + -mcmodel=small for GCC compat)
make ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- \
  M=drivers/net/usb \
  KBUILD_CFLAGS_MODULE="-DMODULE -mcmodel=small" \
  modules
```

## Step 5: Loading on the Phone

If Step 0 confirmed module loading is possible:

```bash
# Push and load
adb push <module>.ko /data/local/tmp/
adb shell su root -c "insmod /data/local/tmp/<module>.ko"
adb shell dmesg | tail -10
```

## Step 6: MODVERSIONS CRC Handling

When the kernel has `CONFIG_MODVERSIONS=y` (check with `zcat /proc/config.gz | grep MODVERSIONS`), every loaded module must carry a `__versions` section with CRC checksums matching the running kernel's exported symbols. Without matching CRCs, the module fails with:

```
r8153b: disagrees about version of symbol module_layout
```

### Vermagic + MODVERSIONS Interaction

When a module is compiled with `CONFIG_MODVERSIONS=y`, its vermagic string gains the tag `modversions`. The kernel's `same_magic()` function handles this as follows:

```c
static inline int same_magic(const char *amagic, const char *bmagic,
                             bool has_crcs)
{
    if (has_crcs) {
        amagic += strcspn(amagic, " ");
        bmagic += strcspn(bmagic, " ");
    }
    return strcmp(amagic, bmagic) == 0;
}
```

With `has_crcs=true` (module has __versions section):
- Strips only the version number (first token before space)
- Compares the ENTIRE remaining suffix byte-exact (SMP, PREEMPT, mod_unload, aarch64 — all must match exactly, including single spaces)
- Whitespace IS significant — 12 spaces vs 1 space is a mismatch

So if the running kernel was compiled WITHOUT CONFIG_MODVERSIONS (its vermagic has no `modversions` tag), the module vermagic `4.4.302-perf SMP preempt mod_unload modversions aarch64` will NOT match the kernel's `4.4.302-perf SMP preempt mod_unload aarch64` even with `has_crcs=true`.

### Workaround: Build with MODVERSIONS=y but Strip the Tag

Compile with CONFIG_MODVERSIONS=y (so modpost generates the `____versions[]` array with CRCs), but patch vermagic.h to force MODULE_VERMAGIC_MODVERSIONS to empty string:

```bash
cat > include/linux/vermagic.h << 'VERMAGIC_EOF'
#include <generated/utsrelease.h>
#ifdef CONFIG_SMP
#define MODULE_VERMAGIC_SMP "SMP "
#else
#define MODULE_VERMAGIC_SMP ""
#endif
#ifdef CONFIG_PREEMPT
#define MODULE_VERMAGIC_PREEMPT "preempt "
#else
#define MODULE_VERMAGIC_PREEMPT ""
#endif
#ifdef CONFIG_MODULE_UNLOAD
#define MODULE_VERMAGIC_MODULE_UNLOAD "mod_unload "
#else
#define MODULE_VERMAGIC_MODULE_UNLOAD ""
#endif
/* Intentionally empty -- running kernel has no modversions tag */
#define MODULE_VERMAGIC_MODVERSIONS ""
#ifndef MODULE_ARCH_VERMAGIC
#define MODULE_ARCH_VERMAGIC ""
#endif
#define VERMAGIC_STRING \
	UTS_RELEASE " " \
	MODULE_VERMAGIC_SMP MODULE_VERMAGIC_PREEMPT \
	MODULE_VERMAGIC_MODULE_UNLOAD \
	MODULE_VERMAGIC_MODVERSIONS \
	MODULE_ARCH_VERMAGIC
VERMAGIC_EOF
```

### CRC Mismatch Diagnosis

| Error | Meaning | Likely Cause |
|-------|---------|-------------|
| `no symbol version for module_layout` | Module has empty __versions section | Build didn't find kernel CRCs (needs vmlinux) |
| `disagrees about version of symbol module_layout` | CRC in __versions doesn't match kernel's | Running kernel's struct types differ from build tree |

If the second error: the running kernel has a different `struct module` layout, likely from having many more CONFIG options enabled (e.g., 4009 vs 2463). Options like CONFIG_TRACEPOINTS, CONFIG_GENERIC_BUG, CONFIG_KALLSYMS, CONFIG_TRACING all add `#ifdef` fields to struct module, changing module_layout's CRC.

### Reading CRC from vmlinux

```bash
# CRC value from built vmlinux
nm vmlinux | grep __crc_module_layout
# → 00000000b8cfb3df A __crc_module_layout  (value IS the CRC for module_layout)
```

### LineageOS Module Loading Specifics

Mi6 (kernel 4.4.302-perf+, Magisk root):
- `CONFIG_MODULES=y`, `CONFIG_MODULE_UNLOAD=y`
- `CONFIG_MODULE_FORCE_LOAD=n` — `try_to_force_load()` will always fail
- `CONFIG_MODULE_SIG=n` — no signature check
- `finit_module(flags=1)` blocked (ENOEXEC, no dmesg)
- `/dev/mem`, `/proc/kcore`: absent — no way to read kernel memory from userspace
- `kallsyms_lookup_name` exported but kernel-space only
- Running kernel compiled with **Clang 19** (not GCC)
- vermagic: `4.4.302-perf+ SMP PREEMPT mod_unload aarch64` (note `PREEMPT` uppercase in version string but vermagic uses lowercase)

If module loading fails at the CRC stage and you cannot fix it, the only path is rebuilding the entire kernel with the driver built-in (`=y`).

### Binary Vermagic Patching (Alternative)

Instead of the vermagic.h approach, patch the vermagic directly in the .ko ELF:

```python
# Replace "modversions " (12 bytes) in the .modinfo section
# Preserve total length to avoid breaking section iteration
import os
data = open('r8153b.ko', 'rb').read()
idx = data.find(b'modversions ')
if idx >= 0:
    data = data[:idx] + b'            ' + data[idx+12:]
    open('r8153b.ko', 'wb').write(data)
```

Note: the .modinfo section is parsed by `next_string()` which iterates byte-by-byte. Shortening a string shifts subsequent strings — offsets must be preserved. The safest patch replaces "modversions " with spaces of equal length.

### Getting CRCs Without Building Full Kernel

The `____versions[]` array in `.mod.c` is populated by `scripts/mod/modpost`, which reads CRCs from `vmlinux` (via ELF sections) or `Module.symvers`. To generate CRCs without building the full kernel:

1. Extract the running kernel's config: `adb shell zcat /proc/config.gz | base64 | base64 -d > .config`
2. `make olddefconfig` to normalize
3. Build vmlinux first (takes time but generates CRCs for all exported symbols): `make -j$(nproc) ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- vmlinux`
4. Then rebuild the module: `make ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- M=drivers/net/usb modules`

The CRC values come from genksyms, which computes CRC-32 from the expanded type definitions in the preprocessed C source. The CRC depends on the header file content, not the compiler that produced the preprocessed output.

## Built-in Driver Check (Before Compiling Anything)

Many Qualcomm-based Android kernels compile USB Ethernet drivers as built-in (`=y`), especially on newer kernel versions. **Always check first:**

```bash
adb shell "zcat /proc/config.gz 2>/dev/null | grep -E 'USB_RTL815|AX88179|CDCETHER|CDC_NCM|USB_NET_RNDIS'"
```

If `CONFIG_USB_RTL8152=y` is present, **both RTL8152 (100Mbps) and RTL8153 (1000Mbps) are supported** — they share the same driver. No module compilation needed.

Device-specific findings:
- **Mi8 (dipper, kernel 4.9.337)**: `CONFIG_USB_RTL8150=y`, `CONFIG_USB_RTL8152=y` both built-in. No module needed. However, LineageOS 14 (user build) has `su` permission denied — cannot insmod or read dmesg as root. Requires userdebug build or Magisk root for module loading.
- **Mi6 (sagit, kernel 4.4.302)**: `CONFIG_USB_RTL8152=y` is NOT present (no USB Ethernet driver built-in). Module compilation required.

## Reality Check

Most LineageOS / stock Android kernels from the 4.x era **cannot load external modules** at all. Even when the compilation succeeds, loading is blocked by:

- `CONFIG_MODULES=n` → kernel has zero module loading code
- `CONFIG_MODULE_SIG_FORCE=y` → only signed modules from the device vendor's key are accepted
- Lockdown mode (CONFIG_LOCK_DOWN_IN_KERNEL_MODE) → prevents all module loading

**If any of these are true, module compilation is a dead end.** The only working approaches are:

1. **Recompile the entire kernel** with the needed driver built-in (`=y`) and `CONFIG_MODULE_SIG_FORCE=n`
2. **Use a different USB chipset** that the existing kernel already supports (check with `zcat /proc/config.gz | grep "USB_"`)
3. **Use a secondary device** (e.g., Mi6) that can load modules or has a different kernel setup

## Verification Tests

```bash
# Check vermagic in compiled .ko
strings r8153b.ko | grep vermagic
# Expected: vermagic=4.4.302-perf+ SMP preempt mod_unload aarch64

# Check .modinfo section is complete (license, author, description, alias, depends, vermagic)
objdump -s -j .modinfo r8153b.ko

# Load test on host (if same arch/docker — won't actually work but checks format)
modprobe --first-time r8153b.ko 2>&1
```

## When All Else Fails

If module loading is blocked and kernel rebuilding is infeasible (no source tree matching the running kernel, no build environment, etc.):

- **ADB Reverse proxy** (`scripts/adb-http-connect-proxy.py`) tunnels HTTP/HTTPS through the Mac — no kernel changes needed
- **Built-in CDC ECM/NCM**: Some USB Ethernet adapters can switch to CDC ECM mode which the phone's kernel likely already supports (`CONFIG_USB_CDCETHER=y` is common on Qualcomm kernels)
- **RTL8153 on kernel 4.4**: Even if the driver is built-in (`CONFIG_USB_RTL8152=y`), it may not recognize newer chip revisions (0x6010). Upgrading to a newer kernel (or patching the driver's version table) requires a full kernel rebuild — not possible via a loadable module.

### OTG Caveat: USB Port Must Be in Host Mode

For a USB Ethernet adapter to work on a phone, the USB-C port must be in **host/OTG mode**, not device/peripheral mode. When the phone is connected to a computer for ADB, the DWC3 controller is locked in peripheral mode and cannot drive a USB Ethernet adapter on the same physical port.

**Indications of peripheral mode:**
- `sys.usb.config=mtp,adb` or `sys.usb.config=adb`
- ADB shell shows `eth0` absent even when adapter is physically connected

**To use the adapter:**
- Disconnect the USB cable from the computer
- Connect the adapter via an OTG cable or USB-C hub
- The DWC3 controller (Qualcomm) auto-switches to host mode on OTG insertion
- The interface appears as `eth0` (kernel 4.x) or `usb0` (kernel 5+/Android 11+)
- Best practice: pre-configure ADB over TCP (`adb tcpip 5555`) or SSH before disconnecting USB ADB

**If auto-switch fails:**
```bash
# Force host mode (requires root, controller path may vary)
echo host > /sys/bus/platform/drivers/msm-dwc3/a600000.ssusb/mode
# Confirm the controller path first with:
ls /sys/bus/platform/drivers/msm-dwc3/
```
