"""
elevenlabs_adapter.py — NARRATION via ElevenLabs TTS.

Uses ELEVENLABS_API_KEY + ELEVENLABS_VOICE_ID (repo .env).
NOT the primary pipeline voice (Kokoro is — local/unlimited/free); this is
the premium option for ViralVox-grade output.
Payload: {"text": str, "dest": mp3 path, "voice_id": optional override}
"""

from __future__ import annotations

import json
import urllib.request
from pathlib import Path

from .base_adapter import AdapterBase, AdapterResult, env

API_URL = "https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"


class ElevenLabsAdapter(AdapterBase):
    """ElevenLabs TTS — premium narration (paid per character)."""

    name = "elevenlabs"
    capability_score = 0.92
    default_cost_usd = 0.10  # ~ per typical scene narration

    def is_connected(self) -> bool:
        return bool(env("ELEVENLABS_API_KEY"))

    def get_cost_estimate(self, payload: dict) -> float:
        chars = len(str(payload.get("text", payload.get("prompt", ""))))
        return round(chars * 0.00003, 4)  # ~$0.03 per 1k chars ballpark

    def execute(self, payload: dict) -> AdapterResult:
        if not self.is_connected():
            return AdapterResult(success=False, error="ELEVENLABS_API_KEY not set")
        text = str(payload.get("text") or payload.get("prompt") or "").strip()
        if not text:
            return AdapterResult(success=False, error="payload missing 'text'")
        voice_id = str(payload.get("voice_id") or env("ELEVENLABS_VOICE_ID")
                       or "JBFqnCBsd6RMkjVDRZzb")
        dest = Path(payload.get("dest") or "elevenlabs_narration.mp3")
        body = json.dumps({
            "text": text,
            "model_id": "eleven_multilingual_v2",
            "voice_settings": {"stability": 0.5, "similarity_boost": 0.75},
        }).encode("utf-8")
        try:
            def _call() -> bytes:
                req = urllib.request.Request(
                    API_URL.format(voice_id=voice_id), data=body,
                    headers={"xi-api-key": env("ELEVENLABS_API_KEY"),
                             "Content-Type": "application/json",
                             "Accept": "audio/mpeg"},
                    method="POST")
                with urllib.request.urlopen(req, timeout=180) as resp:
                    return resp.read()

            data, ms = self._timed(_call)
            if len(data) < 1000:
                return AdapterResult(success=False, latency_ms=ms,
                                     error=f"ElevenLabs returned {len(data)}B")
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(data)
            return AdapterResult(success=True, output=str(dest), latency_ms=ms,
                                 cost_usd=self.get_cost_estimate(payload))
        except Exception as e:
            return AdapterResult(success=False, error=f"elevenlabs: {e}")
