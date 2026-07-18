---
name: macos-voice-pipeline
description: Real-time speech-to-text pipeline on macOS — ffmpeg avfoundation capture → silero-vad → faster-whisper transcription. Covers raw PCM streaming (no temp files), OpenMP/libiomp5 conflict on Intel Macs, mic permissions, and thread-safe capture/inference separation.
version: 1.0.0
tags: [macOS, voice, speech-to-text, asr, faster-whisper, silero-vad, avfoundation, real-time, pipeline]
dependencies: [faster-whisper, silero-vad, ffmpeg, numpy]
---

# macOS Voice Pipeline

Build a real-time voice-to-text pipeline on macOS using ffmpeg for capture, silero-vad for voice activity detection, and faster-whisper for transcription — all streaming through subprocess PIPE with no temporary WAV files.

## When to use

**Use when:**
- You need real-time/local speech-to-text on macOS (offline, no API calls)
- Building a voice-controlled assistant or dictation system
- Intel Mac with torch/cpu constraints
- You want streaming raw PCM through PIPE (no disk I/O for audio segments)

**Use alternatives instead:**
- **macOS built-in dictation** (`speech-to-text` in System Settings): simpler but less flexible
- **OpenAI Whisper API**: cloud-based, higher quality, but costs money and needs internet
- **whisper.cpp**: faster CPU inference, but different integration path

## Architecture

```
ffmpeg avfoundation ───subprocess.PIPE───→ silero-vad ────→ faster-whisper
  (capture thread)          s16le PCM       (VAD thread)     (inference thread)
```

**Key design decisions:**
1. **No temp files** — audio flows through subprocess PIPE as raw s16le PCM
2. **Separate threads** — capture thread continuously drains ffmpeg stdout to prevent pipe buffer blocking; inference runs on a daemon thread
3. **Frame-based VAD** — silero-vad operates on 512-sample (32ms) frames, accumulated into utterances

## Setup

### Prerequisites

```bash
# ffmpeg with avfoundation support
brew install ffmpeg

# Python 3.10+
python3 -m venv ~/.venvs/voice-pipeline
source ~/.venvs/voice-pipeline/bin/activate
```

### Install dependencies

```bash
pip install faster-whisper silero-vad onnxruntime 'numpy<2'
```

> **Intel Mac note**: `numpy<2` is required because torch 2.2.x (pulled by faster-whisper) was compiled against numpy 1.x API. Without downgrading, you get: "A module that was compiled using NumPy 1.x cannot be run in NumPy 2.x"

### Chinese mirror (if PyPI is slow)

```bash
pip install -i https://pypi.tuna.tsinghua.edu.cn/simple faster-whisper silero-vad onnxruntime 'numpy<2'
```

## Critical: OpenMP/libiomp5 conflict

**This is the #1 issue on Intel Macs.** Both `onnxruntime` (used by silero-vad) and `ctranslate2` (used by faster-whisper) link their own `libiomp5.dylib` (Intel OpenMP runtime). When both are loaded, the process crashes with:

```
OMP: Error #15: Initializing libiomp5.dylib, but found libiomp5.dylib already initialized.
```

### Fix: import order

**faster_whisper must be imported BEFORE silero_vad.** This lets ctranslate2's OpenMP initialize first; onnxruntime's OpenMP can then coexist.

```python
# ✅ RIGHT — Whisper first, VAD second
from faster_whisper import WhisperModel  # must be first
import silero_vad

# ❌ WRONG — silero_vad first causes segfault
import silero_vad
from faster_whisper import WhisperModel  # crashes
```

Set `KMP_DUPLICATE_LIB_OK=TRUE` as an additional safety net:

```python
import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
```

Or set it in the shell when running:
```bash
KMP_DUPLICATE_LIB_OK=TRUE python voice_pipeline.py
```

### Verify both models load

**Model loading order matters — same as import order.** Even with correct imports, calling `load_silero_vad()` before `WhisperModel()` lets onnxruntime init its OpenMP before ctranslate2, which segfaults on Intel Macs.

```python
from faster_whisper import WhisperModel  # import first
import silero_vad

# ✅ CORRECT loading order — Whisper first, VAD second
whisper = WhisperModel("tiny", device="cpu", compute_type="int8")  # init ctranslate2 first
vad = silero_vad.load_silero_vad(onnx=True)  # then onnxruntime
print("Both models loaded")

# ❌ WRONG — VAD first causes segfault during WhisperModel init
# vad = silero_vad.load_silero_vad(onnx=True)  # onnxruntime loads OpenMP
# whisper = WhisperModel("tiny", ...)  # ctranslate2 can't init → segfault
```

Run via:
```bash
KMP_DUPLICATE_LIB_OK=TRUE python3 -c "
from faster_whisper import WhisperModel
import silero_vad
whisper = WhisperModel('tiny', device='cpu', compute_type='int8')
vad = silero_vad.load_silero_vad(onnx=True)
print('Models OK')
"
```

> **Exit segfault**: Even with correct order, the process may segfault (exit code -11/139) during Python shutdown — OpenMP libraries conflict during cleanup. This is **benign**, only on `sys.exit()`/end of script, not during runtime. The pipeline works correctly while running.

## Pipeline code

The reference file `references/pipeline.py` contains the full working implementation. Key components:

### 1. Audio capture

```python
import subprocess
import numpy as np

def capture_frames(device=":0", frame_size=512):
    """Yield float32 numpy arrays from mic via ffmpeg PIPE."""
    cmd = [
        "ffmpeg", "-f", "avfoundation", "-i", device,
        "-f", "s16le", "-ac", "1", "-ar", "16000",
        "-loglevel", "error", "-",
    ]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    frame_bytes = frame_size * 2  # 16-bit = 2 bytes per sample
    buf = b""
    try:
        while True:
            chunk = proc.stdout.read(frame_bytes * 4)
            if not chunk:
                break
            buf += chunk
            while len(buf) >= frame_bytes:
                yield s16le_to_float32(buf[:frame_bytes])
                buf = buf[frame_bytes:]
    finally:
        proc.terminate()
        proc.wait()
```

### 2. s16le → float32 conversion

```python
def s16le_to_float32(data: bytes) -> np.ndarray:
    count = len(data) // 2
    arr = struct.unpack(f"<{count}h", data)
    return np.array(arr, dtype=np.float32) / 32768.0
```

### 3. VAD + transcription loop

```python
for frame in capture_frames():
    prob = vad(frame, 16000)
    # Track speech/silence windows
    # On speech-end: concatenate accumulated frames, transcribe in thread
```

### 4. Transcription

```python
segments, info = whisper.transcribe(audio_array, beam_size=1)
text = " ".join(seg.text for seg in segments)
```

## macOS-specific notes

### Microphone permission
- The process running ffmpeg (Terminal, python, or your app) needs mic access
- Grant in **System Settings → Privacy & Security → Microphone**
- If denied, ffmpeg captures silence; check Console.app for `avfoundation` errors

### Audio device selection
- `:0` = default input device (built-in mic)
- `:1` = second input (USB mic, etc.)
- List devices: `ffmpeg -f avfoundation -list_devices true -i ""`
- External mic IDs may change on reconnect; use :0 for most cases

### Background process & mic
- Terminal.app needs to be in the foreground (or have mic permission as background)
- LaunchAgent processes get mic permission independently via `tccutil`

## Model sizes & performance

| Model | Parameters | Load time (Intel) | RTF (CPU) | Quality |
|-------|-----------|-------------------|-----------|---------|
| tiny  | 39M       | ~7s               | ~0.3x     | Basic   |
| base  | 74M       | ~8s               | ~0.2x     | Decent  |
| small | 244M      | ~15s              | ~0.1x     | Good    |
| medium| 769M      | ~30s              | ~0.05x    | Better  |

- RTF < 1 = faster than real-time
- Model weights cache to `~/.cache/huggingface/hub/`

## Pitfalls

1. **OpenMP crash on import order** — always import faster_whisper before silero_vad
2. **ffmpeg PIPE blocking** — capture thread must continuously read ffmpeg stdout, or the pipe buffer fills (default 64KB on macOS) and ffmpeg hangs silently
3. **Segfault on exit** — benign, caused by OpenMP cleanup conflict
4. **Mic permission** — Terminal needs explicit mic access in System Settings; first run of ffmpeg triggers the permission prompt
5. **Model download timeout** — models are ~150MB-1.5GB; use Chinese mirrors (`pypi.tuna.tsinghua.edu.cn`) if downloads are slow
6. **numpy version** — torch 2.2.x requires numpy<2 on Intel Mac; upgrade numpy causes import crash
7. **VAD threshold tuning** — default 0.5 works for quiet rooms; noisy environments may need adjustment

## Templates

- `templates/voice_pipeline.py` — Full runnable pipeline script. Includes argparser, model loading (Whisper first), ffmpeg capture thread, VAD loop, and transcription output. Use as a starting point for your own pipeline.

## Verification

```bash
# 1. List audio devices
KMP_DUPLICATE_LIB_OK=TRUE python voice_pipeline.py --list-dev

# 2. Run with tiny model (fastest)
KMP_DUPLICATE_LIB_OK=TRUE python voice_pipeline.py --model tiny

# 3. Validate models load in correct order
KMP_DUPLICATE_LIB_OK=TRUE python3 -c "
from faster_whisper import WhisperModel
import silero_vad
vad = silero_vad.load_silero_vad(onnx=True)
whisper = WhisperModel('tiny', device='cpu', compute_type='int8')
print('Models OK')
"
```
