"""
providers/base.py

Abstract base class for all video/audio generation providers.
Every provider (Higgsfield, Kling, Veo, Runway) must implement this interface.
"""

from abc import ABC, abstractmethod
from pathlib import Path
import urllib.request


class ProviderBase(ABC):
    """
    Shared interface for all generation providers.
    Methods return a dict with at minimum:
        {"status": "ok"|"not_connected"|"error", "job_id": str|None, ...}
    """

    @abstractmethod
    def is_connected(self) -> bool:
        """Return True if API key is set and provider is reachable."""
        ...

    @abstractmethod
    def generate_video(self, prompt: str, reference_image_path: str | None = None,
                       aspect_ratio: str = "16:9", duration_sec: int = 8) -> dict:
        """Submit a video generation job. Returns job info dict."""
        ...

    @abstractmethod
    def generate_image(self, prompt: str, aspect_ratio: str = "3:4") -> dict:
        """Submit an image generation job. Returns job info dict."""
        ...

    @abstractmethod
    def generate_audio(self, prompt: str, voice: str = "Hades",
                       duration_sec: int = 10) -> dict:
        """Submit a narration/TTS audio generation job."""
        ...

    @abstractmethod
    def generate_music(self, prompt: str, duration_sec: int = 300) -> dict:
        """Submit a music generation job."""
        ...

    @abstractmethod
    def generate_sfx(self, prompt: str, duration_sec: int = 5) -> dict:
        """Submit a sound effect generation job."""
        ...

    @abstractmethod
    def get_job_status(self, job_id: str) -> dict:
        """Poll status of a submitted job. Returns {"status": ..., "output_url": ...}"""
        ...

    def download_clip(self, output_url: str, dest_path: str | Path) -> bool:
        """
        Download a finished clip/asset from output_url to dest_path.
        Returns True on success (file exists and is >10KB). Never raises.
        """
        dest = Path(dest_path)
        try:
            dest.parent.mkdir(parents=True, exist_ok=True)
            req = urllib.request.Request(output_url, headers={"User-Agent": "EmpireOS/1.0"})
            with urllib.request.urlopen(req, timeout=300) as resp:
                data = resp.read()
            if len(data) < 10_000:
                return False
            dest.write_bytes(data)
            return True
        except Exception:
            dest.unlink(missing_ok=True)
            return False

    def not_connected_response(self, operation: str) -> dict:
        return {
            "status": "not_connected",
            "job_id": None,
            "operation": operation,
            "message": f"Provider '{self.__class__.__name__}' not connected — set the required API key.",
        }
