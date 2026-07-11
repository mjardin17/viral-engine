"""OpenAI Adapter — Tier 2 AI (cloud, paid)"""

from __future__ import annotations
import json
import os
import urllib.request
import urllib.error

from .base import BaseAdapter, AdapterStatus


class OpenAIAdapter(BaseAdapter):
    name = "OpenAI"
    description = "OpenAI API — gpt-4o-mini (default) or gpt-4o for quality tasks"
    version = "1.0.0"

    OPENAI_URL = "https://api.openai.com/v1/chat/completions"

    def __init__(self) -> None:
        self.api_key = os.environ.get("OPENAI_API_KEY", "")

    def health_check(self) -> AdapterStatus:
        if not self.api_key:
            return AdapterStatus(
                available=False,
                name=self.name,
                message="OPENAI_API_KEY not set in .env",
            )
        return AdapterStatus(
            available=True,
            name=self.name,
            message="Key loaded — ready",
            config={"key_prefix": self.api_key[:8] + "..."},
        )

    def generate(
        self,
        prompt: str,
        system: str = "",
        model: str = "gpt-4o-mini",
        temperature: float = 0.7,
        timeout: int = 60,
    ) -> str:
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY not set")

        messages: list[dict] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        payload = {"model": model, "messages": messages, "temperature": temperature}
        req = urllib.request.Request(
            self.OPENAI_URL,
            data=json.dumps(payload).encode(),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            result = json.loads(resp.read().decode())
            return result["choices"][0]["message"]["content"]

    def is_available(self) -> bool:
        return bool(self.api_key)
