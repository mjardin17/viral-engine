"""
kokoro_adapter.py — NARRATION (PRIMARY: local, unlimited, free).

Wraps the existing voice-music-factory/tts_cli.py flow exactly as
empire_render.tts_narrate() does. Never duplicates TTS logic — same venv
python, same CLI args.

Payload: {"text": str, "dest": wav path, "voice": str, "speed": float}
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from .base_adapter import BASE_DIR, AdapterBase, AdapterResult

KOKORO_VENV_PYTHON = BASE_DIR / "voice-music-factory" / "venv" / "Scripts" / "python.exe"
PYTHON_MAIN = Path(r"C:\Users\jjard\AppData\Local\Programs\Python\Python314\python.exe")
TTS_CLI = BASE_DIR / "voice-music-factory" / "tts_cli.py"


class KokoroAdapter(AdapterBase):
    """Kokoro local TTS — Empire OS primary voice engine. Always free."""

    name = "kokoro"
    capability_score = 0.85
    default_cost_usd = 0.0

    def is_connected(self) -> bool:
        return True  # local — tts_cli existence is checked at execute time

    def execute(self, payload: dict) -> AdapterResult:
        text = str(payload.get("text") or payload.get("prompt") or "").strip()
        if not text:
            return AdapterResult(success=False, error="payload missing 'text'")
        if not TTS_CLI.exists():
            return AdapterResult(success=False,
                                 error=f"tts_cli.py not found at {TTS_CLI}")
        dest = Path(payload.get("dest") or "kokoro_narration.wav")
        voice = str(payload.get("voice", "bm_george"))
        speed = float(payload.get("speed", 0.95))
        dest.parent.mkdir(parents=True, exist_ok=True)
        python = KOKORO_VENV_PYTHON if KOKORO_VENV_PYTHON.exists() else PYTHON_MAIN
        cmd = [str(python), str(TTS_CLI), "--text", text, "--voice", voice,
               "--speed", str(speed), "--out", str(dest)]
        try:
            def _run():
                return subprocess.run(cmd, capture_output=True, text=True,
                                      encoding="utf-8", errors="replace")

            result, ms = self._timed(_run)
            if result.returncode != 0 or not dest.exists() \
                    or dest.stat().st_size < 1000:
                return AdapterResult(success=False, latency_ms=ms,
                                     error=f"kokoro TTS failed: "
                                           f"{(result.stderr or '')[-200:]}")
            return AdapterResult(success=True, output=str(dest), latency_ms=ms)
        except Exception as e:
            return AdapterResult(success=False, error=f"kokoro: {e}")
