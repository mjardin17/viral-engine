"""Ollama Adapter — Tier 1 AI (local, free)"""

from __future__ import annotations
import json
import os
import urllib.request
import urllib.error

from .base import BaseAdapter, AdapterStatus


class OllamaAdapter(BaseAdapter):
    name = "Ollama"
    description = "Local Ollama inference — free, private"
    version = "1.0.0"

    def __init__(self) -> None:
        self.url = os.environ.get("OLLAMA_URL", "http://localhost:11434")
        self.model = os.environ.get("OLLAMA_MODEL", "qwen2.5-coder:7b")

    def health_check(self) -> AdapterStatus:
        try:
            req = urllib.request.Request(f"{self.url}/api/tags", method="GET")
            with urllib.request.urlopen(req, timeout=3) as resp:
                data = json.loads(resp.read().decode())
                models = [m["name"] for m in data.get("models", [])]
                return AdapterStatus(
                    available=True,
                    name=self.name,
                    version="1.0.0",
                    message=f"Running — {len(models)} model(s) loaded",
                    config={"url": self.url, "default_model": self.model, "models": models},
                )
        except Exception as e:
            return AdapterStatus(available=False, name=self.name, message=f"Offline: {e}")

    def generate(self, prompt: str, system: str = "", model: str | None = None, timeout: int = 120) -> str:
        payload = {
            "model": model or self.model,
            "prompt": prompt,
            "system": system,
            "stream": False,
        }
        req = urllib.request.Request(
            f"{self.url}/api/generate",
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            result = json.loads(resp.read().decode())
            return result.get("response", "")

    def is_available(self) -> bool:
        return self.health_check().available
