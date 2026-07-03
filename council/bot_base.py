"""
bot_base.py — Viral Engine Council
Base class for all council bots. Every bot inherits from CouncilBot.

To create a new bot:
  1. Create council/bots/bot_yourname.py
  2. class YourBot(CouncilBot): ...
  3. It auto-registers on next council run — no config needed.
"""

from __future__ import annotations
import json
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

BASE_DIR = Path(__file__).parent.parent
STATE_DIR = BASE_DIR / "council" / "state"
STATE_DIR.mkdir(parents=True, exist_ok=True)


@dataclass
class BotResult:
    bot_name: str
    ran_at: str = field(default_factory=lambda: datetime.now().isoformat())
    status: str = "ok"          # ok | warning | error | fixed
    issues_found: int = 0
    issues_fixed: int = 0
    messages: list[str] = field(default_factory=list)
    next_action: Optional[str] = None   # hint for what should run next

    def ok(self, msg: str):
        self.messages.append(f"✓ {msg}")

    def warn(self, msg: str):
        self.messages.append(f"⚠ {msg}")
        self.issues_found += 1
        if self.status == "ok":
            self.status = "warning"

    def error(self, msg: str):
        self.messages.append(f"✗ {msg}")
        self.issues_found += 1
        self.status = "error"

    def fixed(self, msg: str):
        self.messages.append(f"→ {msg}")
        self.issues_fixed += 1
        self.status = "fixed"

    def to_dict(self) -> dict:
        return {
            "bot_name": self.bot_name,
            "ran_at": self.ran_at,
            "status": self.status,
            "issues_found": self.issues_found,
            "issues_fixed": self.issues_fixed,
            "messages": self.messages,
            "next_action": self.next_action,
        }


class CouncilBot(ABC):
    """Base class for all council bots."""

    # Override in subclass
    name: str = "unnamed_bot"
    description: str = ""
    priority: int = 50       # lower = runs first (0-100)
    auto_fix: bool = True    # if False, only reports — never mutates

    def __init__(self, base_dir: Path = BASE_DIR, verbose: bool = True):
        self.base_dir = base_dir
        self.verbose = verbose
        self.result = BotResult(bot_name=self.name)

    @abstractmethod
    def run(self) -> BotResult:
        """Execute bot logic. Must return a BotResult."""
        ...

    def save_state(self, data: dict):
        """Persist bot-specific state to council/state/{name}.json"""
        path = STATE_DIR / f"{self.name}.json"
        existing = {}
        if path.exists():
            try:
                existing = json.loads(path.read_text())
            except Exception:
                pass
        existing.update(data)
        existing["last_updated"] = datetime.now().isoformat()
        path.write_text(json.dumps(existing, indent=2))

    def load_state(self) -> dict:
        path = STATE_DIR / f"{self.name}.json"
        if path.exists():
            try:
                return json.loads(path.read_text())
            except Exception:
                pass
        return {}

    def log(self, msg: str):
        if self.verbose:
            ts = datetime.now().strftime("%H:%M:%S")
            print(f"  [{ts}] [{self.name}] {msg}")
