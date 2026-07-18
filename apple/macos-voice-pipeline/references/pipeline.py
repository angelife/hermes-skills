#!/usr/bin/env python3
"""
macOS real-time voice pipeline — ffmpeg → silero-vad → faster-whisper
Stream raw PCM through subprocess PIPE, no temp WAV files.

Usage:
  python pipeline.py                         # continuous listen + transcribe
  python pipeline.py --list-dev              # list avfoundation devices
  python pipeline.py --model tiny            # use tiny model (fastest)
  python pipeline.py --model base --device :1  # base model, USB mic

Keywords: faster-whisper, silero-vad, ffmpeg avfoundation,
          real-time voice, speech-to-text, macOS Intel
"""

import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"  # silence OpenMP conflict

import argparse
import struct
import subprocess
import sys
import threading
import time
from collections.abc import Generator

import numpy as np
from faster_whisper import WhisperModel  # MUST import before silero_vad
import silero_vad
import torch

# ── Config ──────────────────────────────────────────────────────────
SAMPLE_RATE = 16000
CHANNELS = 1
SAMPLE_WIDTH = 2  # s16le
BYTES_PER_FRAME = SAMPLE_WIDTH * CHANNELS
VAD_FRAME_SIZE = 512  # samples (32ms @ 16kHz)
VAD_WINDOW_SIZE = 3   # consecutive speech frames to trigger "speech started"
SILENCE_WINDOW = 10   # consecutive silence frames to end utterance
MIN_UTTERANCE_MS = 300
WHISPER_MODEL = "base"  # "tiny" | "base" | "small" | "medium"
AUDIO_DEVICE = ":0"  # avfoundation default mic


# ── Init models (lazy, on first use) ────────────────────────────────
_vad = None
_whisper = None
_models_loaded = False


def get_vad():
    global _vad
    if _vad is None:
        _vad = silero_vad.load_silero_vad(onnx=True)
    return _vad


def get_whisper():
    global _whisper
    if _whisper is None:
        _whisper = WhisperModel(
            WHISPER_MODEL, device="cpu", compute_type="int8",
        )
    return _whisper


def load_models():
    """Load models in correct order: Whisper first, then VAD."""
    global _models_loaded
    if _models_loaded:
        return
    get_whisper()  # MUST load Whisper first (ctranslate2 OpenMP init)
    get_vad()      # then VAD (onnxruntime)
    _models_loaded = True


# ── Audio capture ──────────────────────────────────────────────────
def list_devices() -> None:
    """List avfoundation audio input devices."""
    subprocess.run(
        ["ffmpeg", "-f", "avfoundation", "-list_devices", "true", "-i", ""],
        stderr=subprocess.STDOUT,
    )


def s16le_to_float32(data: bytes) -> np.ndarray:
    """Convert raw s16le PCM bytes to float32 numpy array (range [-1, 1])."""
    count = len(data) // BYTES_PER_FRAME
    arr = struct.unpack(f"<{count}h", data)
    return np.array(arr, dtype=np.float32) / 32768.0


def capture_frames(
    device: str = AUDIO_DEVICE,
    frame_size: int = VAD_FRAME_SIZE,
) -> Generator[np.ndarray, None, None]:
    """
    Yield float32 numpy arrays (frame_size samples) from the mic.
    Runs ffmpeg in a subprocess and reads stdout in a separate thread
    to prevent pipe buffer blocking.
    """
    cmd = [
        "ffmpeg",
        "-f", "avfoundation",
        "-i", device,
        "-f", "s16le",
        "-ac", str(CHANNELS),
        "-ar", str(SAMPLE_RATE),
        "-loglevel", "error",
        "-",
    ]
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    frame_bytes = frame_size * BYTES_PER_FRAME
    buf = b""

    try:
        while True:
            chunk = proc.stdout.read(frame_bytes * 4)  # read 4 frames at a time
            if not chunk:
                break
            buf += chunk

            # yield complete frames
            while len(buf) >= frame_bytes:
                frame_data = buf[:frame_bytes]
                buf = buf[frame_bytes:]
                yield s16le_to_float32(frame_data)
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            proc.kill()


# ── VAD + transcription loop ────────────────────────────────────────
def run_pipeline() -> None:
    """Continuous listen → VAD → transcribe."""
    print(f"Listening on avfoundation device {AUDIO_DEVICE} ...")
    print(f"Whisper model: {WHISPER_MODEL}")
    print("Press Ctrl+C to stop.\n")

    vad = get_vad()
    whisper = get_whisper()

    speech_frames: list[np.ndarray] = []
    speech_count = 0
    silence_count = 0
    is_speaking = False
    frame_idx = 0

    try:
        for frame in capture_frames():
            # Silero VAD expects a 1-D float32 tensor/array
            prob = vad(frame, SAMPLE_RATE)

            if prob > 0.5:
                speech_count += 1
                silence_count = 0
            else:
                silence_count += 1
                if not is_speaking:
                    speech_count = 0

            # Speech started (consecutive speech frames)
            if not is_speaking and speech_count >= VAD_WINDOW_SIZE:
                is_speaking = True
                speech_frames = [frame] * VAD_WINDOW_SIZE

            # Accumulate audio during speech
            if is_speaking:
                speech_frames.append(frame)

            # Speech ended (silence threshold reached)
            if is_speaking and silence_count >= SILENCE_WINDOW:
                utterance = np.concatenate(speech_frames)
                dur_ms = len(utterance) / SAMPLE_RATE * 1000

                if dur_ms >= MIN_UTTERANCE_MS:
                    t = threading.Thread(
                        target=transcribe_and_print,
                        args=(utterance,),
                        daemon=True,
                    )
                    t.start()

                speech_frames = []
                speech_count = 0
                silence_count = 0
                is_speaking = False

            frame_idx += 1

    except KeyboardInterrupt:
        print("\nStopped.")
    except Exception:
        print(f"\nError: {sys.exc_info()[1]}")


def transcribe_and_print(audio: np.ndarray) -> None:
    """Transcribe audio array and print result."""
    try:
        whisper = get_whisper()
        segments, info = whisper.transcribe(audio, beam_size=1)

        text = " ".join(seg.text for seg in segments)
        if text.strip():
            dur = len(audio) / SAMPLE_RATE
            print(f"[{dur:.1f}s] {text.strip()}")
    except Exception as e:
        print(f"[transcribe error] {e}")


# ── CLI ─────────────────────────────────────────────────────────────
def main():
    global WHISPER_MODEL, AUDIO_DEVICE
    parser = argparse.ArgumentParser(description="Real-time voice pipeline")
    parser.add_argument("--list-dev", action="store_true", help="List audio devices")
    parser.add_argument("--model", default=WHISPER_MODEL, help="Whisper model size")
    parser.add_argument("--device", default=AUDIO_DEVICE, help="avfoundation device")
    args = parser.parse_args()

    if args.list_dev:
        list_devices()
        return

    WHISPER_MODEL = args.model
    AUDIO_DEVICE = args.device

    print("Loading models (first run downloads ~1GB)...")
    t0 = time.time()
    try:
        load_models()
    except Exception as e:
        print(f"Model loading failed: {e}")
        sys.exit(1)
    print(f"Models ready ({time.time()-t0:.1f}s)\n")

    run_pipeline()


if __name__ == "__main__":
    main()