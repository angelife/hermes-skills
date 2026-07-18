# Android 15 Termux + Python C Extension Issues

## Android 15 App Data Dir Policy
Android 15 no longer auto-creates `/data/data/<package>/files/` on first launch.
The app must be opened at least once before data dirs exist.
**Fix**: User must tap the Termux icon on the home screen (open once, can close immediately).
Without this, all dpkg/push operations will fail with "inaccessible or not found".

## C Extension Wheels (pyyaml example)
pip rejects manylinux/musllinux wheels on Android because `sys.platform == 'android'`.
The wheel binary is compatible (same aarch64 CPU), but pip's platform checker blocks it.

### Manual Compile Method
1. Install libyaml from Termux repo (dpkg)
2. Install Cython from PyPI wheel
3. Download pyyaml source tar.gz
4. Run setup.py with CFLAGS/LDFLAGS pointing to TERMUX_PREFIX

```bash
# On Mac: download assets
curl -L -o libyaml.deb "https://packages.termux.dev/apt/termux-main/pool/main/liby/libyaml/libyaml_0.2.5-5_aarch64.deb"
curl -L -o cython.whl "https://files.pythonhosted.org/packages/57/ed/883d0784250c6a2e21e01bce01752faf1966c634a193e5afb25a67c02fff/cython-3.2.6-py3-none-any.whl"
curl -L -o PyYAML-6.0.2.tar.gz "https://files.pythonhosted.org/packages/54/ed/79a089b6be93607fa5cdaedf301d7dfb23af5f25c398d5ead2525b063e17/pyyaml-6.0.2.tar.gz"
tar -czf pyyaml-src.tar.gz pyyaml-6.0.2/

# Push all to device
adb -s <device> push libyaml.deb cython.whl pyyaml-src.tar.gz /sdcard/Download/

# On device: install
export TERMUX_PREFIX=/data/data/com.termux/files/usr
export PATH=$TERMUX_PREFIX/bin:$PATH
export CFLAGS="-I$TERMUX_PREFIX/include"
export LDFLAGS="-L$TERMUX_PREFIX/lib -lyaml"

$TERMUX_PREFIX/bin/dpkg -i /sdcard/Download/libyaml.deb
pip3 install --no-build-isolation --no-deps /sdcard/Download/cython.whl

cd /sdcard/Download
rm -rf pyyaml-6.0.2
tar -xzf pyyaml-src.tar.gz
cd pyyaml-6.0.2
python3 setup.py build_ext --include-dirs=$TERMUX_PREFIX/include --library-dirs=$TERMUX_PREFIX/lib
python3 setup.py install
```

## proxy.py HTTPS CONNECT Issue
The `simple_proxy.py` used for TCP tunneling does NOT implement HTTP CONNECT tunneling.
pip's SSL connections to PyPI use CONNECT and will fail with "Proxy CONNECT aborted".
**Workaround**: Download all wheels/tarballs on Mac first, push via adb.

## pkg Command Disabled as Root
Termux explicitly blocks running `pkg` as root (since v0.118+).
Use `$TERMUX_PREFIX/bin/dpkg` directly instead.

## DNS on Android via Proxy
DNS resolution may fail on Android when going through the proxy tunnel.
If `curl -x http://127.0.0.1:9999 https://pypi.org/` fails:
- Download packages on Mac, push via adb
- Or check if `resolv.conf` has correct DNS servers in Termux
