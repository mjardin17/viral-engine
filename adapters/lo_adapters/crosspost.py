"""
CrossPost Studio Adapter — Production manager & asset hub (stub)

CrossPost Enterprise runs at localhost:3000.
When ready to integrate:
  1. Ensure CrossPost Enterprise is running (cd empire-os-patch/apps/crosspost-enterprise && npm start)
  2. Implement push_episode(), queue_render(), publish_asset()
"""

from __future__ import annotations
import json
import os
import urllib.request
from .base import BaseAdapter, AdapterStatus


class CrossPostAdapter(BaseAdapter):
    name = "CrossPost Studio"
    description = "Production manager — store projects, queue jobs, publish content"
    version = "0.0.1-stub"

    def __init__(self) -> None:
        self.url = os.environ.get("CROSSPOST_URL", "http://localhost:3000")

    def health_check(self) -> AdapterStatus:
        try:
            req = urllib.request.Request(f"{self.url}/api/health", method="GET")
            with urllib.request.urlopen(req, timeout=3) as resp:
                data = json.loads(resp.read().decode())
                return AdapterStatus(
                    available=True,
                    name=self.name,
                    message=f"CrossPost running — {data.get('status', 'ok')}",
                    config={"url": self.url},
                )
        except Exception as e:
            return AdapterStatus(
                available=False,
                name=self.name,
                message=f"CrossPost offline: {e}. Start with: cd empire-os-patch/apps/crosspost-enterprise && npm start",
            )

    def push_episode(self, episode_json: dict) -> dict:
        """Push completed LO episode to CrossPost project store."""
        raise NotImplementedError("CrossPost push not yet wired — stub only")

    def queue_render(self, episode_id: str) -> str:
        """Add episode to CrossPost render queue. Returns job ID."""
        raise NotImplementedError("CrossPost render queue not yet wired — stub only")
