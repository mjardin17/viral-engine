"""
providers/base.py

Abstract base class for all video/audio generation providers.
Every provider (Higgsfield, Kling, Veo, Runway) must implement this interface.
"""

from abc import ABC, abstractmethod


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

    def not_connected_response(self, operation: str) -> dict:
        return {
            "status": "not_connected",
            "job_id": None,
            "operation": operation,
            "message": f"Provider '{self.__class__.__name__}' not connected — set the required API key.",
        }
