"""
StoryForge Adapter — Story management platform (stub)

When StoryForge is ready to integrate:
  1. Add STORYFORGE_API_KEY + STORYFORGE_URL to .env
  2. Implement push_episode(), pull_episode(), list_projects()
  3. Set self._ready = True
"""

from __future__ import annotations
from .base import BaseAdapter, AdapterStatus
import os


class StoryForgeAdapter(BaseAdapter):
    name = "StoryForge"
    description = "Story management and versioning platform"
    version = "0.0.1-stub"

    def __init__(self) -> None:
        self.api_key = os.environ.get("STORYFORGE_API_KEY", "")
        self.url = os.environ.get("STORYFORGE_URL", "")

    def health_check(self) -> AdapterStatus:
        if not self.api_key or not self.url:
            return AdapterStatus(
                available=False,
                name=self.name,
                version=self.version,
                message="Stub — set STORYFORGE_API_KEY + STORYFORGE_URL in .env",
            )
        return AdapterStatus(available=True, name=self.name, message="Ready")

    def push_episode(self, episode_json: dict) -> str:
        """Push episode to StoryForge. Returns episode URL."""
        raise NotImplementedError("StoryForge not wired — stub only")

    def pull_episode(self, episode_id: str) -> dict:
        """Pull episode JSON from StoryForge."""
        raise NotImplementedError("StoryForge not wired — stub only")

    def list_projects(self) -> list[dict]:
        raise NotImplementedError("StoryForge not wired — stub only")
