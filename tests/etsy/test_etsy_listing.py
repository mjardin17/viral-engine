"""Tests for lib/etsy_listing.py — the draft-create / image-upload /
activate flow, and the who_made/when_made/is_supply policy triangle that
has no eBay analogue.
"""

import pytest

from lib.etsy_listing import (
    EtsyDigitalFileSource,
    EtsyImageSource,
    EtsyListingClient,
    EtsyListingError,
    EtsyProduct,
    EtsyValidationError,
    build_create_draft_payload,
)


class FakeResponse:
    def __init__(self, status_code: int, payload=None):
        self.status_code = status_code
        self._payload = payload

    def json(self):
        if self._payload is None:
            raise ValueError("no json body")
        return self._payload


def make_transport(responses):
    """Transport returning queued responses, recording each call."""
    calls = []

    def transport(method, url, headers, body_kind, body):
        calls.append({"method": method, "url": url, "headers": headers,
                      "body_kind": body_kind, "body": body})
        if not responses:
            raise AssertionError(f"unexpected extra call: {method} {url}")
        return responses.pop(0)

    transport.calls = calls
    return transport


def make_product(**overrides):
    defaults = dict(
        sku="CARD-VINTAGE-001",
        title="1986 Vintage Topps Card",
        description="Genuine vintage trading card, stored in a sleeve.",
        price="24.99",
        who_made="someone_else",
        when_made="1980s",
        taxonomy_id="1234",
        shipping_profile_id="SHIP-1",
        images=(EtsyImageSource(local_path="/tmp/card.jpg"),),
    )
    defaults.update(overrides)
    return EtsyProduct(**defaults)


def _write_temp_file(tmp_path, name="book.epub", size_bytes=1024):
    path = tmp_path / name
    path.write_bytes(b"x" * size_bytes)
    return str(path)


def make_digital_product(tmp_path, **overrides):
    """A digital-book listing — no shipping_profile_id, no images by
    default, one real (on-disk) digital file so EtsyDigitalFileSource's
    existence/size checks have something real to check."""
    defaults = dict(
        sku="BOOK-DIGITAL-001",
        title="The Digital Book",
        description="A downloadable ebook.",
        price="9.99",
        who_made="i_did",
        when_made="made_to_order",
        taxonomy_id="5678",
        listing_type="download",
        digital_files=(EtsyDigitalFileSource(
            local_path=_write_temp_file(tmp_path), filename="book.epub"),),
    )
    defaults.update(overrides)
    return EtsyProduct(**defaults)


# --------------------------------------------------------------------------
# Validation
# --------------------------------------------------------------------------

def test_title_over_140_chars_is_rejected_not_truncated():
    with pytest.raises(EtsyValidationError, match="140"):
        make_product(title="x" * 141)


def test_title_disallowed_character_is_rejected():
    with pytest.raises(EtsyValidationError, match="character"):
        make_product(title="Card <script>")


def test_title_allows_at_most_one_of_each_single_use_char():
    # one % is fine
    make_product(title="50% off vintage card")
    with pytest.raises(EtsyValidationError, match="%"):
        make_product(title="50% off, 20% more vintage card")


def test_unknown_who_made_is_rejected():
    with pytest.raises(EtsyValidationError, match="who_made"):
        make_product(who_made="a_wizard")


def test_unknown_when_made_is_rejected():
    with pytest.raises(EtsyValidationError, match="when_made"):
        make_product(when_made="stone_age")


def test_taxonomy_id_is_required():
    with pytest.raises(EtsyValidationError, match="taxonomy_id"):
        make_product(taxonomy_id="")


def test_physical_listing_requires_shipping_profile_id():
    with pytest.raises(EtsyValidationError, match="shipping_profile_id"):
        make_product(shipping_profile_id=None)


def test_download_listing_does_not_require_shipping_profile_id():
    # Should not raise.
    make_product(listing_type="download", shipping_profile_id=None)


def test_zero_or_negative_price_is_rejected():
    with pytest.raises(EtsyValidationError, match="positive"):
        make_product(price="0")


def test_too_many_images_is_rejected():
    images = tuple(EtsyImageSource(local_path=f"/tmp/{i}.jpg") for i in range(11))
    with pytest.raises(EtsyValidationError, match="10"):
        make_product(images=images)


def test_too_many_tags_is_rejected():
    with pytest.raises(EtsyValidationError, match="13"):
        make_product(tags=tuple(f"tag{i}" for i in range(14)))


def test_tag_over_20_chars_is_rejected():
    with pytest.raises(EtsyValidationError, match="20"):
        make_product(tags=("x" * 21,))


def test_image_source_requires_exactly_one_of_url_or_local_path():
    with pytest.raises(EtsyValidationError):
        EtsyImageSource()
    with pytest.raises(EtsyValidationError):
        EtsyImageSource(url="https://example.com/a.jpg", local_path="/tmp/a.jpg")


def test_image_url_must_be_https():
    with pytest.raises(EtsyValidationError, match="https"):
        EtsyImageSource(url="http://example.com/a.jpg")


# --------------------------------------------------------------------------
# The who_made / when_made / is_supply policy triangle — no eBay analogue
# --------------------------------------------------------------------------

def test_someone_else_with_recent_when_made_and_not_supply_is_rejected():
    """A listing claiming 'someone else made it' but not vintage and not a
    supply doesn't fit any of Etsy's three allowed listing categories."""
    with pytest.raises(EtsyValidationError, match="eligible"):
        make_product(who_made="someone_else", when_made="2020_2023", is_supply=False)


def test_someone_else_with_recent_when_made_and_is_supply_is_allowed():
    # A supply item doesn't need to be vintage — should not raise.
    make_product(who_made="someone_else", when_made="2020_2023", is_supply=True)


def test_i_did_with_recent_when_made_is_allowed():
    # Handmade items are exempt from the vintage check entirely.
    make_product(who_made="i_did", when_made="2020_2023", is_supply=False)


def test_someone_else_with_old_when_made_is_allowed():
    # Genuine vintage — should not raise.
    make_product(who_made="someone_else", when_made="before_1700", is_supply=False)


# --------------------------------------------------------------------------
# Payload shape
# --------------------------------------------------------------------------

def test_create_draft_payload_has_no_state_field():
    """createDraftListing cannot set state — activation is a separate call."""
    payload = build_create_draft_payload(make_product())
    assert "state" not in payload
    assert payload["price"] == "24.99"
    assert payload["who_made"] == "someone_else"


def test_price_uses_decimal_so_cents_are_not_truncated():
    assert make_product(price=1.15).price == "1.15"
    assert make_product(price="24.9").price == "24.90"


# --------------------------------------------------------------------------
# Flow
# --------------------------------------------------------------------------

def test_dry_run_sends_nothing_and_is_not_published():
    transport = make_transport([])
    client = EtsyListingClient("token", "SHOP1", "apikey", transport=transport)

    result = client.create_listing(make_product(), dry_run=True)

    assert transport.calls == []
    assert result.dry_run is True
    assert result.listing_id is None
    assert result.published is False
    assert "create_draft" in result.payloads


def test_happy_path_draft_only_stops_before_activation():
    transport = make_transport([
        FakeResponse(201, {"listing_id": "L123"}),
        FakeResponse(201, {"image_id": "IMG1"}),
    ])
    client = EtsyListingClient("token", "SHOP1", "apikey", transport=transport)

    result = client.create_listing(make_product(), target_state="draft", dry_run=False)

    methods = [(c["method"], c["body_kind"]) for c in transport.calls]
    assert methods == [("POST", "form"), ("POST", "multipart")]
    assert result.listing_id == "L123"
    assert result.images_uploaded == 1
    assert result.published is False, "draft target must never activate"


def test_happy_path_active_makes_all_three_calls():
    transport = make_transport([
        FakeResponse(201, {"listing_id": "L123"}),
        FakeResponse(201, {"image_id": "IMG1"}),
        FakeResponse(200, {"state": "active"}),
    ])
    client = EtsyListingClient("token", "SHOP1", "apikey", transport=transport)

    result = client.create_listing(make_product(), target_state="active", dry_run=False)

    methods = [c["method"] for c in transport.calls]
    assert methods == ["POST", "POST", "PATCH"]
    assert result.published is True


def test_default_target_state_is_draft():
    transport = make_transport([
        FakeResponse(201, {"listing_id": "L123"}),
        FakeResponse(201, {"image_id": "IMG1"}),
    ])
    client = EtsyListingClient("token", "SHOP1", "apikey", transport=transport)

    result = client.create_listing(make_product(), dry_run=False)

    assert len(transport.calls) == 2, "must not PATCH/activate unless explicitly asked"
    assert result.published is False


def test_x_api_key_header_present_on_every_call():
    transport = make_transport([
        FakeResponse(201, {"listing_id": "L123"}),
        FakeResponse(201, {"image_id": "IMG1"}),
    ])
    client = EtsyListingClient("token", "SHOP1", "apikey123", transport=transport)

    client.create_listing(make_product(), dry_run=False)

    for call in transport.calls:
        assert call["headers"]["x-api-key"] == "apikey123"


def test_failure_at_create_names_the_step_and_has_no_listing_id():
    transport = make_transport([FakeResponse(400, {"error": "bad taxonomy_id"})])
    client = EtsyListingClient("token", "SHOP1", "apikey", transport=transport)

    with pytest.raises(EtsyListingError) as exc:
        client.create_listing(make_product(), dry_run=False)

    assert exc.value.step == "createDraftListing"
    assert exc.value.listing_id is None
    assert len(transport.calls) == 1, "must not attempt image upload without a listing_id"


def test_create_accepted_but_no_listing_id_is_an_error_not_a_silent_pass():
    transport = make_transport([FakeResponse(201, {})])  # 201 but no listing_id
    client = EtsyListingClient("token", "SHOP1", "apikey", transport=transport)

    with pytest.raises(EtsyListingError) as exc:
        client.create_listing(make_product(), dry_run=False)

    assert exc.value.step == "createDraftListing"
    assert exc.value.listing_id is None


def test_image_upload_failure_carries_listing_id_and_does_not_activate():
    """The dangerous middle state: a real, valid draft exists (free, not
    buyer-visible) but an image failed. Must not proceed to activation,
    and must never claim the listing is published."""
    transport = make_transport([
        FakeResponse(201, {"listing_id": "L123"}),
        FakeResponse(500, {"error": "upload failed"}),
    ])
    client = EtsyListingClient("token", "SHOP1", "apikey", transport=transport)

    with pytest.raises(EtsyListingError) as exc:
        client.create_listing(make_product(), target_state="active", dry_run=False)

    assert exc.value.step == "uploadListingImage"
    assert exc.value.listing_id == "L123", "must carry the orphaned draft's id so a caller can resume"
    assert len(transport.calls) == 2, "must not attempt activation after an image upload failure"


def test_activation_failure_carries_listing_id_and_reports_not_published():
    transport = make_transport([
        FakeResponse(201, {"listing_id": "L123"}),
        FakeResponse(201, {"image_id": "IMG1"}),
        FakeResponse(400, {"error": "missing return policy"}),
    ])
    client = EtsyListingClient("token", "SHOP1", "apikey", transport=transport)

    with pytest.raises(EtsyListingError) as exc:
        client.create_listing(make_product(), target_state="active", dry_run=False)

    assert exc.value.step == "activateListing"
    assert exc.value.listing_id == "L123"


def test_activation_returning_non_active_state_is_an_error():
    """200 OK but state isn't 'active' — must not be reported as published."""
    transport = make_transport([
        FakeResponse(201, {"listing_id": "L123"}),
        FakeResponse(201, {"image_id": "IMG1"}),
        FakeResponse(200, {"state": "draft"}),  # accepted the PATCH but didn't flip
    ])
    client = EtsyListingClient("token", "SHOP1", "apikey", transport=transport)

    with pytest.raises(EtsyListingError) as exc:
        client.create_listing(make_product(), target_state="active", dry_run=False)

    assert exc.value.step == "activateListing"
    assert "NOT live" in str(exc.value)


def test_empty_access_token_is_rejected_at_construction():
    with pytest.raises(EtsyValidationError, match="access_token"):
        EtsyListingClient("", "SHOP1", "apikey")


def test_empty_shop_id_is_rejected_at_construction():
    with pytest.raises(EtsyValidationError, match="shop_id"):
        EtsyListingClient("token", "", "apikey")


def test_empty_api_key_is_rejected_at_construction():
    with pytest.raises(EtsyValidationError, match="api_key"):
        EtsyListingClient("token", "SHOP1", "")


def test_listing_id_is_url_encoded_in_image_and_activate_calls():
    """listing_id comes back from Etsy's own JSON response and is reused
    unvalidated in URLs — same lesson as eBay's SKU/offer_id encoding."""
    transport = make_transport([
        FakeResponse(201, {"listing_id": "L 123/A"}),
        FakeResponse(201, {"image_id": "IMG1"}),
        FakeResponse(200, {"state": "active"}),
    ])
    client = EtsyListingClient("token", "SHOP1", "apikey", transport=transport)

    client.create_listing(make_product(), target_state="active", dry_run=False)

    image_url = transport.calls[1]["url"]
    activate_url = transport.calls[2]["url"]
    assert "L%20123%2FA" in image_url
    assert "L%20123%2FA" in activate_url
    assert "L 123/A" not in image_url
    assert "L 123/A" not in activate_url


# --------------------------------------------------------------------------
# EtsyDigitalFileSource — digital-download files (books, printables, etc.)
# --------------------------------------------------------------------------

def test_digital_file_source_requires_exactly_one_of_url_or_local_path():
    with pytest.raises(EtsyValidationError):
        EtsyDigitalFileSource(filename="book.epub")
    with pytest.raises(EtsyValidationError):
        EtsyDigitalFileSource(
            url="https://example.com/book.epub", local_path="/tmp/book.epub",
            filename="book.epub",
        )


def test_digital_file_url_must_be_https():
    with pytest.raises(EtsyValidationError, match="https"):
        EtsyDigitalFileSource(url="http://example.com/book.epub", filename="book.epub")


def test_digital_file_requires_filename(tmp_path):
    path = _write_temp_file(tmp_path)
    with pytest.raises(EtsyValidationError, match="filename"):
        EtsyDigitalFileSource(local_path=path)


def test_digital_file_local_path_must_exist(tmp_path):
    with pytest.raises(EtsyValidationError, match="does not exist"):
        EtsyDigitalFileSource(local_path=str(tmp_path / "missing.epub"), filename="book.epub")


def test_digital_file_over_20mb_is_rejected(tmp_path):
    path = _write_temp_file(tmp_path, size_bytes=21 * 1024 * 1024)
    with pytest.raises(EtsyValidationError, match="20MB"):
        EtsyDigitalFileSource(local_path=path, filename="book.epub")


def test_digital_file_under_20mb_is_allowed(tmp_path):
    path = _write_temp_file(tmp_path, size_bytes=1024)
    EtsyDigitalFileSource(local_path=path, filename="book.epub")  # should not raise


def test_digital_file_url_source_skips_size_check_since_size_is_unknown():
    # Should not raise — size can only be known after the server fetches it.
    EtsyDigitalFileSource(url="https://example.com/book.epub", filename="book.epub")


# --------------------------------------------------------------------------
# EtsyProduct — digital_files cross-field validation
# --------------------------------------------------------------------------

def test_digital_files_require_download_or_both_listing_type(tmp_path):
    path = _write_temp_file(tmp_path)
    with pytest.raises(EtsyValidationError, match="listing_type"):
        make_product(
            listing_type="physical",
            digital_files=(EtsyDigitalFileSource(local_path=path, filename="book.epub"),),
        )


def test_digital_files_allowed_on_both_listing_type(tmp_path):
    path = _write_temp_file(tmp_path)
    make_product(  # should not raise
        listing_type="both",
        digital_files=(EtsyDigitalFileSource(local_path=path, filename="book.epub"),),
    )


def test_more_than_5_digital_files_is_rejected(tmp_path):
    files = tuple(
        EtsyDigitalFileSource(
            local_path=_write_temp_file(tmp_path, name=f"f{i}.epub"), filename=f"f{i}.epub")
        for i in range(6)
    )
    with pytest.raises(EtsyValidationError, match="5"):
        make_product(listing_type="download", digital_files=files)


def test_download_listing_without_digital_files_is_allowed_at_construction():
    # Matches Etsy's real flow: a draft can be created file-less. The
    # requirement to actually have a file is enforced only at activation
    # (see the create_listing tests below), not at construction.
    make_product(listing_type="download", shipping_profile_id=None)  # should not raise


# --------------------------------------------------------------------------
# Flow — digital file upload
# --------------------------------------------------------------------------

def test_digital_file_upload_happens_after_images_before_activation(tmp_path):
    transport = make_transport([
        FakeResponse(201, {"listing_id": "L123"}),
        FakeResponse(201, {"image_id": "IMG1"}),
        FakeResponse(201, {"listing_file_id": "F1"}),
        FakeResponse(200, {"state": "active"}),
    ])
    client = EtsyListingClient("token", "SHOP1", "apikey", transport=transport)
    product = make_digital_product(
        tmp_path, listing_type="both",
        images=(EtsyImageSource(local_path="/tmp/cover.jpg"),),
    )

    result = client.create_listing(product, target_state="active", dry_run=False)

    methods = [(c["method"], c["body_kind"]) for c in transport.calls]
    assert methods == [("POST", "form"), ("POST", "multipart"), ("POST", "multipart"), ("PATCH", "form")]
    assert result.files_uploaded == 1
    assert result.images_uploaded == 1
    assert result.published is True


def test_digital_file_upload_uses_file_and_name_fields(tmp_path):
    transport = make_transport([
        FakeResponse(201, {"listing_id": "L123"}),
        FakeResponse(201, {"listing_file_id": "F1"}),
    ])
    client = EtsyListingClient("token", "SHOP1", "apikey", transport=transport)
    product = make_digital_product(tmp_path)

    client.create_listing(product, dry_run=False)

    file_call = transport.calls[1]
    assert file_call["body"]["name"] == "book.epub"
    assert file_call["body"]["rank"] == 1
    assert "file" in file_call["body"]


def test_draft_only_still_uploads_digital_files_but_does_not_activate(tmp_path):
    transport = make_transport([
        FakeResponse(201, {"listing_id": "L123"}),
        FakeResponse(201, {"listing_file_id": "F1"}),
    ])
    client = EtsyListingClient("token", "SHOP1", "apikey", transport=transport)
    product = make_digital_product(tmp_path)

    result = client.create_listing(product, target_state="draft", dry_run=False)

    assert result.files_uploaded == 1
    assert result.published is False


def test_activation_without_digital_files_on_download_listing_is_refused():
    transport = make_transport([
        FakeResponse(201, {"listing_id": "L123"}),
    ])
    client = EtsyListingClient("token", "SHOP1", "apikey", transport=transport)
    product = make_product(listing_type="download", shipping_profile_id=None, images=())

    with pytest.raises(EtsyListingError) as exc:
        client.create_listing(product, target_state="active", dry_run=False)

    assert exc.value.step == "activate"
    assert exc.value.listing_id == "L123"
    assert len(transport.calls) == 1, "must not attempt activation with nothing to sell"


def test_activation_with_failed_digital_file_upload_is_refused(tmp_path):
    transport = make_transport([
        FakeResponse(201, {"listing_id": "L123"}),
        FakeResponse(500, {"error": "upload failed"}),
    ])
    client = EtsyListingClient("token", "SHOP1", "apikey", transport=transport)
    product = make_digital_product(tmp_path)

    with pytest.raises(EtsyListingError) as exc:
        client.create_listing(product, target_state="active", dry_run=False)

    assert exc.value.step == "uploadListingFile"
    assert exc.value.listing_id == "L123", "must carry the orphaned draft's id so a caller can resume"
