# llama.cpp Android Deployment

Deploy llama.cpp on a rooted Android phone (LineageOS, Termux) via ADB.

## Workflow

### 1. Get the binary

Use the **official Android ARM64 build** from GitHub releases — compiled with Android NDK against bionic libc, works natively (no glibc issues):

```bash
curl -sL -o llm-android.tar.gz \
  https://github.com/ggerganov/llama.cpp/releases/download/b9758/llama-b9758-bin-android-arm64.tar.gz
```

The package contains `.so` shared libraries in multiple ARM ISA variants (armv8.0, v8.2, v8.6, v9.0, v9.2) and thin wrapper executables that dlopen the matching variant.

### 2. Push to phone

```bash
adb push llama-b9758/*.so /data/local/tmp/llama/lib/
adb push llama-b9758/llama /data/local/tmp/llama/
adb push llama-b9758/llama-server /data/local/tmp/llama/  # for API mode
adb shell chmod -R 755 /data/local/tmp/llama/
```

### 3. Run

```bash
adb shell su -c '
  export LD_LIBRARY_PATH=/data/local/tmp/llama/lib
  /data/local/tmp/llama/llama serve \
    -m /data/local/tmp/models/model.gguf \
    --host 0.0.0.0 \
    --port 8085 \
    -t 6 \
    -c 4096 \
    --mlock
'
```

Subcommands: `serve` (HTTP API), `cli` (interactive), `bench`, `version`, `help`.

### 5. ADB forward — expose phone service to host

Once `llama serve` is running on the phone (port 8085), make it accessible from the host machine:

```bash
adb forward tcp:8085 tcp:8085
# Now both host:8085 and phone's own localhost:8085 reach the same service
```

This creates a TCP tunnel: connections to the Mac's `localhost:8085` are piped through USB to the phone's `localhost:8085`.

**Why needed**: The phone is USB-tethered and has no LAN IP that the Mac can reach directly. `adb forward` bridges the gap without network setup.

**Verify**:

```bash
curl -s http://localhost:8085/v1/models | python3 -c "import json,sys; d=json.load(sys.stdin); print([m['id'] for m in d['data']])"
```

**Survives**: Only as long as the ADB session is alive. After phone reboot (or ADB restart), re-run the forward command. Not persistent.

### 6. Magisk startup — auto-start on boot

To make `llama serve` start automatically when the phone boots:

```bash
adb shell su -c 'cat > /data/adb/service.d/llama-server.sh << '"'"'SCRIPT'"'"'
#!/system/bin/sh
# Start llama-server on boot (wait for boot to complete first)
while [ "$(getprop sys.boot_completed)" != "1" ]; do sleep 2; done

export LD_LIBRARY_PATH=/data/local/tmp/llama
nohup /data/local/tmp/llama/llama serve \
    -m /data/local/tmp/models/model.gguf \
    --host 0.0.0.0 \
    --port 8085 \
    -t 6 \
    -c 4096 \
    --mlock \
    > /data/local/tmp/llama-server.log 2>&1 &
SCRIPT
chmod +x /data/adb/service.d/llama-server.sh'
```

Magisk `service.d` scripts run at boot in the `u:r:magisk:s0` context (root, networking works). The `while` loop ensures the service starts only after the system finishes booting.

### Model download

Download GGUF models on the host Mac and push:

```bash
# HuggingFace (global, stable)
curl -sL -o qwen.gguf \
  https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct-GGUF/resolve/main/qwen2.5-1.5b-instruct-q4_k_m.gguf

# China mirror (faster in CN networks)
curl -sL -o qwen.gguf \
  https://hf-mirror.com/Qwen/Qwen2.5-1.5B-Instruct-GGUF/resolve/main/qwen2.5-1.5b-instruct-q4_k_m.gguf

# Alternative: Modelscope
curl -sL -o qwen.gguf \
  https://modelscope.cn/api/v1/models/Qwen/Qwen2.5-1.5B-Instruct-GGUF/repo?Revision=master&FilePath=qwen2.5-1.5b-instruct-q4_k_m.gguf

# Verify GGUF format
xxd qwen.gguf | head -1  # should start with "GGUF"
echo "Size: $(ls -lh qwen.gguf | awk '{print $5}')"

adb push qwen.gguf /data/local/tmp/models/
```

**Model download pitfalls**:
- **Modelscope delivers incomplete files without error**: The Modelscope API may return a truncated 15-66MB file for a 985MB model with exit code 0 and no error message. Always check file size (`ls -lh`) before pushing. HuggingFace is more reliable despite slower speed (~0.6 MB/s from CN).
- **Download speed**: ~0.5-0.8 MB/s from HuggingFace in CN networks. A 985MB Q4_KM model takes 20-25 minutes. Background it with `terminal(background=true, notify_on_complete=true)` and monitor progress with periodic `ls -lh`.
- **`content-length` check**: After download starts, verify `ls -lh` periodically. Expected final size: Qwen2.5-1.5B-Q4_K_M ≈ 985MB.

## Pitfalls

### "no backends are loaded" — .so file location matters

The `llama serve` command fails with `no backends are loaded. hint: use ggml_backend_load()` when the shared libraries (`libggml-cpu-android_*.so`, etc.) are in a separate `lib/` subdirectory even if `LD_LIBRARY_PATH` points there. The binary's backend loader searches the **binary's own directory** AND the standard library paths, but not arbitrary `LD_LIBRARY_PATH` directories for backend plugins specifically.

**Fix**: copy ALL `.so` files to the same directory as the `llama` binary, then set `LD_LIBRARY_PATH` to that directory:

```bash
adb shell "cp lib/*.so ."   # from /data/local/tmp/llama/
export LD_LIBRARY_PATH=/data/local/tmp/llama
```

Or run with `LD_LIBRARY_PATH` pointing to the directory containing both binary and libraries.

### Model loading logs — expected warnings

When loading a Qwen GGUF model on Android, normal log output includes:

- `"warming up the model with an empty run - please wait ..."` — expected warmup, takes ~1-2 seconds
- `"n_ctx_seq (4096) < n_ctx_train (32768) -- the full capacity of the model will not be utilized"` — always shows when `-c` is below the model's training context. Not an error.
- `"control-looking token: 128247 '</s>' was not control-type"` — Qwen models have non-standard special token handling; benign warning.

### Performance on SD845 (Xiaomi Mi 8)

Qwen2.5-1.5B Q4_K_MM on Kryo 385 (4x A75 + 4x A55, 6 threads):

- **Generation speed**: ~1.88 tok/s total (prompt processing + generation) on first request
- **First-token latency dominates short requests**: A short chat completion (20 output tokens) reports low tok/s because ~30-60s of prompt processing is amortized over few output tokens. On a long generation (200+ tokens) the amortized speed approaches pure generation throughput (estimated 3-5 tok/s).
- **For accurate measurement**: Use `llama-bench` with `-p 0 -n 128` to measure pure generation speed without prompt overhead.
- **Memory usage**: ~1240 MiB for 1.5B model (including KV cache for 4096 context)
- **CLI settings used**: `-t 6 -c 4096 --mlock` (lock memory, 6 threads)
- **Pre-built binary note**: Official GitHub release binaries may lack `GGML_NATIVE=ON` — compiling from source on the device (or cross-compiling) can unlock ARMv8.2 dotprod and fp16 vector arithmetic optimizations that roughly double throughput.

Settings that matter on constrained phones:
- `--mlock` — prevents the model weights from being swapped out by Android's LMK
- `-t N` — set threads to number of big cores available (N=4 for 4x A75, or increase to 6 if using all cores)
- API auto-negotiates `n_parallel` based on memory: ~4 parallel slots on 5.6GB RAM

### bionic vs glibc
Android's bionic libc is incompatible with glibc-linked binaries. Pre-built Android NDK binaries work; linux-arm64/generic-arm64 binaries fail with "CANNOT LINK EXECUTABLE" or "No such file or directory" (bionic linker can't find glibc's ld-linux). Solution: use Android-specific builds or cross-compile with Android NDK.

### Termux DNS in su context
When running commands as Termux user (`su 10188 -c '...'`) DNS resolution often fails (pkg, pip, curl all affected). Running as root (`su -c '...'`) preserves DNS via Android's getprop net.dns1. Workaround: pipe network commands through root.

### Rust compilation on Android Termux
`pip install` of packages with Rust/Cython dependencies (cryptography, obstore, pydantic-core) fails because `rustup` target `aarch64-linux-android` is unsupported and build tools are missing. Use `--only-binary :all:` and prebuilt wheels, or cross-compile on host.
