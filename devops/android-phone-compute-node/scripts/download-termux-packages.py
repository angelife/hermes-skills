#!/usr/bin/env python3
"""
Download Termux .deb packages from mirror and print install commands.

Use this when `apt`/`pkg` refuse to run (root check) and the non-root
user lacks DNS (Android 13+ su-context limitation). Runs from any root
shell where DNS works (adb root, Magisk su -c).

Usage:
  python3 download-termux-packages.py [package_names...]

Default targets: python, git, openssh, openssl, ca-certificates, resolv-conf
Dependencies are listed but NOT auto-downloaded — install deps first.
"""

import urllib.request, zlib, gzip, os, sys, json

MIRROR = "https://mirrors.tuna.tsinghua.edu.cn/termux/apt/termux-main"
ARCH = "aarch64"  # change for 32-bit arm: "arm"

DEFAULT_TARGETS = [
    "python", "git", "openssh", "openssl",
    "ca-certificates", "resolv-conf"
]


def resolve_targets(names):
    """Return targets list, preferring CLI args over defaults."""
    if not names:
        return DEFAULT_TARGETS
    return [n.strip() for n in names if n.strip()]


def main():
    targets = resolve_targets(sys.argv[1:])

    # Download and parse Packages index
    packages_url = f"{MIRROR}/dists/stable/main/binary-{ARCH}/Packages.gz"
    print(f"[*] Downloading {packages_url} ...")
    data = urllib.request.urlopen(packages_url, timeout=30).read()

    try:
        text = zlib.decompress(data, 47)
    except Exception:
        text = gzip.decompress(data)
    text = text.decode()

    found = []
    for pkg_name in targets:
        marker = "\nPackage: " + pkg_name + "\n"
        idx = text.find(marker)
        if idx < 0:
            print(f"[!] NOT FOUND: {pkg_name}")
            continue
        end_idx = text.find("\n\n", idx)
        if end_idx < 0:
            end_idx = len(text)
        block = text[idx:end_idx]

        filename = ""
        sha256 = ""
        deps = ""
        for line in block.split("\n"):
            if line.startswith("Filename: "):
                filename = line[10:]
            if line.startswith("SHA256: "):
                sha256 = line[8:64]
            if line.startswith("Depends: "):
                deps = line[9:]

        if filename:
            found.append((pkg_name, filename, sha256, deps))

    # Print found info
    for name, fname, sha, deps in found:
        url = MIRROR + "/" + fname
        print(f"\n PKG: {name}")
        print(f"   URL: {url}")
        print(f"   SHA256: {sha}")
        print(f"   Deps: {deps}")

    # Download
    download_dir = "/data/local/tmp/termux_pkgs"
    os.makedirs(download_dir, exist_ok=True)

    print(f"\n[*] Downloading to {download_dir}/ ...")
    for name, fname, sha, deps in found:
        url = MIRROR + "/" + fname
        local = os.path.join(download_dir, os.path.basename(fname))
        if os.path.exists(local):
            print(f"  [skip] {name} (exists)")
            continue
        print(f"  [get]  {name} ...")
        try:
            urllib.request.urlretrieve(url, local)
            size = os.path.getsize(local)
            print(f"         {size} bytes OK")
        except Exception as e:
            print(f"         FAIL: {e}")

    # Print install commands
    print("\n" + "=" * 60)
    print("Install with these commands (in order):")
    print("=" * 60)
    print(f"export PREFIX=/data/data/com.termux/files/usr")
    print(f"export PATH=$PREFIX/bin:/system/bin")
    print()
    # Install resolv-conf and ca-certificates first (no deps)
    for name, fname, sha, deps in found:
        local = os.path.join(download_dir, os.path.basename(fname))
        print(f"dpkg -i --force-confdef --force-confold {local} || true")
    print()
    print("# Fix ownership after install (dpkg runs as root):")
    print(f"# APP_UID=$(stat -c '%u' /data/data/com.termux/)")
    print(f"# chown -R $APP_UID:$APP_UID $PREFIX/")

    print(f"\n[*] Done. {len(found)} packages.")


if __name__ == "__main__":
    main()
