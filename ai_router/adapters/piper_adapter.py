"""
piper_adapter.py — NARRATION offline fallback (local Piper TTS binary).

is_connected(): piper binary on PATH or in tools/.
Payload: {"text": str, "dest": wav path, "model": optional .onnx voice path}
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from .base_adapter import BASE_DIR, AdapterBase, AdapterResult


def _find_piper() -> str | None:
    """Locate the piper binary: PATH first, then tools/."""
    if p := shutil.which("piper"):
        return p
    for candidate in (BASE_DIR / "tools" / "piper" / "piper.exe",
                      BASE_DIR / "tools" / "piper.exe",
                      BASE_DIR / "tools" / "piper" / "piper"):
        if candidate.exists():
            return str(candidate)
    return None


class PiperAdapter(AdapterBase):
    """Piper TTS — fully offline narration fallback."""

    name = "piper"
    capability_score = 0.75
    default_cost_usd = 0.0

    def is_connected(self) -> bool:
        return _find_piper() is not None

    def execute(self, payload: dict) -> AdapterResult:
        piper = _find_piper()
        if piper is None:
            return AdapterResult(success=False,
                                 error="piper binary not found (PATH or tools/)")
        text = str(payload.get("text") or payload.get("prompt") or "").strip()
        if not text:
            return AdapterResult(success=False, error="payload missing 'text'")
        dest = Path(payload.get("dest") or "piper_narration.wav")
        dest.parent.mkdir(parents=True, exist_ok=True)
        cmd = [piper, "--output_file", str(dest)]
        if model := payload.get("model"):
            cmd += ["--model", str(model)]
        try:
            def _run():
                return subprocess.run(cmd, input=text, capture_output=True,
                                      text=True, encoding="utf-8", errors="replace")

            result, ms = self._timed(_run)
            if result.returncode != 0 or not dest.exists() \
                    or dest.stat().st_size < 1000:
                return AdapterResult(success=False, latency_ms=ms,
                                     error=f"piper failed: "
                                           f"{(result.stderr or '')[-200:]}")
            return AdapterResult(success=True, output=str(dest), latency_ms=ms)
        except Exception as e:
            return AdapterResult(success=False, error=f"piper: {e}")
