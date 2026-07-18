# ADB Wireless (TCP) Large File Transfer — Failure Modes & Workarounds

## Problem

`adb push` over TCP (wireless ADB, e.g. `adb -s 192.168.1.x:5555`) reliably fails for
files larger than ~10–20 MB on some network topologies. Symptoms:

| Approach | Failure Signal |
|---|---|
| `adb push <file> /data/local/tmp/` | `EOF` after write completes; file absent on device |
| `adb exec-out "cat > /data/local/tmp/file"` | Hangs indefinitely > 60s |
| `adb shell curl http://mac:port/file` | Connection times out (device can't route back to Mac LAN) |

## Root Cause

TCP ADB over WiFi/4G/RNDIS cross-subnet topologies has asymmetric routing.
The device may be reachable for small control commands (echo, ls, df — sub-1K payloads)
but lack the sustained TCP throughput or correct return-path for multi-MB streams.
This is **not** an ADB version issue — it's the transport layer.

## Diagnostic Sequence

```bash
# 1. Quick ADB alive check
adb -s 192.168.1.21:5555 shell "echo alive"        

# 2. Try a small file push (confirm push protocol works at all)
echo "test" | adb exec-out "cat > /data/local/tmp/test.txt"
adb -s ... shell "cat /data/local/tmp/test.txt"    # → "test" = exec-out pipe works

# 3. Test push of a moderately-sized file (e.g. 1 MB)
dd if=/dev/zero of=/tmp/1m bs=1m count=1
adb -s ... push /tmp/1m /data/local/tmp/           # → if fails, TCP transport is the bottleneck

# 4. Test LAN reachability from device (Mac IP in same subnet)
adb -s ... shell "curl -s --connect-timeout 5 http://192.168.1.8:19999/"  # → if fails, no LAN route
```

## Workarounds (ordered by reliability)

### ✅ A — USB ADB (most reliable)

Physically connect phone to Mac via USB data cable, then use USB transport:

```bash
adb devices -l                           # verify device shows up with USB transport
adb -d push /tmp/file.apk /data/local/tmp/
```

Devices may appear as a second entry (same serial, different transport).
Use `adb -d` (USB) or `adb -t <transport_id>` to target the USB path.

If TCP-on-USB is also routed through wireless, kill the TCP connection:
```bash
adb disconnect 192.168.1.21:5555
adb -d push ...
```

### ✅ B — HTTP Server + Device Pull (LAN direct)

Use only when device has a working LAN route to Mac (same subnet, no proxy).

```bash
# Mac side: start HTTP server on a high port
python3 -m http.server 19999 --directory /tmp/
# runs as background process — keep it alive

# Device side: pull via LAN
adb -s 192.168.1.21:5555 shell \
  "curl -L --connect-timeout 10 --max-time 300 \
   -o /data/local/tmp/file.apk \
   http://192.168.1.8:19999/file.apk"

# If curl unavailable, try wget:
adb -s ... shell \
  "wget -O /data/local/tmp/file.apk \
   http://192.168.1.8:19999/file.apk"
```

**Limitation**: device's routing must allow LAN traffic to Mac.
On 4G + RNDIS topologies, the device's return path may go through cellular,
making TCP handshake incomplete. Verify with a small HTTP GET first.

### ⚠️ C — Split + Base64 (slow but universal)

Works over any ADB transport, even flaky TCP:

```bash
# Mac side: split into 1 MB chunks, base64 encode each
split -b 1m /tmp/file.apk /tmp/chunk_
for f in /tmp/chunk_*; do
  adb -s ... exec-out "cat > /data/local/tmp/$(basename $f).b64" < <(base64 < $f)
done

# Device side: reassemble
adb -s ... shell "
  for f in /data/local/tmp/chunk_*.b64; do
    base64 -d < \$f >> /data/local/tmp/file.apk
    rm \$f
  done
"
```

**Very slow** (~50 KB/s effective even on flaky TCP) but **guaranteed to complete**
if the ADB control channel stays alive.

### ❌ D — Python HTTP proxy over ADB reverse

Does **not** work on Android 15+ with Termux — SELinux blocks Termux user-space
from creating sockets. Only viable if the destination process runs as `root` or
`system` UID (not Termux).

## Best Practice

For files >10 MB destined for Android:

1. **Always prefer USB ADB** for the initial push — even if the device is normally managed wirelessly, one USB plug-in saves hours of troubleshooting.
2. If USB truly unavailable (device remote), use **Workaround B** after confirming LAN reachability with a small test file.
3. Only fall back to **Workaround C** (chunked base64) for one-off small files (<50 MB).
4. Document the network topology in memory (`device X → LAN IP Y / WAN IP Z`) so next session knows whether LAN direct will work.
