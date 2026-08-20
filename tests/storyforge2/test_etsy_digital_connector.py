"""
tests/storyforge2/test_etsy_digital_connector.py — the connector that wires
lib/etsy_listing.py's real Etsy client into the book pipeline's publish()
for digital-download listings.

No live Etsy account exists yet (see CLAUDE.md, 2026-08-20) — every test
here either stays in dry_run (no network call is made at all, by
lib/etsy_listing.py's own design) or monkeypatches EtsyListingClient.create_listing
directly, never a real transport.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from lib.etsy_listing import EtsyListingResult
from storyforge2.publishing.connectors.etsy_digital import EtsyDigitalConnector

FULL_CREDENTIALS = {
    "ETSY_ACCESS_TOKEN": "token123",
    "ETSY_SHOP_ID": "SHOP1",
    "ETSY_API_KEY": "apikey123",
    "ETSY_TAXONOMY_ID": "5678",
}


@pytest.fixture
def manuscript(tmp_path) -> Path:
    path = tmp_path / "my_book.epub"
    path.write_bytes(b"epub bytes")
    return path


@pytest.fixture
def cover(tmp_path) -> Path:
    path = tmp_path / "cover.png"
    path.write_bytes(b"png bytes")
    return path


@pytest.fixture
def no_env(monkeypatch):
    """Clear all four env vars so tests are isolated from whatever the real
    shell/CI environment happens to have set."""
    for key in FULL_CREDENTIALS:
        monkeypatch.delenv(key, raising=False)


# --------------------------------------------------------------------------
# is_configured
# --------------------------------------------------------------------------

def test_is_configured_false_with_no_credentials(no_env):
    connector = EtsyDigitalConnector()
    assert connector.is_configured({}) is False
    assert connector.is_configured(None) is False


def test_is_configured_false_when_one_of_four_is_missing(no_env):
    connector = EtsyDigitalConnector()
    partial = dict(FULL_CREDENTIALS)
    del partial["ETSY_TAXONOMY_ID"]
    assert connector.is_configured(partial) is False


def test_is_configured_true_when_all_four_present(no_env):
    connector = EtsyDigitalConnector()
    assert connector.is_configured(dict(FULL_CREDENTIALS)) is True


def test_is_configured_reads_env_vars_as_fallback(no_env, monkeypatch):
    for key, value in FULL_CREDENTIALS.items():
        monkeypatch.setenv(key, value)
    connector = EtsyDigitalConnector()
    assert connector.is_configured(None) is True


# --------------------------------------------------------------------------
# publish() — guard clauses
# --------------------------------------------------------------------------

def test_publish_without_credentials_reports_missing_credentials(no_env, manuscript, cover):
    connector = EtsyDigitalConnector()
    result = connector.publish(manuscript, cover, {"title": "Book"}, credentials={})
    assert result.success is False
    assert result.error_code == "missing_credentials"
    assert "ETSY_" in result.message


def test_publish_missing_manuscript_reports_file_not_found(no_env, tmp_path, cover):
    connector = EtsyDigitalConnector()
    missing_manuscript = tmp_path / "does_not_exist.epub"
    result = connector.publish(
        missing_manuscript, cover, {"title": "Book"}, credentials=dict(FULL_CREDENTIALS))
    assert result.success is False
    assert result.error_code == "file_not_found"


def test_publish_missing_cover_is_not_fatal_and_sends_zero_images(no_env, tmp_path, manuscript):
    connector = EtsyDigitalConnector()
    missing_cover = tmp_path / "no_cover.png"
    result = connector.publish(
        manuscript, missing_cover, {"title": "Book"}, credentials=dict(FULL_CREDENTIALS), dry_run=True)
    assert result.success is True
    assert result.metadata["images_uploaded"] == 0


# --------------------------------------------------------------------------
# publish() — dry-run payload shape (verifies what would actually be sent)
# --------------------------------------------------------------------------

def test_dry_run_builds_a_real_download_listing_payload(no_env, manuscript, cover):
    connector = EtsyDigitalConnector()
    result = connector.publish(
        manuscript, cover,
        {"title": "The Digital Book", "slug": "the_digital_book"},
        credentials=dict(FULL_CREDENTIALS), dry_run=True,
    )

    assert result.success is True
    assert result.metadata["dry_run"] is True
    assert result.metadata["published"] is False
    assert result.metadata["listing_id"] is None

    payload = result.metadata["payloads"]["create_draft"]
    assert payload["type"] == "download"
    assert payload["title"] == "The Digital Book"
    assert payload["taxonomy_id"] == "5678"
    assert payload["who_made"] == "i_did"
    assert payload["when_made"] == "made_to_order"
    assert "shipping_profile_id" not in payload  # never required for download
    assert payload["price"] == "9.99"  # DEFAULT_PRICE_USD, no price in metadata


def test_dry_run_uses_metadata_price_and_description_when_given(no_env, manuscript, cover):
    connector = EtsyDigitalConnector()
    result = connector.publish(
        manuscript, cover,
        {"title": "Priced Book", "slug": "priced_book", "price": "14.99",
         "description": "A real description."},
        credentials=dict(FULL_CREDENTIALS), dry_run=True,
    )
    payload = result.metadata["payloads"]["create_draft"]
    assert payload["price"] == "14.99"
    assert payload["description"] == "A real description."


def test_dry_run_sends_no_network_request(no_env, manuscript, cover, monkeypatch):
    """lib/etsy_listing.py's dry_run short-circuits before any transport
    call — assert the connector doesn't work around that."""
    calls = []

    def fail_if_called(*args, **kwargs):
        calls.append((args, kwargs))
        raise AssertionError("transport must not be called in dry_run")

    monkeypatch.setattr("lib.etsy_listing._requests_transport", fail_if_called)

    connector = EtsyDigitalConnector()
    result = connector.publish(
        manuscript, cover, {"title": "Book", "slug": "book"},
        credentials=dict(FULL_CREDENTIALS), dry_run=True,
    )
    assert result.success is True
    assert calls == []


# --------------------------------------------------------------------------
# publish() — validation errors are caught, not raised
# --------------------------------------------------------------------------

def test_invalid_title_is_returned_as_a_failed_result_not_raised(no_env, manuscript, cover):
    connector = EtsyDigitalConnector()
    result = connector.publish(
        manuscript, cover,
        {"title": "x" * 200, "slug": "book"},  # over Etsy's 140-char limit
        credentials=dict(FULL_CREDENTIALS), dry_run=True,
    )
    assert result.success is False
    assert result.error_code == "validation_error"
    assert "140" in result.message


# --------------------------------------------------------------------------
# publish() — never activates, even when dry_run=False
# --------------------------------------------------------------------------

def test_publish_always_requests_draft_target_state_never_active(no_env, manuscript, cover, monkeypatch):
    captured = {}

    def fake_create_listing(self, product, target_state="draft", dry_run=True):
        captured["target_state"] = target_state
        captured["dry_run"] = dry_run
        return EtsyListingResult(sku=product.sku, listing_id="L999", dry_run=dry_run)

    monkeypatch.setattr(
        "lib.etsy_listing.EtsyListingClient.create_listing", fake_create_listing)

    connector = EtsyDigitalConnector()
    result = connector.publish(
        manuscript, cover, {"title": "Book", "slug": "book"},
        credentials=dict(FULL_CREDENTIALS), dry_run=False,
    )

    assert captured["target_state"] == "draft", (
        "the connector must never request activation, regardless of dry_run"
    )
    assert result.success is True
    assert result.metadata["listing_id"] == "L999"
    assert "NOT published" in result.message
