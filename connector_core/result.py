"""
connector_core/result.py -- one result shape for every publish attempt.

Books and merch record outcomes into the same ledger, so they report them in
the same shape. A connector that invents its own result type forces every
caller to special-case it.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

__all__ = ["ConnectorResult"]


@dataclass
class ConnectorResult:
    """The outcome of one publish attempt against one platform.

    `success` must mean the platform confirmed the thing exists. A 2xx that
    does not carry an id is not success -- recording it as such creates a
    listing in the ledger that does not exist on the platform.
    """

    success: bool
    message: str
    platform_id: str
    listing_url: Optional[str] = None
    error_code: Optional[str] = None
    metadata: Optional[dict[str, Any]] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "success": self.success,
            "message": self.message,
            "platform_id": self.platform_id,
            "listing_url": self.listing_url,
            "error_code": self.error_code,
            "metadata": self.metadata or {},
        }
