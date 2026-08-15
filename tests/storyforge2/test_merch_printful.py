"""
tests/storyforge2/test_merch_printful.py -- Printful connector.

No live account exists, so nothing here hits the network. The behaviours
tested are the ones that decide whether a *real* run is trustworthy:

- dry_run is the default, and runs the same preflight a live call would
- a 2xx that does not actually contain a product is NOT reported as published
- credentials are never echoed back in a message
"""

from types import SimpleNamespace

import pytest

from storyforge2.merch.artwork import ArtworkSource
from storyforge2.merch.connectors import (
    MerchPublishRequest, MerchVariant, PrintfulConnector,
)

GOOD_ART = ArtworkSource.from_url("https://cdn.example.com/rooted.png")
CREDS = {"PRINTFUL_API_KEY": "pf-secret-key"}


def _request(**overrides):
    base = dict(
        title="Rooted & Ready - Plant Lover T-Shirt",
        artwork=GOOD_ART,
        retail_price=24.99,
        variants=[
            MerchVariant(vendor_variant_id="4012", label="M"),
            MerchVariant(vendor_variant_id="4013", label="L"),
        ],
        sku="MP-DEMO01",
        product_type="tshirt",
    )
    base.update(overrides)
    return MerchPublishRequest(**base)


class _Response:
    """Stand-in for a requests.Response."""

    def __init__(self, status_code, body=None, text="", raise_on_json=False):
        self.status_code = status_code
        self._body = body
        self.text = text
        self._raise = raise_on_json

    def json(self):
        if self._raise:
            raise ValueError("not json")
        return self._body


@pytest.fixture
def connector():
    return PrintfulConnector()


# -- request validation ----------------------------------------------------

def test_valid_request_has_no_problems():
    assert _request().validate() == []


def test_empty_title_is_rejected():
    assert "title is empty" in _request(title="  ").validate()


def test_non_positive_price_is_rejected():
    assert any("positive" in p for p in _request(retail_price=0).validate())


def test_no_variants_is_rejected():
    assert any("no variants" in p for p in _request(variants=[]).validate())


def test_variant_without_vendor_id_is_rejected():
    """A missing catalogue id is how art lands on the wrong garment."""
    problems = _request(variants=[MerchVariant(vendor_variant_id="", label="M")]).validate()
    assert any("no vendor id" in p for p in problems)


def test_duplicate_variant_ids_are_rejected():
    problems = _request(variants=[
        MerchVariant(vendor_variant_id="4012", label="M"),
        MerchVariant(vendor_variant_id="4012", label="L"),
    ]).validate()
    assert any("duplicate" in p for p in problems)


def test_unsubmittable_artwork_is_rejected():
    art = ArtworkSource.from_url("data:image/svg+xml;utf8,%3Csvg%3E")
    problems = _request(artwork=art).validate()
    assert any(p.startswith("artwork:") for p in problems)


def test_all_problems_are_reported_at_once():
    """One round-trip per problem is how a fix takes five attempts."""
    problems = _request(title="", retail_price=-1, variants=[]).validate()
    assert len(problems) >= 3


# -- credentials -----------------------------------------------------------

def test_missing_credentials_block_the_publish(connector, monkeypatch):
    monkeypatch.delenv("PRINTFUL_API_KEY", raising=False)
    result = connector.publish(_request(), credentials={}, dry_run=True)
    assert result.success is False
    assert result.error_code == "missing_credentials"


def test_missing_credentials_names_the_variable_not_the_value(connector, monkeypatch):
    monkeypatch.delenv("PRINTFUL_API_KEY", raising=False)
    assert connector.missing_credentials({}) == ["PRINTFUL_API_KEY"]


def test_credentials_are_never_echoed_in_a_result(connector):
    result = connector.publish(_request(), credentials=CREDS, dry_run=True)
    assert "pf-secret-key" not in str(result.to_dict())


def test_env_var_satisfies_credentials(connector, monkeypatch):
    monkeypatch.setenv("PRINTFUL_API_KEY", "from-env")
    assert connector.is_configured() is True


def test_explicit_credentials_take_precedence(connector, monkeypatch):
    monkeypatch.delenv("PRINTFUL_API_KEY", raising=False)
    assert connector.is_configured(CREDS) is True


# -- payload ---------------------------------------------------------------

def test_payload_shape(connector):
    payload = connector.build_payload(_request())
    assert payload["sync_product"]["name"].startswith("Rooted")
    assert len(payload["sync_variants"]) == 2


def test_variant_ids_are_sent_as_integers(connector):
    """Printful's catalogue ids are numeric."""
    payload = connector.build_payload(_request())
    assert [v["variant_id"] for v in payload["sync_variants"]] == [4012, 4013]


def test_non_numeric_variant_id_is_passed_through_not_coerced(connector):
    """Better the vendor names the bad value than we silently invent one."""
    payload = connector.build_payload(
        _request(variants=[MerchVariant(vendor_variant_id="not-a-number")])
    )
    assert payload["sync_variants"][0]["variant_id"] == "not-a-number"


def test_prices_are_formatted_to_two_decimals(connector):
    payload = connector.build_payload(_request(retail_price=24.9))
    assert payload["sync_variants"][0]["retail_price"] == "24.90"


def test_per_variant_price_overrides_the_default(connector):
    payload = connector.build_payload(_request(variants=[
        MerchVariant(vendor_variant_id="4012", label="M"),
        MerchVariant(vendor_variant_id="4014", label="2XL", retail_price=27.99),
    ]))
    assert [v["retail_price"] for v in payload["sync_variants"]] == ["24.99", "27.99"]


def test_artwork_url_is_attached_to_every_variant(connector):
    payload = connector.build_payload(_request())
    for variant in payload["sync_variants"]:
        assert variant["files"][0]["url"] == GOOD_ART.raw


def test_overlong_title_is_truncated_not_rejected(connector):
    payload = connector.build_payload(_request(title="x" * 400))
    assert len(payload["sync_product"]["name"]) == 255


# -- dry run ---------------------------------------------------------------

def test_publish_defaults_to_dry_run(connector):
    """A real submission must be an explicit choice."""
    result = connector.publish(_request(), credentials=CREDS)
    assert result.success is True
    assert result.metadata["dry_run"] is True
    assert "[DRY_RUN]" in result.message


def test_dry_run_returns_the_real_payload(connector):
    result = connector.publish(_request(), credentials=CREDS, dry_run=True)
    assert result.metadata["payload"] == connector.build_payload(_request())


def test_dry_run_still_enforces_preflight(connector):
    """A dry run that skipped validation would give false confidence."""
    art = ArtworkSource.from_url("data:image/svg+xml;utf8,%3Csvg%3E")
    result = connector.publish(_request(artwork=art), credentials=CREDS, dry_run=True)
    assert result.success is False
    assert result.error_code == "invalid_request"


# -- response interpretation ----------------------------------------------

def _interpret(connector, response):
    return connector._interpret_create_response(response, _request())


def test_created_product_is_reported_with_its_id(connector):
    result = _interpret(connector, _Response(200, {"code": 200, "result": {"id": 987}}))
    assert result.success is True
    assert result.metadata["product_id"] == 987
    assert "987" in result.listing_url


def test_2xx_without_a_result_object_is_not_success(connector):
    """The failure this guards: recording a live listing that does not exist."""
    result = _interpret(connector, _Response(200, {"code": 200}))
    assert result.success is False
    assert result.error_code == "unexpected_response"


def test_2xx_result_without_an_id_is_not_success(connector):
    result = _interpret(connector, _Response(200, {"result": {"external_id": "x"}}))
    assert result.success is False
    assert result.error_code == "no_product_id"


def test_error_status_is_reported_with_the_vendor_message(connector):
    result = _interpret(connector, _Response(
        400, {"error": {"message": "Variant 4012 is unavailable"}}
    ))
    assert result.success is False
    assert result.error_code == "create_failed"
    assert "Variant 4012 is unavailable" in result.message


def test_non_json_response_is_reported_not_crashed(connector):
    result = _interpret(connector, _Response(502, text="<html>gateway</html>",
                                             raise_on_json=True))
    assert result.success is False
    assert result.error_code == "bad_response"


def test_publish_reports_a_network_error(connector, monkeypatch):
    import requests

    def _boom(*args, **kwargs):
        raise requests.RequestException("connection reset")

    monkeypatch.setattr(requests, "post", _boom)
    result = connector.publish(_request(), credentials=CREDS, dry_run=False)
    assert result.success is False
    assert result.error_code == "request_error"


def test_live_publish_sends_the_store_header_when_set(connector, monkeypatch):
    """Multi-store accounts need disambiguating; single-store must not send it."""
    import requests
    captured = {}

    def _capture(url, headers=None, json=None, timeout=None):
        captured["headers"] = headers
        return _Response(200, {"result": {"id": 1}})

    monkeypatch.setattr(requests, "post", _capture)
    connector.publish(_request(), credentials={**CREDS, "PRINTFUL_STORE_ID": "77"},
                      dry_run=False)
    assert captured["headers"]["X-PF-Store-Id"] == "77"

    captured.clear()
    connector.publish(_request(), credentials=CREDS, dry_run=False)
    assert "X-PF-Store-Id" not in captured["headers"]
