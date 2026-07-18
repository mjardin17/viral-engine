"""
musetalk_adapter.py — LIP_SYNC via HuggingFace (TMElyralab/MuseTalk).

Uses HF_TOKEN. Primary: HF Inference API. Fallback: gradio_client Space.
Payload: {"face_path": image/video path, "audio_path": wav path, "dest": mp4 path}
"""

from __future__ import annotations

import base64
import json
import urllib.request
from pathlib import Path

from .base_adapter import AdapterBase, AdapterResult, env

HF_URL = "https://api-inference.huggingface.co/models/TMElyralab/MuseTalk"
SPACE = "TMElyralab/MuseTalk"


class MuseTalkAdapter(AdapterBase):
    """MuseTalk lip-sync — HF inference first, gradio Space fallback."""

    name = "musetalk"
    capability_score = 0.88
    default_cost_usd = 0.0  # HF free credits

    def is_connected(self) -> bool:
        return bool(env("HF_TOKEN"))

    def _inference_api(self, face: Path, audio: Path, dest: Path) -> AdapterResult:
        payload = {"inputs": {
            "video": base64.b64encode(face.read_bytes()).decode("ascii"),
            "audio": base64.b64encode(audio.read_bytes()).decode("ascii"),
        }}
        req = urllib.request.Request(
            HF_URL, data=json.dumps(payload).encode("utf-8"),
            headers={"Authorization": f"Bearer {env('HF_TOKEN')}",
                     "Content-Type": "application/json"},
            method="POST")
        with urllib.request.urlopen(req, timeout=300) as resp:
            data = resp.read()
        if len(data) < 10_000:
            return AdapterResult(success=False,
                                 error=f"HF inference returned {len(data)}B: "
                                       f"{data[:150]!r}")
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
        return AdapterResult(success=True, output=str(dest))

    def _gradio_space(self, face: Path, audio: Path, dest: Path) -> AdapterResult:
        try:
            from gradio_client import Client, handle_file
        except ImportError:
            return AdapterResult(success=False,
                                 error="gradio_client not installed "
                                       "(pip install gradio_client)")
        client = Client(SPACE, hf_token=env("HF_TOKEN"))
        result = client.predict(handle_file(str(face)), handle_file(str(audio)))
        out = Path(result[0] if isinstance(result, (list, tuple)) else result)
        if out.exists() and out.stat().st_size > 10_000:
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(out.read_bytes())
            return AdapterResult(success=True, output=str(dest))
        return AdapterResult(success=False, error="MuseTalk Space returned no video")

    def execute(self, payload: dict) -> AdapterResult:
        if not self.is_connected():
            return AdapterResult(success=False, error="HF_TOKEN not set")
        face = Path(payload.get("face_path", ""))
        audio = Path(payload.get("audio_path", ""))
        if not face.exists() or not audio.exists():
            return AdapterResult(success=False,
                                 error="musetalk needs existing 'face_path' + 'audio_path'")
        dest = Path(payload.get("dest") or "musetalk_out.mp4")
        try:
            result, ms = self._timed(self._inference_api, face, audio, dest)
            result.latency_ms = ms
            if result.success:
                return result
        except Exception as e:
            result = AdapterResult(success=False, error=f"HF inference: {e}")
        try:
            fallback, ms = self._timed(self._gradio_space, face, audio, dest)
            fallback.latency_ms = ms
            if not fallback.success:
                fallback.error = f"{result.error} | space: {fallback.error}"
            return fallback
        except Exception as e:
            return AdapterResult(success=False,
                                 error=f"{result.error} | space raised: {e}")
