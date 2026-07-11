#!/usr/bin/env python3
"""
tts_cli.py — CLI wrapper for Kokoro TTS
Called by auto_render.py via subprocess using the venv Python.

Usage:
    python tts_cli.py --text "Hello world" --voice am_adam --speed 0.65 --out /path/to/output.wav

Exit 0 on success, 1 on failure.
"""

import argparse
import asyncio
import sys
from pathlib import Path

# Ensure the factory module is importable when called from anywhere
sys.path.insert(0, str(Path(__file__).parent))
from voice_music_factory import generate_speech


async def _run(text: str, voice: str, speed: float, out: Path) -> None:
    audio_bytes = await generate_speech(text, voice, speed)
    if len(audio_bytes) < 1000:
        raise RuntimeError(f"Output too small ({len(audio_bytes)} bytes) — likely silence or error")
    out.write_bytes(audio_bytes)


def main() -> None:
    ap = argparse.ArgumentParser(description="Kokoro TTS CLI")
    ap.add_argument("--text",  required=True, help="Text to synthesize")
    ap.add_argument("--voice", default="am_adam", help="Kokoro voice ID")
    ap.add_argument("--speed", type=float, default=1.0, help="Speed multiplier (0.7–1.5)")
    ap.add_argument("--out",   required=True, help="Output .wav path")
    args = ap.parse_args()

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)

    try:
        asyncio.run(_run(args.text, args.voice, args.speed, out))
        print(f"[TTS-CLI] OK: {out} ({out.stat().st_size} bytes)")
        sys.exit(0)
    except Exception as e:
        print(f"[TTS-CLI] ERROR: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
