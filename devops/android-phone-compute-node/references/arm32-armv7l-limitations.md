# arm32 (armv7l / armeabi-v7a / 32-bit ARM) Device Limitations

## Detection

Three signals confirm 32-bit ARM:

```bash
adb shell getprop ro.product.cpu.abi       # armeabi-v7a
adb shell uname -m                           # armv7l
adb shell getprop ro.build.version.sdk      # usually <=28 (Android 9) for these devices
```

## OS Upgrade

- **GSI availability**: arm32 GSI images (Generic System Images) are extremely scarce. Project Treble GSI builds (LineageOS, Pixel Experience) are almost exclusively aarch64. The last arm32 GSI releases were Android 10-era (2019-2020). No Android 13+ GSI exists for 32-bit ARM.
- **Official firmware**: Most arm32 devices shipped with Android 8-9 and received no major version upgrade. OEMs ended support at Android 9 (Go edition is common).
- **Bootloader lock**: Many arm32 devices (especially Chinese OEM: DuoQin/Qin phones, ultra-budget devices) have locked bootloaders with no official unlock method. Unlocking requires either (a) a leaked engineering bootloader, (b) a known OEM unlock code, or (c) an exploit — none widely available for these devices.
- **Custom recovery**: TWRP rarely supports arm32 devices. Recovery flashing is typically unavailable.
- **Conclusion**: Do not attempt to upgrade the Android version on an arm32 device. It's almost certainly impossible.

## Python Packages with Rust Extensions

Several popular Python packages use Rust for their core C extensions and target glibc-based Linux. On Termux (Android, Bionic libc), these packages cannot be installed:

| Package | Reason | Status |
|---------|--------|--------|
| `pydantic-core` | Rust C extension, manylinux wheel links glibc | BLOCKED |
| `tokenizers` (HuggingFace) | Rust C extension | BLOCKED |
| `obstore` | Rust C extension, no aarch64 wheel | BLOCKED (also on aarch64) |
| `cryptography` | Has Termux-specific apt package (`python-cryptography`) | ✅ Works via apt |
| `psutil` | Has Termux-specific apt package (`python-psutil`) | ✅ Works via apt |
| `Pillow` | Has Termux-specific apt package (`python-pillow`) | ✅ Works via apt |

### Workaround for Missing Wheels

When a Rust crate has no pre-built Termux wheel, try:

1. **`--target` pip install trick**: Install the glibc manylinux wheel to a temp directory (`pip install --target /tmp --platform manylinux_2_17_armv7l --only-binary :all: --no-deps pkg.whl`), then copy `.so` and `.dist-info` to site-packages. The `.so` will FAIL to load at runtime because it links against glibc, not Bionic — `ModuleNotFoundError: No module named 'pkg._native'`.
2. **Compile from source on phone**: Requires Rust toolchain (`pkg install rust`). On 1GB RAM devices, the compiler itself may OOM (rustc can use 2GB+ for large crates). The Termux `rust` package is 495MB installed, 120MB download.
3. **Skip the dependency**: Check if the upstream project has an alternative code path without the Rust extension. Some packages (pydantic-core) are hard requirements.
4. **Use proot-distro**: Install a full Linux distribution (Debian/Ubuntu) via `proot-distro` inside Termux. This provides glibc compatibility. However, 1GB RAM may be insufficient for both the distro and the Python process.

### Downloading Wheels for arm32

For packages that DO have manylinux armv7l wheels (pydantic-core is one of them), the wheel exists but won't load at runtime due to glibc vs Bionic incompatibility. The file can be installed (with `--target` and `--platform manylinux_2_17_armv7l`) but `import` fails with:

```
ModuleNotFoundError: No module named 'pkg._native'
# where _native is the .so file that can't link against glibc
```

## RAM Constraints

arm32 devices typically have 1-3GB RAM. Android Go edition reserves ~500MB for the system, leaving:
- 1GB device: ~440MB available (e.g. 多亲2/Qin 2, 878MB total, 344MB used, 477MB available, 702MB swap)
- 2GB device: ~1.1GB available
- 3GB device: ~1.9GB available

Hermes Agent (Python) cannot run on 440MB available RAM — Python alone uses 30-50MB, loaded packages 50-100MB, and the agent loop needs headroom. Use the phone for lightweight Python scripts, SSH terminal, or data collection only.
