"""
ai_router/adapters/base_adapter.py — shared adapter contract + .env loader.

Every model adapter implements:
    is_connected() -> bool
    execute(payload: dict) -> AdapterResult
    get_cost_estimate(payload: dict) -> float
    get_capability_score() -> float   (0.0-1.0)

Adapters NEVER raise from execute() — they return AdapterResult(success=False).
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

BASE_DIR: Path = Path(__file__).resolve().parents[2]  # repo root

_ENV_LOADED = False


def load_env() -> None:
    """Load repo-root .env into os.environ (setdefault — never overrides)."""
    global _ENV_LOADED
    if _ENV_LOADED:
        return
    env_path = BASE_DIR / ".env"
    try:
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            value = value.split("#")[0].strip().strip('"').strip("'")
            if key.strip() and value:
                os.environ.setdefault(key.strip(), value)
    except OSError:
        pass
    _ENV_LOADED = True


def env(key: str) -> str:
    """Return an env var (post .env load), empty string if unset."""
    load_env()
    return os.environ.get(key, "").strip()


@dataclass
class AdapterResult:
    """Outcome of one adapter execution."""

    success: bool
    output: Any = None                 # path str, text, bytes, dict — task-dependent
    error: str | None = None
    cost_usd: float = 0.0
    latency_ms: int = 0
    meta: dict = field(default_factory=dict)


class AdapterBase:
    """Base class for all model adapters (subclass and override)."""

    name: str = "unnamed"
    capability_score: float = 0.5
    default_cost_usd: float = 0.0

    def is_connected(self) -> bool:
        """True if this adapter can be used right now (key set / binary found)."""
        return False

    def execute(self, payload: dict) -> AdapterResult:  # pragma: no cover - override
        """Run the task. Must never raise; return AdapterResult(success=False)."""
        return AdapterResult(success=False, error=f"{self.name}: execute() not implemented")

    def get_cost_estimate(self, payload: dict) -> float:
        """Estimated USD cost of executing this payload."""
        return self.default_cost_usd

    def get_capability_score(self) -> float:
        """Static quality score 0.0-1.0 for this adapter's specialty."""
        return self.capability_score

    def _timed(self, fn, *args, **kwargs) -> tuple[Any, int]:
        """Run fn, return (result, elapsed_ms)."""
        start = time.monotonic()
        out = fn(*args, **kwargs)
        return out, int((time.monotonic() - start) * 1000)
