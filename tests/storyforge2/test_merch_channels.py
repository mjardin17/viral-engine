"""
tests/storyforge2/test_merch_channels.py -- merch channel registry honesty.

Same guard as the book registry: a platform must not be labelled as having
an API it does not have. Redbubble and Spring are the ones at risk here --
CLAUDE.md policy is that neither has a usable public API and that no scraper
should be built against them.
"""

import pytest

from storyforge2.merch.channels import (
    CONNECTOR_TYPE_TO_STATUS, MERCH_CHANNELS, merch_registry,
    reconcile_export_channels,
)
from storyforge2.publishing.registry import ConnectorStatus, get_registry


@pytest.fixture
def registry():
    return merch_registry()


# -- registry honesty ------------------------------------------------------

def test_direct_api_channels_declare_an_endpoint(registry):
    for cap in registry.direct_api_platforms():
        assert cap.base_url.startswith("https://"), (
            f"{cap.platform_id} is DIRECT_API but declares no https endpoint"
        )
        assert cap.auth_method, f"{cap.platform_id} is DIRECT_API with no auth method"


def test_manual_channels_claim_no_api(registry):
    for cap in registry.draft_export_platforms():
        assert not cap.base_url, (
            f"{cap.platform_id} is manual-upload but declares base_url {cap.base_url!r}"
        )
        assert cap.auth_method in ("web_ui", "")


def test_no_api_platforms_stay_manual(registry):
    """Regression against a future relabel. CLAUDE.md policy is explicit that
    these have no usable public API and must not get a scraper."""
    for platform_id in ("redbubble", "spring", "amazon_merch"):
        cap = registry.get(platform_id)
        assert cap is not None, f"{platform_id} missing from registry"
        assert cap.is_draft_export() is True, f"{platform_id} wrongly claims an API"


def test_gated_platforms_are_not_listed_as_ready(registry):
    """direct_api_platforms() is what a caller uses to decide what can publish
    without an approval step -- a gated API must not appear there."""
    gated = registry.list_by_status(ConnectorStatus.APPROVED_PARTNER_API)
    assert gated
    direct_ids = {p.platform_id for p in registry.direct_api_platforms()}
    for cap in gated:
        assert cap.platform_id not in direct_ids


def test_reported_facts_are_labelled_as_reported(registry):
    """The POD endpoints came from a research pass, not a verified call.
    Dropping that caveat is how a reported fact becomes a fabricated one."""
    for platform_id in ("printful", "printify", "gooten"):
        cap = registry.get(platform_id)
        assert "[Reported, not Certain]" in cap.notes, (
            f"{platform_id} states an endpoint without its confidence label"
        )


def test_every_channel_has_evidence_notes(registry):
    for cap in registry.all_platforms():
        assert len(cap.notes.strip()) > 20, f"{cap.platform_id} has no stated reason"


def test_every_channel_declares_artwork_formats(registry):
    for cap in registry.all_platforms():
        assert cap.supported_formats


def test_channel_ids_are_unique(registry):
    ids = [c.platform_id for c in MERCH_CHANNELS]
    assert len(ids) == len(set(ids))


def test_merch_ids_do_not_collide_with_book_ids(registry):
    """The two registries describe different products on shared vendors and
    must stay mergeable -- etsy_merch vs etsy_digital, not both 'etsy'."""
    book_ids = set(get_registry().platforms)
    merch_ids = {c.platform_id for c in MERCH_CHANNELS}
    assert merch_ids & book_ids == set()


def test_merch_registry_does_not_mutate_the_book_singleton():
    before = dict(get_registry().platforms)
    merch_registry()
    assert get_registry().platforms == before


# -- reconciliation --------------------------------------------------------

def _channel(name, connector_type, connected=False):
    return {"id": f"ch_{name}", "name": name,
            "connector_type": connector_type, "connected": connected}


def test_agreeing_channels_produce_no_mismatch():
    channels = [
        _channel("Printful", "OFFICIAL_API"),
        _channel("Etsy", "OFFICIAL_API"),
        _channel("Shopify", "OFFICIAL_API"),
        _channel("Redbubble", "UPLOAD_PACKAGE"),
        _channel("Amazon Merch on Demand", "UPLOAD_PACKAGE"),
    ]
    assert reconcile_export_channels(channels) == []


def test_tiktok_shop_disagreement_is_surfaced():
    """The shipped export calls TikTok Shop UNSUPPORTED; a real gated Partner
    API exists, so the blocker is approval, not absence. Surfaced rather than
    silently overridden."""
    [mismatch] = reconcile_export_channels([_channel("TikTok Shop", "UNSUPPORTED")])
    assert mismatch.export_status is ConnectorStatus.UNSUPPORTED
    assert mismatch.registry_status is ConnectorStatus.APPROVED_PARTNER_API


def test_unmodelled_channel_is_surfaced_as_unverified():
    [mismatch] = reconcile_export_channels([_channel("Zazzle", "OFFICIAL_API")])
    assert mismatch.registry_status is None
    assert "not modelled" in mismatch.detail


def test_unrecognised_connector_type_is_surfaced():
    [mismatch] = reconcile_export_channels([_channel("Printful", "MAGIC_API")])
    assert mismatch.export_status is None
    assert "unrecognised" in mismatch.detail


def test_connected_flag_on_a_no_api_channel_is_surfaced():
    """Redbubble has no API, so 'connected' cannot mean an authenticated
    session -- believing it would route a publish into a dead end."""
    mismatches = reconcile_export_channels(
        [_channel("Redbubble", "UPLOAD_PACKAGE", connected=True)]
    )
    assert any("no submission API" in m.detail for m in mismatches)


def test_channel_name_matching_is_case_insensitive():
    assert reconcile_export_channels([_channel("printful", "OFFICIAL_API")]) == []


def test_teespring_maps_to_spring():
    assert reconcile_export_channels([_channel("Teespring", "UPLOAD_PACKAGE")]) == []


def test_connector_type_vocabulary_is_fully_mapped():
    """Every type the export can emit must have a status, or reconciliation
    reports a false mismatch."""
    assert set(CONNECTOR_TYPE_TO_STATUS) == {
        "OFFICIAL_API", "UPLOAD_PACKAGE", "UNSUPPORTED",
    }
    for status in CONNECTOR_TYPE_TO_STATUS.values():
        assert isinstance(status, ConnectorStatus)
