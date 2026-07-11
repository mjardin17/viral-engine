"""
Higgsfield Adapter — AI Video Generation (stub)

When Higgsfield is ready to integrate:
  1. Add HIGGSFIELD_API_KEY to .env
  2. Implement generate_video() using their API
  3. Set self._ready = True

Interface contract:
  - generate_video(image_url, prompt, duration_sec, style) -> job_id
  - get_job_status(job_id) -> {"status": "pending|processing|done|failed", "url": str|None}
"""

from __future__ import annotations
from .base import BaseAdapter, AdapterStatus
import os


class HiggsFieldAdapter(BaseAdapter):
    name = "Higgsfield"
    description = "AI video generation — cinematic camera movement for LO scenes"
    version = "0.0.1-stub"
    _ready = False

    def __init__(self) -> None:
        self.api_key = os.environ.get("HIGGSFIELD_API_KEY", "")
        self._ready = bool(self.api_key)

    def health_check(self) -> AdapterStatus:
        if not self._ready:
            return AdapterStatus(
                available=False,
                name=self.name,
                version=self.version,
                message="Stub — set HIGGSFIELD_API_KEY in .env to activate",
            )
        return AdapterStatus(available=True, name=self.name, message="Ready")

    def generate_video(self, image_url: str, prompt: str, duration_sec: int = 4, style: str = "cinematic") -> str:
        """Returns a job ID string."""
        raise NotImplementedError("Higgsfield integration not yet wired — stub only")

    def get_job_status(self, job_id: str) -> dict:
        raise NotImplementedError("Higgsfield integration not yet wired — stub only")

    def get_lo_camera_prompt(self, scene_type: str, visual_prompt: str) -> str:
        """
        Returns a Higgsfield-style camera prompt for a Little Olympus scene.
        This is usable even without the full API — for manual Higgsfield use.
        """
        camera_styles = {
            "hook": "slow push-in, dreamy light rays, warm golden haze",
            "narrative": "gentle parallax drift, soft depth of field",
            "action": "dynamic follow shot, motion blur on fast elements, high energy",
            "emotional": "slow rack focus to character face, soft bokeh background",
            "teaching": "birds-eye-view tilt-shift, educational diagram feel",
            "resolution": "wide pull-out reveal, uplifting lens flare, triumphant",
        }
        camera_move = camera_styles.get(scene_type, "smooth cinematic drift")
        return f"Little Olympus bright cartoon world — {camera_move} — {visual_prompt} — kid-safe, colorful, warm"
