#!/usr/bin/env python3
import os
import sys
from faster_whisper import WhisperModel


def main():
    if len(sys.argv) < 2:
        print("Usage: transcribe.py <wav_path>", file=sys.stderr)
        sys.exit(1)

    wav_path = sys.argv[1]
    model_size = os.getenv("TRANSCRIPTION_MODEL", "small")

    model = WhisperModel(model_size, device="cpu")
    segments, _ = model.transcribe(wav_path)
    text = "".join(segment.text for segment in segments)
    print(text.strip())


if __name__ == "__main__":
    main()
