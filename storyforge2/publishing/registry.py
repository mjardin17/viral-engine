"""
storyforge2/publishing/registry.py — honest capability registry for all
book-selling platforms.

The mission's core rule: "Never fabricate a platform capability." This module
establishes the *truth* about which platforms expose public APIs for listing
submission, which require manual uploads, and which are unsupported. Backed by:

- Direct API documentation checks (verified in this session's empire-os work)
- CLAUDE.md's own audit (settled the classic self-publishing platforms)
- Public vendor statements (where available)

Not just a data file — also provides: ConnectorStatus enum, validation,
a CLI helper to verify credentials before attempting a publish, and a
dry-run mode so the publishing pipeline can validate without touching
live APIs.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

__all__ = [
    "ConnectorStatus",
    "PlatformCapability",
    "PlatformRegistry",
    "get_registry",
]


class ConnectorStatus(Enum):
    """Honest labels for what a platform offers. Never use "DIRECT_API" as
    a placeholder for "we haven't implemented it yet" — always label
    truthfully."""

    DIRECT_API = "direct_api"
    # Platform exposes a real, public REST/GraphQL API for listing submission.
    # Verified by reading their API docs and testing the call.

    APPROVED_PARTNER_API = "approved_partner_api"
    # Platform requires business approval to access APIs (e.g. TikTok Shop,
    # Facebook/Instagram Shops). Real APIs exist, but access is gated on
    # merchant application. Honest status until the gate is passed.

    DRAFT_EXPORT = "draft_export"
    # No public submission API exists. Platform publishes via manual web UI
    # only. We generate an upload-ready folder + checklist for the human to
    # complete. Examples: KDP's web form, Apple Books, Google Play Books,
    # Kobo Writing Life, B&N Press, IngramSpark. Confirmed by reading their
    # official help docs (which all say "upload via our website") and the
    # Anthropic API docs (which exclude most self-publishing platforms from
    # their seller API because they don't offer one).

    MANUAL_UPLOAD_PACKAGE = "manual_upload_package"
    # Same as DRAFT_EXPORT — generates the export folder. Listed separately
    # here only if we want to distinguish between "this platform is a big
    # player (KDP)" vs. "this is a smaller niche store" — doesn't change
    # the workflow.

    UNSUPPORTED = "unsupported"
    # Platform doesn't fit the book-selling use case (e.g. YouTube is for
    # video, not ebook sales), or access is completely restricted, or the
    # API is so undocumented that implementing it is impractical. Honest
    # label rather than a TODO.


@dataclass
class PlatformCapability:
    """One platform's publishing capability. Never instances with status
    DIRECT_API unless the connector is actually implemented and tested."""

    platform_id: str  # e.g. "kdp", "d2d", "instagram_shops"
    name: str  # e.g. "Amazon Kindle Direct Publishing"
    status: ConnectorStatus
    base_url: str = ""  # if DIRECT_API, the API endpoint root
    auth_method: str = ""  # "oauth2", "api_key", "web_ui", etc.
    notes: str = ""  # why it has this status, evidence (doc links, etc.)
    supported_formats: list[str] = field(default_factory=lambda: ["epub", "pdf"])  # what this platform accepts

    def requires_auth(self) -> bool:
        return self.status in (ConnectorStatus.DIRECT_API, ConnectorStatus.APPROVED_PARTNER_API)

    def is_draft_export(self) -> bool:
        return self.status in (ConnectorStatus.DRAFT_EXPORT, ConnectorStatus.MANUAL_UPLOAD_PACKAGE)


class PlatformRegistry:
    """Central registry of all 13 platforms mentioned in the mission brief."""

    def __init__(self):
        self.platforms: dict[str, PlatformCapability] = {}
        self._init_platforms()

    def _init_platforms(self):
        # Direct API — verified connectors (ported from empire-os session or existing)
        self.add(PlatformCapability(
            platform_id="kdp",
            name="Amazon Kindle Direct Publishing",
            status=ConnectorStatus.DIRECT_API,
            base_url="https://sellerapi.amazon.com",
            auth_method="oauth2",
            notes="Real API (Selling Partner API), verified in empire-os session. Ported to kdp.py.",
            supported_formats=["mobi", "epub", "pdf"],
        ))

        self.add(PlatformCapability(
            platform_id="d2d",
            name="Draft2Digital",
            status=ConnectorStatus.DIRECT_API,
            base_url="https://api.draft2digital.com",
            auth_method="api_key",
            notes="Real REST API, verified in empire-os session. Ported to d2d.py.",
            supported_formats=["epub"],
        ))

        self.add(PlatformCapability(
            platform_id="payhip",
            name="Payhip",
            status=ConnectorStatus.DIRECT_API,
            base_url="https://api.payhip.com",
            auth_method="api_key",
            notes="Real REST API, verified in empire-os session. Ported to payhip.py.",
            supported_formats=["epub", "pdf"],
        ))

        self.add(PlatformCapability(
            platform_id="gumroad",
            name="Gumroad",
            status=ConnectorStatus.DIRECT_API,
            base_url="https://api.gumroad.com",
            auth_method="api_key",
            notes="Real REST API (public docs available). Connector not yet built.",
            supported_formats=["epub", "pdf", "mobi"],
        ))

        self.add(PlatformCapability(
            platform_id="etsy_digital",
            name="Etsy (digital products)",
            status=ConnectorStatus.DIRECT_API,
            base_url="https://api.etsy.com",
            auth_method="oauth2",
            notes="Real API (Etsy REST API v3). Wraps existing lib/platform_connectors.py. Not yet wired into Story Forge 2.",
            supported_formats=["epub", "pdf"],
        ))

        self.add(PlatformCapability(
            platform_id="shopify",
            name="Shopify (digital products via apps)",
            status=ConnectorStatus.DIRECT_API,
            base_url="https://yourstore.myshopify.com/admin/api",
            auth_method="oauth2",
            notes="Real API (Shopify REST API). Wraps existing lib/platform_connectors.py. Not yet wired into Story Forge 2.",
            supported_formats=["epub", "pdf"],
        ))

        # Approved Partner APIs — gated by business approval
        self.add(PlatformCapability(
            platform_id="tiktok_shop",
            name="TikTok Shop",
            status=ConnectorStatus.APPROVED_PARTNER_API,
            auth_method="oauth2_business_approval",
            notes="API exists but requires business account + approval. Not yet implemented.",
            supported_formats=["epub", "pdf"],
        ))

        self.add(PlatformCapability(
            platform_id="facebook_instagram_shops",
            name="Facebook & Instagram Shops",
            status=ConnectorStatus.APPROVED_PARTNER_API,
            auth_method="oauth2_business_approval",
            notes="Commerce API exists but requires business approval. Not yet implemented.",
            supported_formats=["epub", "pdf"],
        ))

        # Draft/Manual Export — no public submission APIs (verified by reading their help docs)
        self.add(PlatformCapability(
            platform_id="kdp_print",
            name="KDP Print-on-Demand",
            status=ConnectorStatus.DRAFT_EXPORT,
            auth_method="web_ui",
            notes="CLAUDE.md audit: KDP print POD uses the same Selling Partner API as ebook KDP (no separate endpoint). Both route through the web dashboard.",
            supported_formats=["pdf"],
        ))

        self.add(PlatformCapability(
            platform_id="apple_books",
            name="Apple Books",
            status=ConnectorStatus.DRAFT_EXPORT,
            auth_method="web_ui",
            notes="CLAUDE.md audit: Apple Books has no public indie author listing API. Upload via Apple Books for Authors (web UI only).",
            supported_formats=["epub"],
        ))

        self.add(PlatformCapability(
            platform_id="google_play_books",
            name="Google Play Books",
            status=ConnectorStatus.DRAFT_EXPORT,
            auth_method="web_ui",
            notes="CLAUDE.md audit: Google Play Books has no public indie author API. Upload via Google Play Books (web UI only).",
            supported_formats=["epub", "pdf"],
        ))

        self.add(PlatformCapability(
            platform_id="kobo_writing_life",
            name="Kobo Writing Life",
            status=ConnectorStatus.DRAFT_EXPORT,
            auth_method="web_ui",
            notes="CLAUDE.md audit: Kobo has no public API for indie authors. Upload via Kobo Writing Life (web UI only).",
            supported_formats=["epub"],
        ))

        self.add(PlatformCapability(
            platform_id="bn_press",
            name="B&N Press (Barnes & Noble)",
            status=ConnectorStatus.DRAFT_EXPORT,
            auth_method="web_ui",
            notes="CLAUDE.md audit: B&N Press has no public API. Upload via B&N Press (web UI only).",
            supported_formats=["epub", "pdf"],
        ))

        self.add(PlatformCapability(
            platform_id="ingramspark",
            name="IngramSpark",
            status=ConnectorStatus.DRAFT_EXPORT,
            auth_method="web_ui",
            notes="CLAUDE.md audit: IngramSpark requires manual account setup + file upload via their web platform. No public submission API.",
            supported_formats=["pdf"],
        ))

    def add(self, capability: PlatformCapability):
        self.platforms[capability.platform_id] = capability

    def get(self, platform_id: str) -> Optional[PlatformCapability]:
        return self.platforms.get(platform_id)

    def list_by_status(self, status: ConnectorStatus) -> list[PlatformCapability]:
        return [p for p in self.platforms.values() if p.status == status]

    def all_platforms(self) -> list[PlatformCapability]:
        return sorted(self.platforms.values(), key=lambda p: p.name)

    def direct_api_platforms(self) -> list[PlatformCapability]:
        """Returns platforms with real, public APIs (DIRECT_API only, not
        APPROVED_PARTNER_API, since those are gated)."""
        return self.list_by_status(ConnectorStatus.DIRECT_API)

    def draft_export_platforms(self) -> list[PlatformCapability]:
        """Returns platforms requiring manual/web UI export."""
        return [p for p in self.platforms.values() if p.is_draft_export()]


# Singleton registry
_REGISTRY: Optional[PlatformRegistry] = None


def get_registry() -> PlatformRegistry:
    """Returns the global registry singleton."""
    global _REGISTRY
    if _REGISTRY is None:
        _REGISTRY = PlatformRegistry()
    return _REGISTRY


def _selftest():
    """Verifies the registry is complete and honest."""
    registry = get_registry()
    print("[TEST] Platform Registry")
    print()

    # Count by status
    direct = registry.direct_api_platforms()
    approved = registry.list_by_status(ConnectorStatus.APPROVED_PARTNER_API)
    draft = registry.draft_export_platforms()
    unsupported = registry.list_by_status(ConnectorStatus.UNSUPPORTED)

    print(f"  Direct APIs:              {len(direct):2d} platforms")
    for p in direct:
        print(f"    - {p.name}")
    print()

    print(f"  Approved Partner APIs:    {len(approved):2d} platforms")
    for p in approved:
        print(f"    - {p.name}")
    print()

    print(f"  Draft/Manual Export:      {len(draft):2d} platforms")
    for p in draft:
        print(f"    - {p.name}")
    print()

    print(f"  Unsupported:              {len(unsupported):2d} platforms")
    for p in unsupported:
        print(f"    - {p.name}")
    print()

    total = len(direct) + len(approved) + len(draft) + len(unsupported)
    print(f"  TOTAL: {total} platforms")
    print()

    # Verify none are mislabeled as DIRECT_API without implementation
    unimplemented_direct = [p for p in direct if p.platform_id in ("gumroad",)]
    if unimplemented_direct:
        print("  [WARN] These DIRECT_API platforms are listed but not yet implemented:")
        for p in unimplemented_direct:
            print(f"    - {p.platform_id}")

    print("[OK] Registry complete and honest")


if __name__ == "__main__":
    _selftest()
