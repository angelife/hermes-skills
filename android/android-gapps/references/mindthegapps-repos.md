# MindTheGApps Repository & Version Reference

## Repositories

| Android Version | LineageOS | Repo | Known Latest Release |
|---|---|---|---|
| 16 | 23 | [MindTheGapps/16.0.0-arm](https://github.com/MindTheGapps/16.0.0-arm) | Check latest API |
| **15** | **22** | **[MindTheGapps/15.0.0-arm](https://github.com/MindTheGapps/15.0.0-arm)** | **20250812_214252** |
| 14 | 21 | [MindTheGapps/14.0.0-arm](https://github.com/MindTheGapps/14.0.0-arm) | Check latest |
| 13 | 20 | [MindTheGapps/13.0.0-arm](https://github.com/MindTheGapps/13.0.0-arm) | Check latest |

> ARM64-only repos. For 32-bit ARM, replace `arm` with `arm32` in repo name (e.g. `15.0.0-arm32`).

## Quick Download (Android 15, 2025-08-12 build)

```
https://github.com/MindTheGapps/15.0.0-arm/releases/download/MindTheGapps-15.0.0-arm-20250812_214252/MindTheGapps-15.0.0-arm-20250812_214252.zip
```

**Size:** 268 MB | **Signature:** test-signed (`SignApk`)

## API-based latest-release detection

```bash
# Get the latest download URL for Android 15:
curl -sL "https://api.github.com/repos/MindTheGapps/15.0.0-arm/releases/latest" \
  | grep -E '"tag_name"|"browser_download_url"'
```

## What's included

MindTheGapps contains only core Google services:
- Google Play Services (GmsCore) ~154 MB
- Google Play Store (Phonesky) ~76 MB
- Google Services Framework (GSF)
- Google Calendar Sync
- Google Contacts Sync
- TalkBack
- Velvet (Google Search / Assistant) ~255 MB
- Wellbeing, GoogleRestore, SetupWizard, etc.

No Gmail, Maps, Chrome, YouTube, Drive, Photos, or other Google apps (install from Play Store after boot).
