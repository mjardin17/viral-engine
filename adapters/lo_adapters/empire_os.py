"""
Empire OS Adapter — Central routing hub (stub)

Empire OS runs at localhost:3001 (or configured EMPIRE_OS_URL).
Routes AI requests through the multi-provider registry.
"""

from __future__ import annotations
import json
import os
import urllib.request
from .base import BaseAdapter, AdapterStatus


class EmpireOSAdapter(BaseAdapter):
    name = "Empire OS"
    description = "Central AI routing hub — Ollama / Gemini / OpenAI via unified API"
    version = "0.0.1-stub"

    def __init__(self) -> None:
        self.url = os.environ.get("EMPIRE_OS_URL", "http://localhost:3001")

    def health_check(self) -> AdapterStatus:
        try:
            req = urllib.request.Request(f"{self.url}/api/health", method="GET")
            with urllib.request.urlopen(req, timeout=3) as resp:
                data = json.loads(resp.read().decode())
                return AdapterStatus(
                    available=True,
                    name=self.name,
                    message=f"Empire OS alive — {data.get('status', 'ok')}",
                    config={"url": self.url},
                )
        except Exception as e:
            return AdapterStatus(
                available=False,
                name=self.name,
                message=f"Empire OS offline: {e}",
            )

    def ai_route(self, prompt: str, system: str = "", force_cloud: bool = False) -> str:
        """Route an AI request through Empire OS router."""
        payload = {
            "prompt": prompt,
            "system": system,
            "forceCloud": force_cloud,
        }
        req = urllib.request.Request(
            f"{self.url}/api/empire/ai-router",
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=90) as resp:
            data = json.loads(resp.read().decode())
            return data.get("response", "")
