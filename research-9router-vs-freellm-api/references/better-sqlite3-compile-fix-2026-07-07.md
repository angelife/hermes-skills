# better-sqlite3 Compilation Fix — macOS + Node 23 (2026-07-07)

## Root Cause

`prebuild-install` has no prebuilt binary for Node 23 (ABI 131) on macOS darwin-x64.
`node-gyp` rebuild fails with:

```
../src/better_sqlite3.cpp:1:10: fatal error: 'climits' file not found
    1 | #include <climits>
      |          ^~~~~~~~~
```

The C++ standard library headers exist at `/Library/Developer/CommandLineTools/SDKs/MacOSX.sdk/usr/include/c++/v1/climits` but `node-gyp` doesn't find them automatically on this macOS version (Sequoia 15.7, SDK 26).

## Fix

```bash
export CXXFLAGS="-I/Library/Developer/CommandLineTools/SDKs/MacOSX.sdk/usr/include/c++/v1"
cd /usr/local/lib/node_modules/omniroute
npm rebuild better-sqlite3
```

The flag adds the libc++ header path to the compiler's include search path.

## Verification

```bash
node -e "
const b = require('/usr/local/lib/node_modules/omniroute/node_modules/better-sqlite3');
const db = new b(':memory:');
db.exec('CREATE TABLE t (x INT)');
db.prepare('INSERT INTO t VALUES(1)').run();
console.log('OK:', db.prepare('SELECT * FROM t').all());
"
```

Expected: `OK: [ { id: 1 } ]`

## Why `omniroute runtime repair` also fails

The built-in repair command depends on npm availability. It may fail with "Repair failed — check npm availability" even when npm is installed, because of the same native compilation issue. Use manual rebuild with CXXFLAGS instead.

## Persistence

The CXXFLAGS fix is per-shell — only `export` it in the session where you run `npm rebuild`. The rebuilt binary persists at:
`/usr/local/lib/node_modules/omniroute/node_modules/better-sqlite3/build/Release/better_sqlite3.node`

Future `npm rebuild` calls will also need the same CXXFLAGS until a prebuilt binary is published for ABI 131.
