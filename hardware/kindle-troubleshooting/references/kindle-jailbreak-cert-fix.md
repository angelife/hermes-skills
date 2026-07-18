# Kindle Jailbreak Certificate Fix — Session Log 2026-07-13

## Scenario
- Kindle Paperwhite 5 (11th Gen, "malbec"), firmware 5.16.2.1.1
- Jailbroken via LanguageBreak (version 1.0.2.1, hotfix v2.5.0)
- KOReader installed (v2026.03)
- Home WiFi browser stopped working: "一开始是可以的" (used to work, now doesn't)
- WiFi connects OK, browser starts but pages never load

## Diagnosis from Mac USB Mount

### Device Info
```
Kindle 5.16.2.1.1 (409748 002)
KOReader: v2026.03, KindlePaperWhite5
Hotfix version file: Run Hotfix.run_hotfix → "2.5.0"
```

### Key Log Entries (from system logbackup)
```
E JwtSigner:Error::UnsupportedOperationException while adding headers.
  Message: x509 certificate couldn't be obtained
ADM: terminate called after throwing an instance of 'std::runtime_error'
  what():  Request Signing Failure. StatusCode: 1
E com.lab126.browser:void NetworkManager::init(SoupSession*):
  Unable to read device identifiers
Server returned HTTP response code: 500
  for URL: https://firs-ta-g7g.amazon.com/FirsProxy/getNewDeviceCredentials
```

### Positive Signals (not the problem)
```
I com.lab126.browser:void NetworkManager::updateProxy():
  no proxy set - connection type=wifi reason=connection without proxy
I spectator:conn-done:t=44118.852190:
  (WiFi connection successful)
I spectator:dns-nw-ok:t=44118.851161:
  (DNS OK)
```

### Root Cause Determination
The x509 certificate error is present in EVERY log backup from May 31 onwards — it's persistent, not transient. The LanguageBreak hotfix (v2.5.0) was installed during initial jailbreak but the certificate chain is still broken. The browser depends on Amazon's device identity framework which in turn requires valid certificates → HTTPS fails even though WiFi layer is healthy.

## Fix Attempt 1: LanguageBreak-Specific Hotfix (FAILED)

1. Downloaded `LanguageBreak-16.11.23.tar.gz` from GitHub releases
2. Extracted `Update_hotfix_languagebreak-en-US.bin` (158KB)
3. Copied to `/Volumes/Kindle/` root
4. Ejected Kindle
5. User applies on device: `;dsts` → Update your Kindle → confirm

**Result:** Progress bar stuck at 1% for 5+ minutes → user force-restarted (40s power button) → device showed "Update Error" → returned to previous state. No data loss. This is a known LanguageBreak bug where the hotfix gets stuck when OTA updates are disabled (common jailbreak hardening step).

## Fix Attempt 2: KindleModding Universal Hotfix v2.5.0 (APPLIED — demo mode exited, browser still FAILS)

1. Removed LanguageBreak .bin from `/Volumes/Kindle/`
2. Downloaded `Update_hotfix_universal.bin` (3.7MB) from KindleModding/Hotfix release 2.5.0
3. Copied to `/Volumes/Kindle/` root
4. Ejected Kindle
5. Applied via `;dsts` → Update your Kindle → confirm

**Result:** Update succeeded. Post-verification showed:
- ✅ `.bin` consumed (file gone from root)
- ✅ `.demo` directory GONE (demo mode exited)
- ✅ `DONT_CHECK_BATTERY` GONE
- ✅ `jb` file GONE
- ❌ `mkk` directory NOT created (expected post-LanguageBreak normalisation)
- ✅ `Run Hotfix.run_hotfix` still present (still says "2.5.0")
- ✅ `koreader/`, `extensions/`, `libkh/` survived
- ✅ `version.txt` unchanged (5.16.2.1.1, as expected)

**Browser: still doesn't load pages.** Running `;711` jailbreak bridge health check pending.

**Hypothesis for unresolved browser failure:**
- The x509 certificate error may be more fundamental than the hotfix can fix — the LanguageBreak jailbreak may have permanently altered system files that the hotfix doesn't restore
- The browser may have stopped working due to a DIFFERENT cause (time drift, Amazon backend change, firmware quirk) that coincided with the jailbreak timeline
- The `;711` bridge test will determine if the jailbreak bridge itself is intact

### Universal Hotfix Download Source
```
Release: https://github.com/KindleModding/Hotfix/releases/tag/2.5.0
Direct:  https://github.com/KindleModding/Hotfix/releases/download/2.5.0/Update_hotfix_universal.bin
```

### Relevant Log Files Examined
- `log_backup_260713005412.txt.gz` (most recent) — browser start, certificate errors
- `log_backup_260712172708.txt.gz` — WiFi connection at home (SSID starting with "P", ending with "8")
- `log_backup_260608150150.txt.gz` — Amazon device credential fetch failure

## Commands Used

```bash
# Device info
cat /Volumes/Kindle/system/version.txt
cat /Volumes/Kindle/koreader/version.log

# Log scanning across all backups
for f in /Volumes/Kindle/system/logbackup/log_backup_*.txt.gz; do
  echo "=== $(basename $f) ==="
  gunzip -c "$f" 2>/dev/null | grep -iE "Request Signing|JwtSigner|Unable to read device|browser|getNewDeviceCredentials" | head -5
done

# WiFi info
gunzip -c /Volumes/Kindle/system/logbackup/log_backup_*.txt.gz | grep -i "wmgr:wconn" | head -5

# Browser-specific
gunzip -c /Volumes/Kindle/system/logbackup/log_backup_*.txt.gz | grep -iE "browser|NetworkManager|JunoApplicationManager" | head -10

# Hotfix download
cd /tmp
curl -sL --max-time 30 "https://github.com/notmarek/LanguageBreak/releases/download/1.0.2.1/LanguageBreak-16.11.23.tar.gz" -o LanguageBreak.tar.gz
tar xzf LanguageBreak.tar.gz "./Update_hotfix_languagebreak-en-US.bin"
cp /tmp/Update_hotfix_languagebreak-en-US.bin /Volumes/Kindle/
```

## Pitfalls
- The hotfix is NOT installed via MRInstaller/KUAL — it's a Kindle system update `.bin` file. Place on root, then Settings → Update your Kindle.
- System logs on the user partition (USB-visible) only reveal symptoms. The actual certificate store is on the root partition and NOT accessible via USB.
- "Request Signing Failure" has been logging since day 1 of jailbreak for this device — its presence alone doesn't mean the hotfix wasn't applied. The browser may have worked despite it until a key certificate expired or was rotated.
- LanguageBreak hotfix only works for LanguageBreak-jailbroken devices. Other jailbreak methods (WinterBreak, etc.) need their own hotfix.
