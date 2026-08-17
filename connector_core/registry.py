"""
connector_core/registry.py -- honest capability vocabulary.

The rule this encodes, inherited from the book pipeline and applied unchanged
to merch: never label a platform as having an API it does not have. A status
is a claim about the outside world, so every entry carries the evidence for
its own claim in `notes`.

`CapabilityRegistry` is deliberately empty on construction. Platform lists are
product-specific -- books and POD channels are different sets, sometimes on
the same vendor -- so each pipeline builds its own.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

__all__ = ["ConnectorStatus", "PlatformCapability", "CapabilityRegistry"]


class ConnectorStatus(Enum):
    """What a platform actually offers.

    Never use DIRECT_API as a placeholder for "not implemented yet" -- that is
    the exact mislabelling this enum exists to prevent.
    """

    DIRECT_API = "direct_api"
    # A real, public API for listing submission, whose endpoint we can name.

    APPROVED_PARTNER_API = "approved_partner_api"
    # A real API gated behind business approval (TikTok Shop, Meta Shops).
    # The blocker is an approval step, not a missing API -- which is why this
    # is distinct from UNSUPPORTED.

    DRAFT_EXPORT = "draft_export"
    # No submission API exists; publishing happens through a web UI. We
    # generate an upload-ready package and a human finishes it.

    MANUAL_UPLOAD_PACKAGE = "manual_upload_package"
    # Same workflow as DRAFT_EXPORT. Kept separate only so a caller can tell
    # a major platform from a niche one; it does not change the process.

    UNSUPPORTED = "unsupported"
    # Genuinely out of scope, or so undocumented that integrating is
    # impractical. An honest label, never a TODO.


@dataclass
class PlatformCapability:
    """One platform's publishing capability.

    Never construct with DIRECT_API unless a real endpoint can be named.
    """

    platform_id: str
    name: str
    status: ConnectorStatus
    base_url: str = ""          # required when DIRECT_API
    auth_method: str = ""       # "oauth2", "api_key", "web_ui", ...
    notes: str = ""             # evidence for the status above
    supported_formats: list[str] = field(default_factory=lambda: ["epub", "pdf"])

    def requires_auth(self) -> bool:
        return self.status in (
            ConnectorStatus.DIRECT_API,
            ConnectorStatus.APPROVED_PARTNER_API,
        )

    def is_draft_export(self) -> bool:
        return self.status in (
            ConnectorStatus.DRAFT_EXPORT,
            ConnectorStatus.MANUAL_UPLOAD_PACKAGE,
        )


class CapabilityRegistry:
    """A set of platform capabilities. Empty until something adds to it."""

    def __init__(self, capabilities: Optional[list[PlatformCapability]] = None):
        self.platforms: dict[str, PlatformCapability] = {}
        for capability in capabilities or ():
            self.add(capability)

    def add(self, capability: PlatformCapability) -> None:
        self.platforms[capability.platform_id] = capability

    def get(self, platform_id: Optional[str]) -> Optional[PlatformCapability]:
        if platform_id is None:
            return None
        return self.platforms.get(platform_id)

    def all_platforms(self) -> list[PlatformCapability]:
        return sorted(self.platforms.values(), key=lambda p: p.name)

    def list_by_status(self, status: ConnectorStatus) -> list[PlatformCapability]:
        return [p for p in self.platforms.values() if p.status == status]

    def direct_api_platforms(self) -> list[PlatformCapability]:
        """Platforms publishable without a human or an approval step.

        Deliberately excludes APPROVED_PARTNER_API: callers use this list to
        decide what can go out now, and a gated API cannot.
        """
        return self.list_by_status(ConnectorStatus.DIRECT_API)

    def draft_export_platforms(self) -> list[PlatformCapability]:
        return [p for p in self.platforms.values() if p.is_draft_export()]
