"""
ai_router/adapters/omniroute_adapter.py — OmniRoute multi-provider fallback.

OmniRoute: https://omniroute.online/
Automatically routes to next best provider when primary runs out of credits.

Supports: image generation, video, TTS, reasoning across 20+ AI models.
When Claude credits exhaust, OmniRoute seamlessly switches to GPT-4, Gemini, etc.
"""

from __future__ import annotations

import json
from typing import Any

from .base_adapter import AdapterBase, AdapterResult, env


class OmniRouteAdapter(AdapterBase):
    """Multi-provider AI router with automatic fallback + credit management."""

    name = "OmniRoute"
    capability_score = 0.85  # High score — meta-router, always works if any provider online
    default_cost_usd = 0.0  # Cost depends on which provider OmniRoute chooses

    def __init__(self):
        self.api_key = env("OMNIROUTE_API_KEY")
        self.api_endpoint = env("OMNIROUTE_ENDPOINT") or "https://api.omniroute.online/v1"
        self.fallback_providers = [
            "gpt-4",
            "claude-opus",
            "gemini-pro",
            "mistral-large",
            "llama-2-70b",
        ]

    def is_connected(self) -> bool:
        """OmniRoute is available if API key is set."""
        return bool(self.api_key)

    def execute(self, payload: dict) -> AdapterResult:
        """
        Route task to OmniRoute. Payload contains:
          task_type: 'image_gen' | 'video' | 'tts' | 'reasoning' | 'video_editing'
          prompt: str
          params: dict (model-specific options)
          budget_usd: float (max spend for this task)
        """
        try:
            import requests
        except ImportError:
            return AdapterResult(
                success=False,
                error="OmniRoute adapter requires 'requests' (pip install requests)",
            )

        if not self.is_connected():
            return AdapterResult(success=False, error="OmniRoute API key not set (OMNIROUTE_API_KEY)")

        task_type = payload.get("task_type", "reasoning")
        prompt = payload.get("prompt", "")
        params = payload.get("params", {})
        budget_usd = payload.get("budget_usd", 1.0)

        # Build OmniRoute request
        body = {
            "task_type": task_type,
            "prompt": prompt,
            "params": params,
            "budget_usd": budget_usd,
            "fallback_providers": self.fallback_providers,
            "auto_switch": True,  # Key: switch to next provider if current exhausted
        }

        try:
            start_time = __import__("time").monotonic()
            resp = requests.post(
                f"{self.api_endpoint}/route",
                headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                json=body,
                timeout=300,
            )
            latency_ms = int((__import__("time").monotonic() - start_time) * 1000)

            if resp.status_code not in (200, 201):
                return AdapterResult(
                    success=False,
                    error=f"OmniRoute HTTP {resp.status_code}: {resp.text[:200]}",
                    latency_ms=latency_ms,
                )

            data = resp.json()
            return AdapterResult(
                success=data.get("success", False),
                output=data.get("output"),
                cost_usd=float(data.get("cost_usd", 0.0)),
                latency_ms=latency_ms,
                meta={
                    "provider_used": data.get("provider_used"),
                    "model": data.get("model"),
                    "fallback_chain": data.get("fallback_chain", []),
                },
            )

        except Exception as e:
            return AdapterResult(
                success=False,
                error=f"OmniRoute request failed: {str(e)[:200]}",
            )

    def get_cost_estimate(self, payload: dict) -> float:
        """Estimate based on task type and budget."""
        task_type = payload.get("task_type", "reasoning")
        budget = payload.get("budget_usd", 1.0)

        # OmniRoute chooses the cheapest available provider within budget
        # Return the budget as the estimate (actual cost will be <= budget)
        return min(budget, {"image_gen": 0.05, "video": 2.0, "tts": 0.01, "reasoning": 0.10}.get(task_type, 0.5))

    def get_capability_score(self) -> float:
        """
        Meta-router: can do anything (reasoning, images, video, TTS).
        High score because it auto-switches to best available provider.
        """
        return 0.95  # Nearly universal capability
