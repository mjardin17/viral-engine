"""
claude_adapter.py — PLANNING / WRITING / STORYBOARDING / PROMPT_CREATION.

Real Anthropic Messages API call via stdlib urllib (same no-new-dependency
convention as openai_adapter.py). Uses ANTHROPIC_API_KEY.

Fallback: When Claude is unavailable or quota-limited, automatically falls back
to Ollama (qwen2.5-coder:7b) running on localhost:11434. Fallback is transparent
to callers — they get an AdapterResult with provider info in meta.

Payload keys: {"prompt": str, "task_type": str, "system": optional str,
"model": optional str override, "max_tokens": optional int}
→ output = generated text.
"""

from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request

from .base_adapter import AdapterBase, AdapterResult, env

logger = logging.getLogger(__name__)


API_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_VERSION = "2023-06-01"
DEFAULT_MODEL = "claude-sonnet-5"
DEFAULT_MAX_TOKENS = 8192
TEXT_TASKS = {"PLANNING", "WRITING", "STORYBOARDING", "PROMPT_CREATION"}

# Ollama fallback config
OLLAMA_API_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "qwen2.5-coder:7b"
OLLAMA_TIMEOUT_SEC = 300

# Anthropic first-party pricing, USD per token (cached 2026-06-24 from the
# claude-api skill). Used only to report real spend on AdapterResult.cost_usd
# — never to gate whether a call is made.
_PRICE_PER_TOKEN = {
    "claude-opus-5": (5.00 / 1_000_000, 25.00 / 1_000_000),
    "claude-sonnet-5": (2.00 / 1_000_000, 10.00 / 1_000_000),
    "claude-haiku-4-5": (1.00 / 1_000_000, 5.00 / 1_000_000),
}


class ClaudeAdapter(AdapterBase):
    """Claude text model — highest planning/writing quality when keyed."""

    name = "claude"
    capability_score = 0.95
    default_cost_usd = 0.01

    def is_connected(self) -> bool:
        return bool(env("ANTHROPIC_API_KEY"))

    @staticmethod
    def _call(req: urllib.request.Request) -> dict:
        with urllib.request.urlopen(req, timeout=180) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def execute(self, payload: dict) -> AdapterResult:
        task = payload.get("task_type", "")
        if task and task not in TEXT_TASKS:
            return AdapterResult(success=False, error=f"claude adapter has no handler for task '{task}'")

        prompt = str(payload.get("prompt", "")).strip()
        if not prompt:
            return AdapterResult(success=False, error="payload missing 'prompt'")

        system = str(payload.get("system") or "")
        max_tokens = int(payload.get("max_tokens") or DEFAULT_MAX_TOKENS)

        # Try Claude first if key is set
        if self.is_connected():
            result = self._try_claude(prompt, system, max_tokens, payload)
            if result.success:
                return result
            claude_error = result.error
            logger.warning(f"Claude failed ({claude_error}), attempting Ollama fallback...")
        else:
            claude_error = "ANTHROPIC_API_KEY not set"
            logger.info(f"Claude unavailable ({claude_error}), attempting Ollama fallback...")

        # Fall back to Ollama
        result = self._try_ollama(prompt, system, max_tokens)
        if result.success:
            logger.info(f"Ollama fallback succeeded (model={OLLAMA_MODEL})")
            return result

        # Both failed
        ollama_error = result.error
        return AdapterResult(
            success=False,
            error=f"Both Claude ({claude_error}) and Ollama ({ollama_error}) failed",
        )

    def _try_claude(self, prompt: str, system: str, max_tokens: int, payload: dict) -> AdapterResult:
        """Attempt to generate text via Anthropic Claude API."""
        model = str(payload.get("model") or env("BOOK_FACTORY_CLAUDE_MODEL") or DEFAULT_MODEL)

        body = {
            "model": model,
            "max_tokens": max_tokens,
            "messages": [{"role": "user", "content": prompt}],
        }
        if system:
            body["system"] = system

        req = urllib.request.Request(
            API_URL, data=json.dumps(body).encode("utf-8"),
            headers={
                "x-api-key": env("ANTHROPIC_API_KEY"),
                "anthropic-version": ANTHROPIC_VERSION,
                "Content-Type": "application/json",
            },
            method="POST",
        )

        try:
            out, ms = self._timed(self._call, req)
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", errors="replace")[:500]
            return AdapterResult(success=False, error=f"HTTP {e.code}: {detail}")
        except Exception as e:
            return AdapterResult(success=False, error=str(e))

        if out.get("stop_reason") == "refusal":
            return AdapterResult(success=False, error="request refused", latency_ms=ms)

        text = "".join(
            block.get("text", "") for block in out.get("content", [])
            if block.get("type") == "text"
        )
        if not text:
            return AdapterResult(success=False, error="no text returned", latency_ms=ms)

        usage = out.get("usage", {})
        in_price, out_price = _PRICE_PER_TOKEN.get(model, _PRICE_PER_TOKEN[DEFAULT_MODEL])
        cost = usage.get("input_tokens", 0) * in_price + usage.get("output_tokens", 0) * out_price

        return AdapterResult(
            success=True, output=text, cost_usd=cost, latency_ms=ms,
            meta={"model": model, "provider": "claude", "usage": usage},
        )

    def _try_ollama(self, prompt: str, system: str, max_tokens: int) -> AdapterResult:
        """Attempt to generate text via local Ollama server."""
        full_prompt = f"{system}\n\n{prompt}" if system else prompt

        payload = {
            "model": OLLAMA_MODEL,
            "prompt": full_prompt,
            "stream": False,
        }

        try:
            import urllib.request as ur
            req = ur.Request(
                OLLAMA_API_URL,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            out, ms = self._timed(self._call, req)
        except Exception as e:
            return AdapterResult(success=False, error=f"Ollama error: {str(e)}")

        text = out.get("response", "").strip()
        if not text:
            return AdapterResult(success=False, error="Ollama returned empty response")

        return AdapterResult(
            success=True, output=text, cost_usd=0.0, latency_ms=ms,
            meta={"model": OLLAMA_MODEL, "provider": "ollama"},
        )
