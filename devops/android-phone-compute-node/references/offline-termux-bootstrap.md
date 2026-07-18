# Offline Termux Bootstrap (No Network)

When the phone has broken WiFi and no mobile data, standard `apt install` fails.
This reference covers two offline installation strategies.

## Strategy A: ADB Reverse Proxy (root-only, not for Termux app)

`adb reverse` forwards a TCP port from the phone to the host machine. Combined
with a local HTTP proxy on the host, it gives the phone's root/system shell
internet access. **However, this does NOT work for the Termux app user**
(u0_a* PID), because Android's per-app network namespace isolation blocks
ADB-reverse-forwarded ports from app sandboxes. The Termux app will see
`Connection refused` on those ports.

Suitable only for downloading .deb packages as root for offline installation.
Steps:

```bash
# On host: write tiny HTTP CONNECT proxy (or use mitmproxy/squid)
python3 tiny_proxy.py

# ADB reverse: phone:9999 -> host:8080
adb reverse tcp:9999 tcp:8080

# Verify from phone root shell
adb shell 'http_proxy=http://127.0.0.1:9999 https_proxy=http://127.0.0.1:9999 \
  curl -sI https://packages.termux.dev | head -5'
```

## Strategy B: Offline .deb Installation (recommended)

Download all required Termux packages on a machine with internet, push via ADB,
and install via dpkg as root. This bypasses both the network restriction and
apt's root-safety check.

### 1. Identify needed packages

Parse the Termux aarch64 Package index to find the full dependency tree:

```bash
# On host, download the package index
curl -sL -o Packages.gz \
  "https://packages.termux.dev/apt/termux-main/dists/stable/main/binary-aarch64/Packages.gz"

# Parse with python3 to extract dependency URLs
python3 << 'EOF'
import gzip, re
with gzip.open('Packages.gz', 'rt') as f:
    content = f.read()
blocks = content.split('\n\n')

# Find python and its dependencies
dep_names = set()
for block in blocks:
    pkg = None
    for line in block.split('\n'):
        if line.startswith('Package: '):
            pkg = line.split(' ', 1)[1].strip()
    if pkg == 'python':
        for line in block.split('\n'):
            if line.startswith('Depends: '):
                deps = re.findall(r'([a-z0-9][a-z0-9+.-]+)', line.split(': ', 1)[1])
                dep_names.update(deps)

# Find download URLs (recursively resolve transitive deps)
visited = set()
def resolve(name):
    if name in visited: return
    visited.add(name)
    for block in blocks:
        pkg = None
        filename = None
        deps = []
        for line in block.split('\n'):
            if line.startswith('Package: '):
                pkg = line.split(' ', 1)[1].strip()
            elif line.startswith('Filename: '):
                filename = line.split(' ', 1)[1].strip()
            elif line.startswith('Depends: '):
                deps = re.findall(r'([a-z0-9][a-z0-9+.-]+)', line.split(': ', 1)[1])
        if pkg == name and filename:
            url = f"https://packages.termux.dev/{filename}"
            print(f"{name}: {url}")
            for d in deps:
                resolve(d)
            break

for d in sorted(dep_names):
    resolve(d)
EOF
```

### 2. Download packages

```bash
# Either on host (direct) or on phone root (via ADB reverse proxy)
mkdir -p debs && cd debs
for url in $(python3 ../list_deps.py); do
  curl -sL -o $(basename $url) $url || echo "FAIL: $url"
done
```

### 3. Push to phone and install

```bash
# Push to shared storage
adb push debs/ /sdcard/Download/termux_debs/

# Install via dpkg as root
adb shell 'export TERMUX_PREFIX=/data/data/com.termux/files/usr && \
  export PATH=$TERMUX_PREFIX/bin:$PATH && \
  dpkg -i /sdcard/Download/termux_debs/*.deb'
```

### 4. Verify

```bash
adb shell "su - u0_a203 -c '/data/data/com.termux/files/usr/bin/python3 --version'"
```

## Key Caveats

- **`apt` refuses root**: Termux's apt binary has a hard-coded root check:
  "Ability to run this command as root has been disabled permanently for safety
  purposes." Always use `dpkg` when running as root.

- **ADB reverse + app sandbox**: `adb reverse` forwards are invisible to regular
  app processes (u0_a*). This is an Android security feature. Only root/shell
  can reach those ports.

- **Package naming with colons**: Some Termux packages have `:` in version
  strings (e.g. `openssl_1:3.6.3`). The colon is valid in the download URL but
  may cause issues as a filename; sanitize with `sed 's/:/_/g'` when saving.

- **DPKG database location**: Termux's dpkg database lives at
  `/data/data/com.termux/files/usr/var/lib/dpkg/`. When running dpkg as root,
  ensure `TERMUX_PREFIX` is set correctly so dpkg finds this database.

## LOS Upgrade: Expected Partition Warnings

When upgrading LineageOS across major Android versions (e.g. LOS 21→22.2,
Android 14→15), the recovery will emit:

```
ERROR: recovery: [liblp] Logical partition metadata has invalid geometry magic signature.
```

This is **expected behavior** — the super partition layout changes between
Android major versions and the recovery's liblp checker flags the old layout.
The critical line is:

```
script succeeded: result was [1.000000]
Install completed with status 0.
```

**`Status 0` means the installation succeeded.** The partition metadata warnings
can be ignored. Do not abort or re-download the ROM based on these warnings.
