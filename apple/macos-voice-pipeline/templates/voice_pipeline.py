#!/usr/bin/env python3
"""
Real-time macOS voice-to-text pipeline.
ffmpeg avfoundation → subprocess PIPE → Silero VAD → faster-whisper

Usage:
    KMP_DUPLICATE_LIB_OK=TRUE python voice_pipeline.py
    KMP_DUPLICATE_LIB_OK=TRUE python voice_pipeline.py --model tiny
    KMP_DUPLICATE_LIB_OK=TRUE python voice_pipeline.py --list-dev
"""

import argparse
import os
import struct
import subprocess
import sys
import time
from threading import Thread

os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

# Import order matters: faster_whisper BEFORE silero_vad
from faster_whisper import WhisperModel  # noqa: E402
import silero_vad  # noqa: E402
import numpy as np  # noqa: E402

WHISPER_MODEL = None
VAD_MODEL = None


def s16le_to_float32(data: bytes) -> np.ndarray:
    """Convert raw s16le PCM bytes to float32 numpy array."""
    count = len(data) // 2
    arr = struct.unpack(f"<{count}h", data)
    return np.array(arr, dtype=np.float32) / 32768.0


def _load_models(model_name: str = "base"):
    """Load models — Whisper first, then VAD (prevents OpenMP conflict)."""
    global WHISPER_MODEL, VAD_MODEL
    print(f"Loading models (model={model_name})...")
    t0 = time.time()
    WHISPER_MODEL = WhisperModel(model_name, device="cpu", compute_type="int8")
    VAD_MODEL = silero_vad.load_silero_vad(onnx=True)
    print(f"Models ready ({time.time() - t0:.1f}s)")


def capture_audio(device: str = ":0", sample_rate: int = 16000):
    """Yield raw PCM bytes from macOS mic via ffmpeg subprocess PIPE."""
    cmd = [
        "ffmpeg",
        "-f", "avfoundation",
        "-i", device,
        "-f", "s16le",
        "-ac", "1",
        "-ar", str(sample_rate),
        "-loglevel", "error",
        "-",
    ]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        while True:
            chunk = proc.stdout.read(4096)
            if not chunk:
                break
            yield chunk
    finally:
        proc.terminate()
        proc.wait()


def transcribe(audio_np: np.ndarray) -> str:
    """Transcribe audio array with faster-whisper."""
    segments, info = WHISPER_MODEL.transcribe(audio_np, beam_size=1)
    texts = [seg.text.strip() for seg in segments]
    return " ".join(texts)


def main():
    parser = argparse.ArgumentParser(description="Real-time macOS voice-to-text")
    parser.add_argument("--model", default="base", help="Whisper model size (tiny/base/small/medium)")
    parser.add_argument("--device", default=":0", help="avfoundation device index (e.g. :0)")
    parser.add_argument("--list-dev", action="store_true", help="List audio input devices and exit")
    args = parser.parse_args()

    if args.list_dev:
        subprocess.run(["ffmpeg", "-f", "avfoundation", "-list_devices", "true", "-i", ""])
        return

    _load_models(args.model)
    sample_rate = 16000
    frame_size = 512  # 32ms @ 16kHz

    print(f"Listening on avfoundation device {args.device} ...")
    print(f"Whisper model: {args.model}")
    print("Press Ctrl+C to stop.")

    audio_buffer = bytearray()
    speech_frames = []
    is_speaking = False
    silence_count = 0
    max_silence_frames = 10  # ~320ms of silence = end of utterance
    min_speech_frames = 30  # ~1s minimum utterance

    try:
        for raw_chunk in capture_audio(args.device, sample_rate):
            audio_buffer.extend(raw_chunk)
            frame_bytes = frame_size * 2

            while len(audio_buffer) >= frame_bytes:
                pcm = bytes(audio_buffer[:frame_bytes])
                audio_buffer = audio_buffer[frame_bytes:]
                audio_np = s16le_to_float32(pcm)

                speech_prob = VAD_MODEL(audio_np, sample_rate)
                is_active = speech_prob >= 0.5

                if is_active:
                    speech_frames.append(audio_np)
                    silence_count = 0
                    if not is_speaking:
                        is_speaking = True
                else:
                    if is_speaking:
                        silence_count += 1
                        speech_frames.append(audio_np)

                        if silence_count >= max_silence_frames:
                            # End of utterance
                            if len(speech_frames) >= min_speech_frames:
                                utterance = np.concatenate(speech_frames)
                                t0 = time.time()
                                text = transcribe(utterance)
                                elapsed = time.time() - t0
                                if text.strip():
                                    print(f"[{elapsed:.1f}s] {text}")

                            speech_frames = []
                            is_speaking = False
                            silence_count = 0
    except KeyboardInterrupt:
        print("\nStopped.")


if __name__ == "__main__":
    main()