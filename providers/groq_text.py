"""
providers/groq_text.py

Groq — free, extremely fast LLM inference (OpenAI-compatible API).
Used to turn narration chunks into smart image prompts, saving Gemini's
free text quota for image generation.

Free tier: ~1,000 requests/day on llama-3.3-70b-versatile — plenty for the
~48-60 prompt calls a GG episode needs.

Setup (30 seconds — see FREE_API_SETUP.md):
  https://console.groq.com → API Keys → create → GROQ_API_KEY in .env

This is a TEXT provider — it deliberately does not subclass ProviderBase
(that interface is for audiovisual generation). empire_render.py calls
generate_image_prompt() directly.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
# Tried in order — first model that answers wins.
MODEL_CANDIDATES: tuple[str, ...] = (
    "llama-3.3-70b-versatile",
    "llama-3.1-8b-instant",
)
LOG_TAG = "[groq_text]"


def _load_env() -> None:
    """Populate os.environ from the repo-root .env (never overrides existing vars)."""
    env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
    if not os.path.exists(env_path):
        return
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key, value = key.strip(), value.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = value


class GroqTextProvider:
    """Groq free LLM — narration chunk → one-line historical image prompt."""

    def __init__(self) -> None:
        _load_env()
        self.api_key: str = os.environ.get("GROQ_API_KEY", "").strip()

    def is_connected(self) -> bool:
        """True if GROQ_API_KEY is set in .env."""
        return bool(self.api_key)

    def generate_text(self, prompt: str, max_tokens: int = 100) -> str | None:
        """
        One chat completion. Tries MODEL_CANDIDATES in order.
        Returns stripped text or None. Never raises.
        """
        if not self.is_connected():
            return None
        for model in MODEL_CANDIDATES:
            payload = json.dumps({
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": max_tokens,
                "temperature": 0.7,
            }).encode("utf-8")
            req = urllib.request.Request(GROQ_API_URL, data=payload, method="POST", headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            })
            try:
                with urllib.request.urlopen(req, timeout=30) as resp:
                    result = json.loads(resp.read().decode("utf-8"))
                text = ((result.get("choices") or [{}])[0]
                        .get("message", {}).get("content", "") or "").strip()
                if text:
                    return text
                print(f"{LOG_TAG} {model} returned empty content — trying next", flush=True)
            except urllib.error.HTTPError as e:
                body = e.read().decode("utf-8", errors="replace")[:300]
                print(f"{LOG_TAG} {model} HTTP {e.code}: {body}", flush=True)
            except Exception as e:
                print(f"{LOG_TAG} {model} failed: {e}", flush=True)
        return None

    def generate_image_prompt(self, narration_chunk: str) -> str | None:
        """
        Turn a narration chunk into one specific historical-image description.
        Returns a single clean line (capped at 300 chars) or None on failure.
        """
        ask = (
            "You are creating visuals for a history documentary. "
            f"The narrator says: '{narration_chunk}'. "
            "In ONE sentence, describe the most powerful specific historical "
            "image for this exact moment. Name the person, location, action. "
            "Style: historical oil painting."
        )
        text = self.generate_text(ask, max_tokens=100)
        if not text:
            return None
        return " ".join(text.split())[:300]
