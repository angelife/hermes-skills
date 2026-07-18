# Android GApps & Recovery — Session Findings

## Mi8 (dipper) Recovery Entry — Hardware Button Required

On Mi8/dipper running LineageOS, `adb reboot recovery` does NOT work — the device boots into the normal system instead. Recovery must be entered via hardware buttons:

**Mi8 Recovery entry**: Hold **Volume Down + Power** simultaneously until the Lineage logo appears, then release.

This is distinct from Mi6/sagit (which uses Volume Up + Power after a brief power-off press). Each device has its own button combo — do not assume `adb reboot recovery` works on any of these devices.

After entering Recovery, ADB shows the device as `sideload` mode. Use `adb sideload <gapps.zip>` to flash.

## MindTheGapps Installation via Recovery Sideload

For LineageOS devices without GApps (no Google Play Services), install MindTheGapps via Recovery:

**Download** (official GitHub releases):
```bash
# LOS 22.2 (Android 15) → MindTheGapps 15.0.0-arm
curl -sL "https://api.github.com/repos/MindTheGapps/15.0.0-arm/releases/latest" \
  | grep '"browser_download_url"' | grep '.zip' | head -1
# → https://github.com/MindTheGapps/15.0.0-arm/releases/download/<tag>/MindTheGapps-<ver>.zip

# Direct (verify version first):
curl -L -o mindthegapps.zip \
  "https://github.com/MindTheGapps/15.0.0-arm/releases/download/MindTheGapps-15.0.0-arm-<date>/MindTheGapps-15.0.0-arm-<date>.zip"
```

**Flash**:
1. Boot into Recovery (hardware buttons, NOT `adb reboot recovery`)
2. `adb devices` shows `a6520fa3	sideload`
3. `adb sideload /path/to/mindthegapps.zip`

**Signature verification failed — this is NORMAL**:
- MindTheGapps is signed with a test/mismatched key
- The Recovery UI shows "signature verification failed"
- The user must tap **"Install anyway"** / **"仍然安装"** on the device screen to confirm
- No workaround needed; the package installs successfully after user confirmation

**After flash**: Reboot system normally from Recovery menu.