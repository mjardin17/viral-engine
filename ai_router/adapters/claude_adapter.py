"""
claude_adapter.py — PLANNING / WRITING / STORYBOARDING / PROMPT_CREATION.

Stub adapter: no API call wired yet. is_connected() checks ANTHROPIC_API_KEY;
when the key lands, execute() gets a real Messages API call. Until then it
reports unavailable so the router falls to chatgpt/gemini cleanly.
"""

from __future__ import annotations

from .base_adapter import AdapterBase, AdapterResult, env


class ClaudeAdapter(AdapterBase):
    """Claude text model — highest planning/writing quality when keyed."""

    name = "claude"
    capability_score = 0.95
    default_cost_usd = 0.01

    def is_connected(self) -> bool:
        return bool(env("ANTHROPIC_API_KEY"))

    def execute(self, payload: dict) -> AdapterResult:
        if not self.is_connected():
            return AdapterResult(success=False, error="ANTHROPIC_API_KEY not set")
        # [Certain] Intentional stub — real Messages API call to be wired when
        # Josh adds the key. Fail loudly rather than fake output (truth rule).
        return AdapterResult(
            success=False,
            error="claude adapter is a stub — API call not wired yet "
                  "(key present; implement Messages API call to activate)",
        )
