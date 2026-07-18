#!/usr/bin/env bash
# verify-openwrt-n1-flash.sh
IMGPATH="/tmp/openwrt_one-nor-factory.bin"
EXPECTED="a14e5c08d07d33e70cd1ddc482472e889884f5d633ebcb58240c69f9f410aebd"
if shasum -a 256 "$IMGPATH" | grep -q "$EXPECTED"; then
    echo "✅ Checksum matches"
else
    echo "❌ Checksum mismatch"
    exit 1
fi