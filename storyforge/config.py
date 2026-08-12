"""
storyforge/config.py — Environment configuration loader.
Handles .env loading with fail-fast on missing required keys.
"""

import os
from pathlib import Path
from typing import Dict


def load_env(path: Path | None = None) -> Dict[str, str]:
    """Parse a simple KEY=VALUE .env file (stdlib only, no python-dotenv)."""
    if path is None:
        path = Path(__file__).parent.parent / ".env"

    env: Dict[str, str] = {}
    if not path.exists():
        return env

    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        env[key.strip()] = value.strip().strip('"').strip("'")

    return env


def init_env() -> None:
    """Load .env file and populate os.environ. Call once at startup."""
    env_dict = load_env()
    for key, value in env_dict.items():
        os.environ[key] = value


def get_required(key: str, description: str = "") -> str:
    """Get an environment variable, fail fast if missing."""
    value = os.getenv(key, "").strip()
    if not value:
        desc_msg = f" ({description})" if description else ""
        raise RuntimeError(
            f"{key} not set in .env{desc_msg}\n"
            f"Add it to .env and restart, or run: "
            f"export {key}='your-value'"
        )
    return value
