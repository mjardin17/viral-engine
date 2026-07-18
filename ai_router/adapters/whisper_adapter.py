"""
whisper_adapter.py — SUBTITLE_CREATION via openai-whisper (local, free).

Requires: pip install openai-whisper (+ ffmpeg, already in the pipeline).
Payload: {"audio_path": path, "dest": optional .srt path, "model": "base"}
Output: path to the generated .srt file.
"""

from __future__ import annotations

from pathlib import Path

from .base_adapter import AdapterBase, AdapterResult


def _fmt_ts(seconds: float) -> str:
    """SRT timestamp: HH:MM:SS,mmm."""
    ms = int(round(seconds * 1000))
    h, rem = divmod(ms, 3_600_000)
    m, rem = divmod(rem, 60_000)
    s, ms = divmod(rem, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def segments_to_srt(segments: list[dict]) -> str:
    """Convert whisper transcription segments to SRT text."""
    lines: list[str] = []
    for i, seg in enumerate(segments, start=1):
        lines.append(str(i))
        lines.append(f"{_fmt_ts(float(seg['start']))} --> {_fmt_ts(float(seg['end']))}")
        lines.append(str(seg.get("text", "")).strip())
        lines.append("")
    return "\n".join(lines)


class WhisperAdapter(AdapterBase):
    """Local Whisper transcription → .srt subtitle file."""

    name = "whisper"
    capability_score = 0.90
    default_cost_usd = 0.0

    def is_connected(self) -> bool:
        try:
            import whisper  # noqa: F401
            return True
        except ImportError:
            return False

    def execute(self, payload: dict) -> AdapterResult:
        if not self.is_connected():
            return AdapterResult(success=False,
                                 error="openai-whisper not installed "
                                       "(pip install openai-whisper)")
        audio = Path(payload.get("audio_path") or payload.get("prompt") or "")
        if not audio.exists():
            return AdapterResult(success=False,
                                 error=f"audio_path not found: {audio}")
        dest = Path(payload.get("dest") or audio.with_suffix(".srt"))
        model_name = str(payload.get("model", "base"))
        try:
            import whisper

            def _run():
                model = whisper.load_model(model_name)
                return model.transcribe(str(audio))

            result, ms = self._timed(_run)
            segments = result.get("segments") or []
            if not segments:
                return AdapterResult(success=False, latency_ms=ms,
                                     error="whisper produced no segments")
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(segments_to_srt(segments), encoding="utf-8")
            return AdapterResult(success=True, output=str(dest), latency_ms=ms,
                                 meta={"language": result.get("language", "")})
        except Exception as e:
            return AdapterResult(success=False, error=f"whisper: {e}")
