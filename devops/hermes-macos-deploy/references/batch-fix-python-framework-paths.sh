#!/bin/bash
# batch-fix-python-framework-paths.sh
# Batch-fix all hardcoded /Library/Frameworks/Python.framework/ paths in an
# extracted Python framework bundle for headless deployment (no sudo).
#
# Usage:
#   1. Extract Python_Framework.pkg Payload to a temp dir:
#        cd /tmp/py-extract/Python_Framework.pkg
#        cat Payload | gzip -d | cpio -idmu
#   2. Run this script from inside Python_Framework.pkg:
#        bash /path/to/batch-fix-python-framework-paths.sh
#   3. Move to ~/.local/Python.framework/ and set PATH.
#
# The fix replaces the absolute path with @executable_path/../ (for executables)
# or @loader_path/../ (for .dylib/.so files), making the framework relocatable.

set -euo pipefail

FIXDIR="${1:-.}"
echo "=== Fixing hardcoded Python.framework paths in: $FIXDIR ==="

# The hardcoded prefix to replace
OLD_PATH="/Library/Frameworks/Python.framework/Versions/3.11"

# Count and fix all Mach-O files referencing the framework
count=0
while IFS= read -r -d '' file; do
  # Skip if not a Mach-O binary
  filetype=$(file -b "$file" 2>/dev/null | head -1)
  case "$filetype" in
    Mach-O*) ;;
    *) continue ;;
  esac

  # Get all dylib references to the old path
  refs=$(otool -L "$file" 2>/dev/null | grep "$OLD_PATH" || true)
  if [ -z "$refs" ]; then
    continue
  fi

  echo "=== Fixing: $file ==="
  echo "$refs" | while read -r line; do
    lib=$(echo "$line" | awk '{print $1}')
    # Compute the relative path:
    #   /Library/Frameworks/Python.framework/Versions/3.11/... -> @loader_path/../...
    # For executables: @executable_path/../Python
    # For .dylib/.so: @loader_path/../Python (or ../lib/...)
    relative=$(echo "$lib" | sed "s|$OLD_PATH/||")
    install_name_tool -change "$lib" "@loader_path/../$relative" "$file" 2>/dev/null || \
    install_name_tool -change "$lib" "@executable_path/../$relative" "$file" 2>/dev/null
  done
  count=$((count + 1))
done < <(find "$FIXDIR" -type f -print0)

echo ""
echo "=== Fixed $count files ==="
echo "Now move this directory to your target location:"
echo "  mv $FIXDIR ~/.local/Python.framework"
echo "  export PATH=\"\$HOME/.local/Python.framework/Versions/3.11/bin:\$PATH\""
