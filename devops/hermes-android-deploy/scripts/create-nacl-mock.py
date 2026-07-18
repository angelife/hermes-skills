#!/usr/bin/env python3
"""Create a mock nacl._sodium module for Android Termux when libsodium
isn't compiled. Hermes only uses PyNaCl for GitHub/GitLab secret encryption,
which is not needed for the basic Telegram gateway or CLI operations.

Usage: run on the Android device as root:
  su -c 'python3 /path/to/create-nacl-mock.py'

Or via ADB:
  adb push create-nacl-mock.py /data/local/tmp/
  adb shell su -c '/data/data/com.termux/files/usr/bin/python3 /data/local/tmp/create-nacl-mock.py'
"""

import os, sys

SITE_PACKAGES = '/data/data/com.termux/files/usr/lib/python3.13/site-packages'
SODIUM_DIR = os.path.join(SITE_PACKAGES, 'nacl', '_sodium')

os.makedirs(SODIUM_DIR, exist_ok=True)

with open(os.path.join(SODIUM_DIR, '__init__.py'), 'w') as f:
    f.write('''"""
Mock _sodium module for Hermes on Android Termux.
Hermes uses PyNaCl only for GitHub/GitLab secret encryption,
which is NOT needed for basic Telegram gateway or CLI operations.
"""

class _MockFFI:
    def __init__(self):
        self.NULL = 0
        self.R_OK = 4; self.W_OK = 2; self.X_OK = 1; self.F_OK = 0
    def addressof(self, *a, **kw): return 0
    def alignof(self, *a, **kw): return 8
    def sizeof(self, *a, **kw): return 4
    def typeof(self, *a, **kw): return type('CType', (), {})()
    def callback(self, *a, **kw): return lambda: None
    def cast(self, *a, **kw): return None
    def new(self, *a, **kw): return None
    def from_buffer(self, *a, **kw): return bytearray(32)
    def string(self, *a, **kw): return b''
    def unpack(self, *a, **kw): return tuple()
    def getwinerror(self, *a, **kw): return (0, '')
    def dlopen(self, *a, **kw):
        import ctypes.util
        path = ctypes.util.find_library('sodium')
        if path:
            return ctypes.CDLL(path)
        raise OSError('libsodium not found')
    def getctype(self, *a, **kw): return 'void'
    def new_ctype(self, *a, **kw): return type('CType', (), {})()

ffi = _MockFFI()
lib = ffi
''')

# Patch encoding/__init__.py with Encoder base class if needed
ENCODING_DIR = os.path.join(SITE_PACKAGES, 'nacl', 'encoding')
os.makedirs(ENCODING_DIR, exist_ok=True)
encoding_init = os.path.join(ENCODING_DIR, '__init__.py')
if os.path.exists(encoding_init):
    with open(encoding_init, 'r') as f:
        content = f.read()
    if 'class Encoder' not in content:
        with open(encoding_init, 'a') as f:
            f.write('\n\nclass Encoder:\n    @staticmethod\n    def encode(data): return data\n    @staticmethod\n    def decode(data): return data\n')
else:
    with open(encoding_init, 'w') as f:
        f.write('class Encoder:\n    @staticmethod\n    def encode(data): return data\n    @staticmethod\n    def decode(data): return data\n\nclass RawEncoder(Encoder): pass\n\nclass Base64Encoder(Encoder):\n    @staticmethod\n    def encode(data): return __import__("base64").b64encode(data)\n    @staticmethod\n    def decode(data): return __import__("base64").b64decode(data)\n\nclass HexEncoder(Encoder):\n    @staticmethod\n    def encode(data): return data.hex().encode()\n    @staticmethod\n    def decode(data): return bytes.fromhex(data.decode())\n')

print('nacl._sodium mock created:', SODIUM_DIR)
print('nacl.encoding Encoder class added:', encoding_init)
