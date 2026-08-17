"""
tests/merch/test_printify.py -- Printify connector.

Nothing here hits the network. The behaviours worth pinning are the ones that
differ from Printful and each have a money or wrong-product failure mode:

- price is integer minor units (2499), not "24.99"
- blueprint_id / print_provider_id are required, never guessed
- artwork uploads first and the product references an image id
- a local raster file IS submittable here (base64), unlike Printful
"""

from decimal import Decimal

import pytest

from merch.artwork import ArtworkSource
from merch.connectors import (
    MerchPublishRequest, MerchVariant, PrintifyConnector, to_minor_units,
)
from merch.connectors.printify import (
    MAX_UPLOAD_BYTES, PrintifyArtworkError, PrintifyPriceError,
)

GOOD_ART = ArtworkSource.from_url("https://cdn.example.com/rooted.png")
CREDS = {"PRINTIFY_API_KEY": "pfy-secret", "PRINTIFY_SHOP_ID": "9001"}
BLUEPRINT = {"blueprint_id": 384, "print_provider_id": 1}


def _request(**overrides):
    base = dict(
        title="Rooted & Ready - Plant Lover T-Shirt",
        artwork=GOOD_ART,
        retail_price=24.99,
        variants=[
            MerchVariant(vendor_variant_id="45740", label="M"),
            MerchVariant(vendor_variant_id="45741", label="L"),
        ],
        description="An original badge-style tee.",
        sku="MP-DEMO01",
    )
    base.update(overrides)
    return MerchPublishRequest(**base)


class _Response:
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
    return PrintifyConnector()


# -- money -----------------------------------------------------------------

@pytest.mark.parametrize("price,expected", [
    (24.99, 2499),
    (25, 2500),
    (0.01, 1),
    ("19.95", 1995),
    (Decimal("34.50"), 3450),
    (1000, 100000),
])
def test_prices_convert_to_minor_units(price, expected):
    assert to_minor_units(price) == expected


@pytest.mark.parametrize("price,truncated,correct", [
    (1.15, 114, 115),
    (0.29, 28, 29),
    (0.57, 56, 57),
    (1.13, 112, 113),
])
def test_float_truncation_would_underprice_but_decimal_does_not(price, truncated, correct):
    """A cent lost on every sale of an affected price. 24.99 is NOT affected,
    which is why spot-checking one value proves nothing."""
    assert int(price * 100) == truncated
    assert to_minor_units(price) == correct


def test_sub_cent_price_raises_rather_than_rounding():
    """Silently turning 24.999 into 2500 hides a mistake upstream."""
    with pytest.raises(PrintifyPriceError, match="sub-cent"):
        to_minor_units(24.999)


def test_zero_and_negative_prices_are_rejected():
    for bad in (0, -1, "-5.00"):
        with pytest.raises(PrintifyPriceError, match="positive"):
            to_minor_units(bad)


def test_non_numeric_price_is_rejected():
    with pytest.raises(PrintifyPriceError, match="not a number"):
        to_minor_units("free")


def test_publish_reports_a_bad_price_rather_than_sending_it(connector):
    result = connector.publish(
        _request(retail_price=24.999), credentials=CREDS, dry_run=True, **BLUEPRINT,
    )
    assert result.success is False
    assert result.error_code == "invalid_price"


# -- catalogue ids ---------------------------------------------------------

def test_missing_blueprint_id_blocks_the_publish(connector):
    """A guessed blueprint prints the design on a garment nobody chose."""
    result = connector.publish(_request(), credentials=CREDS, dry_run=True,
                               print_provider_id=1)
    assert result.success is False
    assert result.error_code == "missing_catalog_ids"


def test_missing_print_provider_blocks_the_publish(connector):
    result = connector.publish(_request(), credentials=CREDS, dry_run=True,
                               blueprint_id=384)
    assert result.success is False
    assert result.error_code == "missing_catalog_ids"


# -- credentials -----------------------------------------------------------

def test_shop_id_is_required_not_optional(connector, monkeypatch):
    """Printify has no default shop, so an account with several is ambiguous."""
    monkeypatch.delenv("PRINTIFY_SHOP_ID", raising=False)
    missing = connector.missing_credentials({"PRINTIFY_API_KEY": "k"})
    assert missing == ["PRINTIFY_SHOP_ID"]


def test_missing_credentials_block_the_publish(connector, monkeypatch):
    monkeypatch.delenv("PRINTIFY_API_KEY", raising=False)
    monkeypatch.delenv("PRINTIFY_SHOP_ID", raising=False)
    result = connector.publish(_request(), credentials={}, dry_run=True, **BLUEPRINT)
    assert result.success is False
    assert result.error_code == "missing_credentials"


def test_credentials_are_never_echoed_in_a_result(connector):
    result = connector.publish(_request(), credentials=CREDS, dry_run=True, **BLUEPRINT)
    assert "pfy-secret" not in str(result.to_dict())


def test_every_request_sends_a_user_agent(connector, monkeypatch):
    """Printify rejects requests without one. The first draft of this
    connector omitted it and every live call would have failed."""
    import requests
    seen = []

    def _record(url, headers=None, json=None, timeout=None):
        seen.append(headers)
        return _Response(200, {"id": "img" if "uploads" in url else "prod"})

    monkeypatch.setattr(requests, "post", _record)
    monkeypatch.setattr(requests, "get", lambda url, headers=None, timeout=None:
                        (seen.append(headers), _Response(200, []))[1])

    connector.publish(_request(), credentials=CREDS, dry_run=False, **BLUEPRINT)
    connector.fetch_shops(credentials=CREDS)
    connector.fetch_blueprint_providers(384, credentials=CREDS)

    assert len(seen) == 4
    for headers in seen:
        assert headers.get("User-Agent"), "a Printify call went out with no User-Agent"


def test_fetch_shops_needs_only_the_api_key(connector, monkeypatch):
    """Requiring the shop id here would be circular -- this call is how you
    find it."""
    import requests
    monkeypatch.setattr(requests, "get", lambda url, headers=None, timeout=None:
                        _Response(200, [{"id": 5432, "title": "My new store"}]))

    result = connector.fetch_shops(credentials={"PRINTIFY_API_KEY": "k"})
    assert result.success is True
    assert result.metadata["shops"][0]["id"] == 5432


def test_fetch_shops_without_a_key_fails_locally(connector, monkeypatch):
    monkeypatch.delenv("PRINTIFY_API_KEY", raising=False)
    result = connector.fetch_shops(credentials={})
    assert result.success is False
    assert result.error_code == "missing_credentials"


# -- payload ---------------------------------------------------------------

def test_payload_prices_are_integers_not_strings(connector):
    payload = connector.build_payload(_request(), 384, 1, "img_1")
    prices = [v["price"] for v in payload["variants"]]
    assert prices == [2499, 2499]
    assert all(isinstance(p, int) for p in prices)


def test_payload_references_the_uploaded_image_id_not_a_url(connector):
    payload = connector.build_payload(_request(), 384, 1, "img_abc")
    images = payload["print_areas"][0]["placeholders"][0]["images"]
    assert images[0]["id"] == "img_abc"
    assert "url" not in images[0]


def test_payload_enables_every_variant(connector):
    payload = connector.build_payload(_request(), 384, 1, "img_1")
    assert all(v["is_enabled"] for v in payload["variants"])


def test_payload_covers_all_variants_in_the_print_area(connector):
    payload = connector.build_payload(_request(), 384, 1, "img_1")
    assert payload["print_areas"][0]["variant_ids"] == [45740, 45741]


def test_per_variant_price_overrides_the_default(connector):
    payload = connector.build_payload(_request(variants=[
        MerchVariant(vendor_variant_id="45740", label="M"),
        MerchVariant(vendor_variant_id="45742", label="2XL", retail_price=27.99),
    ]), 384, 1, "img_1")
    assert [v["price"] for v in payload["variants"]] == [2499, 2799]


def test_non_numeric_variant_id_is_passed_through_not_coerced(connector):
    payload = connector.build_payload(
        _request(variants=[MerchVariant(vendor_variant_id="large")]), 384, 1, "i",
    )
    assert payload["variants"][0]["id"] == "large"


def test_overlong_title_is_truncated(connector):
    payload = connector.build_payload(_request(title="x" * 400), 384, 1, "i")
    assert len(payload["title"]) == 255


def test_print_position_is_configurable(connector):
    payload = connector.build_payload(_request(), 384, 1, "i", print_position="back")
    assert payload["print_areas"][0]["placeholders"][0]["position"] == "back"


# -- artwork upload --------------------------------------------------------

def test_hosted_artwork_uploads_by_url(connector):
    payload = connector.build_upload_payload(_request())
    assert payload["url"] == GOOD_ART.raw
    assert "contents" not in payload


def test_local_raster_file_uploads_as_base64(connector, tmp_path):
    """The capability that separates Printify from Printful."""
    art_file = tmp_path / "design.png"
    art_file.write_bytes(b"\x89PNG\r\n\x1a\n" + b"0" * 64)
    request = _request(artwork=ArtworkSource.from_url(str(art_file)))

    payload = connector.build_upload_payload(request)
    assert payload["file_name"] == "design.png"
    assert "url" not in payload

    import base64
    assert base64.b64decode(payload["contents"]) == art_file.read_bytes()


def test_local_raster_file_passes_preflight_on_printify(connector, tmp_path):
    art_file = tmp_path / "design.png"
    art_file.write_bytes(b"\x89PNG" + b"0" * 64)
    request = _request(artwork=ArtworkSource.from_url(str(art_file)))
    assert connector.preflight(request, CREDS) is None


def test_the_same_local_file_is_rejected_by_printful(tmp_path):
    """Same artwork, different vendor, different answer -- the capability
    split is real and must not be flattened."""
    from merch.connectors import PrintfulConnector

    art_file = tmp_path / "design.png"
    art_file.write_bytes(b"\x89PNG" + b"0" * 64)
    request = _request(artwork=ArtworkSource.from_url(str(art_file)))

    failure = PrintfulConnector().preflight(request, {"PRINTFUL_API_KEY": "k"})
    assert failure is not None
    assert failure.error_code == "invalid_request"


def test_local_vector_file_is_rejected_even_though_upload_is_allowed(connector, tmp_path):
    """Direct upload solves transport, not format."""
    art_file = tmp_path / "design.svg"
    art_file.write_text("<svg/>", encoding="utf-8")
    request = _request(artwork=ArtworkSource.from_url(str(art_file)))
    failure = connector.preflight(request, CREDS)
    assert failure is not None
    assert "raster" in failure.message


def test_missing_local_file_is_caught_before_upload(connector, tmp_path):
    request = _request(artwork=ArtworkSource.from_url(str(tmp_path / "gone.png")))
    failure = connector.preflight(request, CREDS)
    assert failure is not None
    assert "does not exist" in failure.message


def test_oversize_upload_is_rejected_locally(connector, tmp_path, monkeypatch):
    monkeypatch.setattr(
        "merch.connectors.printify.MAX_UPLOAD_BYTES", 32,
    )
    art_file = tmp_path / "big.png"
    art_file.write_bytes(b"0" * 128)
    request = _request(artwork=ArtworkSource.from_url(str(art_file)))
    with pytest.raises(PrintifyArtworkError, match="upload limit"):
        connector.build_upload_payload(request)


# -- dry run ---------------------------------------------------------------

def test_publish_defaults_to_dry_run(connector):
    result = connector.publish(_request(), credentials=CREDS, **BLUEPRINT)
    assert result.success is True
    assert result.metadata["dry_run"] is True


def test_dry_run_shows_minor_unit_prices(connector):
    result = connector.publish(_request(), credentials=CREDS, dry_run=True, **BLUEPRINT)
    assert result.metadata["prices_minor_units"] == [2499, 2499]


def test_dry_run_does_not_dump_base64_into_the_output(connector, tmp_path):
    """A megabyte of base64 in a terminal buries the actual result."""
    art_file = tmp_path / "design.png"
    art_file.write_bytes(b"\x89PNG" + b"0" * 4096)
    result = connector.publish(
        _request(artwork=ArtworkSource.from_url(str(art_file))),
        credentials=CREDS, dry_run=True, **BLUEPRINT,
    )
    assert result.metadata["upload"] == {
        "mode": "base64_contents", "file_name": "design.png", "bytes": 4100,
    }
    # The summary names the mode; the encoded payload itself is absent.
    import base64
    encoded = base64.b64encode(art_file.read_bytes()).decode("ascii")
    assert encoded not in str(result.to_dict())


def test_dry_run_still_enforces_preflight(connector):
    art = ArtworkSource.from_url("data:image/svg+xml;utf8,%3Csvg%3E")
    result = connector.publish(_request(artwork=art), credentials=CREDS,
                               dry_run=True, **BLUEPRINT)
    assert result.success is False
    assert result.error_code == "invalid_request"


# -- response interpretation ----------------------------------------------

def _interpret(connector, response):
    return connector._interpret_create_response(response, _request(), "9001", "img_1")


def test_created_product_is_reported_with_its_id(connector):
    result = _interpret(connector, _Response(200, {"id": "prod_77"}))
    assert result.success is True
    assert result.metadata["product_id"] == "prod_77"
    assert "prod_77" in result.listing_url


def test_created_product_is_described_as_a_draft(connector):
    """Printify products are not live until published to a sales channel --
    reporting otherwise overstates what happened."""
    result = _interpret(connector, _Response(200, {"id": "prod_77"}))
    assert "draft" in result.message


def test_2xx_without_a_product_id_is_not_success(connector):
    result = _interpret(connector, _Response(200, {"status": "queued"}))
    assert result.success is False
    assert result.error_code == "no_product_id"


def test_error_status_is_reported_with_the_vendor_message(connector):
    result = _interpret(connector, _Response(422, {"message": "variant 45740 invalid"}))
    assert result.success is False
    assert "variant 45740 invalid" in result.message


def test_non_json_response_is_reported_not_crashed(connector):
    result = _interpret(connector, _Response(502, text="<html/>", raise_on_json=True))
    assert result.success is False
    assert result.error_code == "bad_response"


def test_failed_product_creation_still_reports_the_orphaned_image(connector):
    """The artwork already uploaded. Losing that id leaks an asset in the
    account with no way to find it."""
    result = _interpret(connector, _Response(500, {"message": "boom"}))
    assert result.metadata["image_id"] == "img_1"


# -- two-step flow ---------------------------------------------------------

def test_upload_failure_stops_before_product_creation(connector, monkeypatch):
    import requests
    calls = []

    def _post(url, headers=None, json=None, timeout=None):
        calls.append(url)
        return _Response(400, {"message": "bad image"})

    monkeypatch.setattr(requests, "post", _post)
    result = connector.publish(_request(), credentials=CREDS, dry_run=False, **BLUEPRINT)

    assert result.success is False
    assert result.error_code == "upload_failed"
    assert len(calls) == 1, "must not attempt product creation after a failed upload"


def test_successful_flow_uploads_then_creates(connector, monkeypatch):
    import requests
    calls = []

    def _post(url, headers=None, json=None, timeout=None):
        calls.append((url, json))
        if "uploads" in url:
            return _Response(200, {"id": "img_xyz"})
        return _Response(200, {"id": "prod_1"})

    monkeypatch.setattr(requests, "post", _post)
    result = connector.publish(_request(), credentials=CREDS, dry_run=False, **BLUEPRINT)

    assert result.success is True
    assert len(calls) == 2
    assert "uploads/images.json" in calls[0][0]
    assert "shops/9001/products.json" in calls[1][0]
    images = calls[1][1]["print_areas"][0]["placeholders"][0]["images"]
    assert images[0]["id"] == "img_xyz", "product must reference the uploaded image"


def test_upload_without_an_image_id_does_not_proceed(connector, monkeypatch):
    import requests
    calls = []

    def _post(url, headers=None, json=None, timeout=None):
        calls.append(url)
        return _Response(200, {"file_name": "x.png"})

    monkeypatch.setattr(requests, "post", _post)
    result = connector.publish(_request(), credentials=CREDS, dry_run=False, **BLUEPRINT)
    assert result.success is False
    assert result.error_code == "no_image_id"
    assert len(calls) == 1
