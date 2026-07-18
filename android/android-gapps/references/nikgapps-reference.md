# NikGapps Reference

NikGapps is an alternative to MindTheGapps with better Android 15 dynamic partition support. For devices where MindTheGapps fails with "Could not mount /mnt/system! Aborting" after signature bypass, NikGapps often works without modification.

## Download channels

NikGapps provides **two download channels** on SourceForge — pick the right one based on variant needs:

### Channel 1: Config-Releases (preferred — latest builds)

https://sourceforge.net/projects/nikgapps/files/Config-Releases/Android-15/

This channel is **updated daily** and has **more modern variants** (essential, etc.). It's the recommended source for recent GApps.

```bash
# List available build dates (380+ releases)
curl -sL "https://sourceforge.net/projects/nikgapps/rss?path=/Config-Releases/Android-15" \
  | grep -oP '<link>[^<]+</link>' | head -10
```

| Latest build | Variant | Size | Downloads/wk |
|-------------|---------|------|-------------|
| 20-Jun-2026 | **a15-essential** (arm64) | 276 MB | **586** |

Download URL pattern:
```
https://sourceforge.net/projects/nikgapps/files/Config-Releases/Android-15/<DD-MMM-YYYY>/NikGapps-a15-<variant>-arm64-15-<YYYYMMDD>-unofficial.zip/download
```

Example (latest as of mid-2026):
```bash
curl -L "https://sourceforge.net/projects/nikgapps/files/Config-Releases/Android-15/20-Jun-2026/NikGapps-a15-essential-arm64-15-20260620-unofficial.zip/download" \
  -o nikgapps.zip --progress-bar
```

### Channel 2: Releases (stable — fewer variants)

https://sourceforge.net/projects/nikgapps/files/Releases/Android-15/

This channel has **multiple variant options** but is updated less frequently (last A15 build: 04-Feb-2026).

```bash
# List available build dates:
curl -sL "https://sourceforge.net/projects/nikgapps/rss?path=/Releases/Android-15" \
  | grep -oP '<link>[^<]+</link>' | head -10
```

| Build Date | Notes |
|-----------|-------|
| 04-Feb-2026 | Latest A15 build (1391 weekly downloads) |
| 16-Jul-2025 | Alternative A15 build |
| 27-Jan-2025 | Earlier A15 build |

Variants available per build folder:
- **core** (126 MB, 665/wk) — Play Store + core services only
- **basic** (244 MB) — core + extras
- **omni** (524 MB)
- **stock** / **full** (900+ MB) — all Google apps
- **go** (188 MB) — lightweight variant

Download URL pattern:
```
https://sourceforge.net/projects/nikgapps/files/Releases/Android-15/<DD-MMM-YYYY>/NikGapps-<variant>-arm64-15-<YYYYMMDD>-signed.zip/download
```

Example (core variant, Feb 2026):
```bash
curl -L "https://sourceforge.net/projects/nikgapps/files/Releases/Android-15/04-Feb-2026/NikGapps-core-arm64-15-20260204-signed.zip/download" \
  -o nikgapps-core.zip --progress-bar
```

### Variant selection guide

| Need | Recommended |
|------|------------|
| Just Play Store + Play Services | **core** (126 MB) or **essential** (276 MB) |
| Plus basic Google apps | **basic** (244 MB) |
| Google experience like stock | **full** (1.1 GB) |
| Minimal footprint | **core** (126 MB) |

### Android 16 builds

Both channels have Android 16 directories too (`/Config-Releases/Android-16/` and `/Releases/Android-16/`). Skip if your device is on LineageOS 22 (A15).

## SourceForge download pattern quirk

SourceForge links **do not** redirect immediately — the `/download` suffix triggers the actual file delivery. Without it, the URL returns an HTML page.

✅ Correct:
```
https://.../NikGapps-core-arm64-15-20260204-signed.zip/download
```

❌ Wrong (returns HTML):
```
https://.../NikGapps-core-arm64-15-20260204-signed.zip
```

The `curl -L` flag handles the final redirect to a SourceForge mirror automatically.

## Installation via LineageOS Recovery

Same procedure as MindTheGapps:

1. Flash LineageOS ROM first (sideload)
2. Without rebooting: **Apply update → Apply from ADB**
3. `adb sideload NikGapps-*.zip`
4. Signature verification will likely *succeed* (NikGapps uses a different signing approach)
5. If it fails, tap "Yes" / "Install anyway"
6. Reboot

## Why NikGapps works where MindTheGapps fails

NikGapps installer script uses a more robust mount-point detection that handles dynamic partitions. It does not rely on `get_block_for_mount_point()` trying legacy by-name symlinks.

## Package contents

NikGapps comes in variants:
- **Core** / **Basic** — minimal Google services (Play Store + Play Services)
- **Full** — includes Google apps (Gmail, Maps, etc.)
- **Essential** — between core and basic, modern middle-ground variant
- **Config-based** installs (customize which apps to include)
