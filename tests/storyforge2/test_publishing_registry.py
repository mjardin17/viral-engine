"""
tests/storyforge2/test_publishing_registry.py — platform registry honesty.

These tests exist to stop a platform from being labelled as having an API it
does not have. That mislabelling already happened once (KDP was marked
DIRECT_API with a fabricated Selling Partner API base_url while its connector
was actually Playwright browser automation).
"""

import pytest

from storyforge2.publishing.registry import (
    ConnectorStatus, PlatformCapability, PlatformRegistry, get_registry,
)


@pytest.fixture
def registry():
    return PlatformRegistry()


def test_requires_auth_only_for_api_statuses():
    def cap(status):
        return PlatformCapability(platform_id="x", name="X", status=status)

    assert cap(ConnectorStatus.DIRECT_API).requires_auth() is True
    assert cap(ConnectorStatus.APPROVED_PARTNER_API).requires_auth() is True
    assert cap(ConnectorStatus.DRAFT_EXPORT).requires_auth() is False
    assert cap(ConnectorStatus.MANUAL_UPLOAD_PACKAGE).requires_auth() is False


def test_is_draft_export_covers_both_manual_statuses():
    def cap(status):
        return PlatformCapability(platform_id="x", name="X", status=status)

    assert cap(ConnectorStatus.DRAFT_EXPORT).is_draft_export() is True
    assert cap(ConnectorStatus.MANUAL_UPLOAD_PACKAGE).is_draft_export() is True
    assert cap(ConnectorStatus.DIRECT_API).is_draft_export() is False


def test_registry_covers_the_mission_platform_set(registry):
    assert len(registry.all_platforms()) >= 13


def test_platform_ids_are_unique(registry):
    ids = [p.platform_id for p in registry.all_platforms()]
    assert len(ids) == len(set(ids))


def test_get_missing_platform_returns_none(registry):
    assert registry.get("not_a_platform") is None


def test_no_platform_is_silently_unsupported(registry):
    """UNSUPPORTED is allowed, but must carry a reason rather than being a TODO."""
    for cap in registry.list_by_status(ConnectorStatus.UNSUPPORTED):
        assert cap.notes.strip(), f"{cap.platform_id} is UNSUPPORTED with no stated reason"


def test_direct_api_platforms_declare_an_endpoint(registry):
    """DIRECT_API means a real API exists. If we cannot name its endpoint,
    the label is a guess and must not be DIRECT_API."""
    for cap in registry.direct_api_platforms():
        assert cap.base_url.startswith("https://"), (
            f"{cap.platform_id} is DIRECT_API but declares no https endpoint"
        )
        assert cap.auth_method, f"{cap.platform_id} is DIRECT_API with no auth method"


def test_draft_export_platforms_claim_no_api(registry):
    """A manual-upload platform must not carry API metadata — that is exactly
    how a fabricated capability gets introduced."""
    for cap in registry.draft_export_platforms():
        assert cap.auth_method in ("web_ui", ""), (
            f"{cap.platform_id} is manual-upload but claims auth '{cap.auth_method}'"
        )
        assert not cap.base_url, (
            f"{cap.platform_id} is manual-upload but declares API base_url '{cap.base_url}'"
        )


def test_kdp_is_not_labelled_direct_api(registry):
    """Regression: KDP has no public submission API (excluded from Amazon's
    Selling Partner API). Its connector drives the web UI via Playwright."""
    kdp = registry.get("kdp")
    assert kdp is not None
    assert kdp.status != ConnectorStatus.DIRECT_API
    assert kdp.is_draft_export() is True
    assert not kdp.base_url


def test_known_no_api_platforms_are_draft_export(registry):
    """Settled by the CLAUDE.md audit — none of these expose a public
    submission API. Guards against a future relabel."""
    for platform_id in ("apple_books", "google_play_books", "kobo_writing_life",
                        "bn_press", "ingramspark"):
        cap = registry.get(platform_id)
        assert cap is not None, f"{platform_id} missing from registry"
        assert cap.is_draft_export() is True, f"{platform_id} wrongly claims an API"


def test_approved_partner_platforms_are_not_treated_as_ready(registry):
    """Gated APIs must not appear in direct_api_platforms() — callers use that
    list to decide what can publish without a business-approval step."""
    gated = registry.list_by_status(ConnectorStatus.APPROVED_PARTNER_API)
    assert gated, "expected at least one approval-gated platform"
    direct_ids = {p.platform_id for p in registry.direct_api_platforms()}
    for cap in gated:
        assert cap.platform_id not in direct_ids


def test_every_platform_declares_supported_formats(registry):
    for cap in registry.all_platforms():
        assert cap.supported_formats, f"{cap.platform_id} declares no supported formats"


def test_every_platform_has_evidence_notes(registry):
    """Each status must be justified in-line, so the next person can check it
    rather than trusting the label."""
    for cap in registry.all_platforms():
        assert len(cap.notes.strip()) > 20, f"{cap.platform_id} has no evidence for its status"


def test_get_registry_is_a_singleton():
    assert get_registry() is get_registry()
