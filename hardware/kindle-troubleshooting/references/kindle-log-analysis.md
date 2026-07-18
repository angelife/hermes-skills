# Kindle System Log Analysis — Field Notes

## Where Logs Live

When connected via USB, the Kindle mounts at `/Volumes/Kindle/`. System logs are under:

```
/Volumes/Kindle/system/logbackup/log_backup_YYMMDDHHMMSS.txt.gz
```

Filenames encode the date: `log_backup_260713005412.txt.gz` = 2026-07-13 00:54:12.

The logs are rotated backups. The latest file is the most recent snapshot.

## Reading Compressed Logs

```bash
# Read specific patterns
gunzip -c /Volumes/Kindle/system/logbackup/log_backup_260713005412.txt.gz | grep -iE "wifi|network|dns|proxy|browser|error|fail"

# Iterate all logs
for f in /Volumes/Kindle/system/logbackup/*.gz; do
  echo "=== $(basename $f) ==="
  gunzip -c "$f" 2>/dev/null | grep -iE "pattern" | tail -5
done
```

## Process Name Reference

| Log prefix | Process | Description |
|------------|---------|-------------|
| `mesquite[]` | Browser | Kindle's Experimental Browser process (WebKit-based) |
| `wifid[]` | WiFi daemon | Connection scanning, association, DHCP, DNS |
| `ADM:` | Amazon Device Messaging | Auth signing, push notifications |
| `cvm[]` | Java VM (KAF) | Kindle Application Framework — runs UI, network services |
| `KPPMainApp[]` | Home/Launcher | Main Kindle home screen app |
| `tmd[]` | Transfer Manager Download | HTTP download engine (metrics for SSL/TLS handshake timing) |
| `powerd[]` | Power daemon | Battery, charging, screen state |
| `odhcp6c[]` | DHCPv6 client | IPv6 address assignment |
| `bcm[]` | Battery charge manager | Battery metrics |
| `JunoStatusBarDriver[]` | Status bar | WiFi signal strength display |
| `lipc-*` | LIPC bus | Inter-process communication (events) |

## Error Signature Reference

### Certificate/Signing Failures (Jailbreak Damage)

These three errors **always appear together** in jailbroken Kindles with broken certificate chains:

```
E JwtSigner:Error::UnsupportedOperationException while adding headers. Message: x509 certificate couldn't be obtained
E AmazonDHAv2JwtSigner:Error::Unable to retrieve x509 certificates
ADM: terminate called after throwing an instance of 'std::runtime_error'
  what():  Request Signing Failure. StatusCode: 1
```

**Meaning:** The device's x509 certificate store is corrupted or missing (jailbreak side effect). The JwtSigner cannot find a certificate to sign Amazon API requests. This breaks:
- Device registration with Amazon → can't sync, can't verify identity
- Browser's NetworkManager → `Unable to read device identifiers`
- Any HTTPS connection that requires client certificate authentication

**This error has been present since the device was jailbroken** (check earliest log — if the error appears in every backup going back months, it's a persistent state, not a new problem).

### Browser Init Failure

```
E com.lab126.browser:void NetworkManager::init(SoupSession*):Unable to read device identifiers:
```

**Meaning:** The browser's network layer (based on libsoup/WebKit) can't get device identity, likely because the x509 certificate chain is broken. The browser starts (app lifecycle) but can't establish secure connections.

### Device Credential Refresh Failure

```
java.io.IOException: Server returned HTTP response code: 500 for URL: https://firs-ta-g7g.amazon.com/FirsProxy/getNewDeviceCredentials
E DeviceAuthenticationService:DownloadCredentialsFailed::...
```

**Meaning:** Amazon's credential server returned 500 when the device tried to refresh its credentials. This can be either Amazon-side (transient server error) or device-side (sending malformed requests due to broken certificate chain). If it happens repeatedly, it's likely the device side.

### WiFi/Connectivity (Healthy)

These indicate normal WiFi operation:

```
I spectator:conn-done:t=44118.852190:
I wmgr:wconn:rssi=5::~:
```

### Timing Metrics (tmd — Transfer Manager)

The `tmd[]` logs show detailed request timing:

```
I rate_stats2:COMPLETED:id=53,...,c2_dns=56ms,c3_conn=235ms,c4_ssl=2523ms,c5_pret=3ms,c6_dstart=0ms,c7_dend=270ms,c8_total=3090ms
```

Fields (useful):
- `c4_ssl` — SSL/TLS handshake time (in ms). If this is very large or fails, SSL issue
- `c2_dns` — DNS resolution time
- `c3_conn` — TCP connection time
- `c8_total` — Total request time

A `FAILED` entry right after a `COMPLETED` entry with the same id and `c8_total` ≈ `c4_ssl` suggests the SSL handshake succeeded but the request was cancelled (likely a timeout or the `Request Signing Failure` cascading).

### Proxy State (Browser)

```
I com.lab126.browser:void NetworkManager::updateProxy():no proxy set - connection type=wifi reason=connection without proxy:
```

Kindle browser logs its proxy configuration. "no proxy set" is the normal state (Kindle doesn't use HTTP proxies).

## Device Information (from USB)

```
cat /Volumes/Kindle/system/version.txt
# e.g. "Kindle 5.16.2.1.1 (409748 002)"
```

The `002-` prefix in the version string indicates Juno platform (11th gen Paperwhite/Scribe).

## Known Fixes for Common Issues

### Browser Not Loading Pages (Jailbroken Kindle)

**Symptom:** Browser opens but never loads any page. WiFi shows connected. Other devices work.

**Most likely cause:** Jailbreak broke certificate chain (see signature reference above).

**Fix order:**
1. Power cycle (hold power 40s) — clears transient state
2. Sync My Kindle — forces credential refresh attempt
3. Set correct time via sync — SSL needs accurate clock
4. Deregister + re-register Amazon account — forces fresh credential issue
5. Reinstall Jailbreak Hotfix via MRInstaller (if available)
6. Factory reset as last resort (will need to re-jailbreak)

### Browser Not Working on Captive Portal WiFi

**Symptom:** Works on home WiFi, fails on library/hotel WiFi.

**Fix:**
- Open browser to `http://example.com` or `http://1.1.1.1` (HTTP triggers redirect)
- Use phone hotspot instead
- Jailbroken Kindle: install USBNetwork for SSH → create SSH tunnel through Mac

## Pitfalls

1. **USB only exposes a limited filesystem.** System configuration files (WiFi passwords, proxy settings, network config) are NOT accessible via `/Volumes/Kindle/`. Don't look for them there.
2. **Compressed logs are rotated daily.** The backup runs each night (via `log_backup.sh`). You may not have the very latest log if it happened after the last backup.
3. **crash.log is KOReader-only.** `/Volumes/Kindle/koreader/crash.log` contains KOReader activity (book opens, crashes), NOT system or browser logs.
4. **Most recent log may contain old entries.** The log backup collects entries since the last backup — it's a cumulative dump, not a fresh per-session file.
5. **"Request Signing Failure" is chronic, not acute.** If this error has been in every log for months, it didn't cause a NEW browser failure. Look for a secondary trigger (firmware update, changed router config, expired lease).
