"""
Video Factory Adapter — AI video production pipeline (stub)

Video Factory handles: image → video → audio → final MP4.
When ready to integrate:
  1. Set VIDEO_FACTORY_URL in .env
  2. Implement render_episode(), get_render_status()
"""

from __future__ import annotations
import os
import json
import urllib.request
from .base import BaseAdapter, AdapterStatus


class VideoFactoryAdapter(BaseAdapter):
    name = "Video Factory"
    description = "AI video production — image gen, TTS, FFmpeg assembly"
    version = "0.0.1-stub"

    def __init__(self) -> None:
        self.url = os.environ.get("VIDEO_FACTORY_URL", "http://localhost:3002")

    def health_check(self) -> AdapterStatus:
        try:
            req = urllib.request.Request(f"{self.url}/api/health", method="GET")
            with urllib.request.urlopen(req, timeout=3) as resp:
                data = json.loads(resp.read().decode())
                return AdapterStatus(available=True, name=self.name, message="Video Factory ready")
        except Exception as e:
            return AdapterStatus(
                available=False,
                name=self.name,
                message=f"Video Factory offline: {e}",
            )

    def render_episode(self, episode_json: dict) -> str:
        """Start render job. Returns job ID."""
        raise NotImplementedError("Video Factory not wired — use auto_render.py directly for now")

    def get_render_status(self, job_id: str) -> dict:
        raise NotImplementedError("Video Factory not wired — stub only")

    def get_render_command(self, episode_id: str) -> str:
        """Returns the manual render command for this episode."""
        return f"python auto_render.py --episode {episode_id}"
