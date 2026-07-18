"""
ffmpeg_adapter.py — RENDERING (the only option; capability 1.0).

Wraps the EXISTING video_effects._find_ffmpeg() discovery. execute() runs
an arbitrary ffmpeg arg list: {"args": [...], "dest": expected output path}.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from .base_adapter import BASE_DIR, AdapterBase, AdapterResult

if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))


def _ffmpeg() -> str | None:
    """Locate ffmpeg via the existing video_effects helper. None if missing."""
    try:
        from video_effects import _find_ffmpeg
        return _find_ffmpeg()
    except Exception:
        return None


class FFmpegAdapter(AdapterBase):
    """FFmpeg render/mux/concat executor — local, free, always preferred."""

    name = "ffmpeg"
    capability_score = 1.0
    default_cost_usd = 0.0

    def is_connected(self) -> bool:
        return _ffmpeg() is not None

    def execute(self, payload: dict) -> AdapterResult:
        ffmpeg = _ffmpeg()
        if ffmpeg is None:
            return AdapterResult(success=False, error="ffmpeg not found")
        args = payload.get("args")
        if not isinstance(args, list) or not args:
            return AdapterResult(success=False,
                                 error="payload needs 'args': list of ffmpeg arguments")
        try:
            def _run():
                return subprocess.run([ffmpeg, "-y", *[str(a) for a in args]],
                                      capture_output=True, text=True,
                                      encoding="utf-8", errors="replace")

            result, ms = self._timed(_run)
            if result.returncode != 0:
                return AdapterResult(success=False, latency_ms=ms,
                                     error=f"ffmpeg failed: "
                                           f"{(result.stderr or '')[-300:]}")
            dest = payload.get("dest")
            if dest and not Path(dest).exists():
                return AdapterResult(success=False, latency_ms=ms,
                                     error=f"ffmpeg ok but output missing: {dest}")
            return AdapterResult(success=True, output=str(dest) if dest else "ok",
                                 latency_ms=ms)
        except Exception as e:
            return AdapterResult(success=False, error=f"ffmpeg: {e}")
