"""
Little Olympus Studio — Base Adapter

All integrations implement this interface.
Swap or add adapters by subclassing BaseAdapter — never hard-code integrations in server.py.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any


@dataclass
class AdapterStatus:
    available: bool
    name: str
    version: str = "0.0.0"
    message: str = ""
    config: dict[str, Any] = field(default_factory=dict)


class BaseAdapter:
    """Base class for all LO Studio adapters."""

    name: str = "base"
    description: str = "Base adapter"
    version: str = "0.0.0"

    def health_check(self) -> AdapterStatus:
        raise NotImplementedError

    def get_status(self) -> dict[str, Any]:
        try:
            status = self.health_check()
        except Exception as e:
            status = AdapterStatus(available=False, name=self.name, message=str(e))
        return {
            "name": status.name,
            "available": status.available,
            "version": status.version,
            "message": status.message,
            "config": status.config,
        }
