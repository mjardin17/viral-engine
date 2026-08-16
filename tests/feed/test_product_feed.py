"""Tests for lib/product_feed.py.

Focus: the things that get a feed silently DISAPPROVED rather than rejected
loudly — wrong condition enum, missing identifier, non-owned link, bad price
format. A disapproved feed looks like "no traffic", not like an error.
"""

import csv
import io
import xml.etree.ElementTree as ET

import pytest

from lib.product_feed import (
    FeedProduct,
    FeedValidationError,
    build_google_rss,
    build_meta_csv,
    format_price,
    normalise_condition,
)

GOOGLE_NS = {"g": "http://base.google.com/ns/1.0"}


def make(**overrides):
    defaults = dict(
        sku="CARD-001",
        title="2024 Topps Chrome Refractor #123",
        description="Near mint, stored in a sleeve since pack-fresh.",
        price="24.99",
        image_url="https://cdn.example.com/front.jpg",
        condition="USED_EXCELLENT",
        quantity=1,
        link="https://jardins-outpost.pages.dev/p/card-001",
        brand="Topps",
    )
    defaults.update(overrides)
    return FeedProduct.from_product(**defaults)


# --------------------------------------------------------------------------
# Condition mapping
# --------------------------------------------------------------------------

def test_ebay_condition_enum_maps_onto_feed_values():
    assert normalise_condition("USED_EXCELLENT") == "used"
    assert normalise_condition("NEW_OTHER") == "new"
    assert normalise_condition("FOR_PARTS_OR_NOT_WORKING") == "used"


def test_feed_native_conditions_pass_through():
    for value in ("new", "used", "refurbished"):
        assert normalise_condition(value) == value


def test_unknown_condition_raises_rather_than_defaulting_to_used():
    with pytest.raises(FeedValidationError, match="does not map"):
        normalise_condition("mint-ish")


def test_missing_condition_is_rejected():
    with pytest.raises(FeedValidationError, match="condition is required"):
        normalise_condition("")


# --------------------------------------------------------------------------
# Price
# --------------------------------------------------------------------------

def test_price_format_is_value_space_currency():
    assert format_price("24.99") == "24.99 USD"
    assert format_price(5, "GBP") == "5.00 GBP"


def test_price_uses_decimal_so_cents_survive():
    assert format_price(1.15) == "1.15 USD"
    assert format_price(0.29) == "0.29 USD"


def test_non_positive_price_is_rejected():
    with pytest.raises(FeedValidationError, match="positive"):
        format_price("0")


def test_bad_currency_code_is_rejected():
    with pytest.raises(FeedValidationError, match="ISO"):
        format_price("10.00", "dollars")


# --------------------------------------------------------------------------
# Item validation
# --------------------------------------------------------------------------

def test_item_with_no_identifier_is_rejected():
    """Google disapproves items with no brand/gtin/mpn — catch it locally."""
    with pytest.raises(FeedValidationError, match="brand / gtin / mpn"):
        make(brand=None, gtin=None, mpn=None)


def test_any_single_identifier_is_enough():
    assert make(brand=None, mpn="TC-123").mpn == "TC-123"
    assert make(brand=None, gtin="00012345678905").gtin == "00012345678905"


def test_non_http_link_is_rejected():
    with pytest.raises(FeedValidationError, match="link must be an http"):
        make(link="/p/card-001")


def test_local_image_path_is_rejected():
    with pytest.raises(FeedValidationError, match="image_link"):
        make(image_url="C:/photos/front.jpg")


def test_empty_description_is_rejected():
    with pytest.raises(FeedValidationError, match="description is required"):
        make(description="   ")


def test_availability_follows_quantity():
    assert make(quantity=3).availability == "in_stock"
    assert make(quantity=0).availability == "out_of_stock"


def test_overlong_title_is_truncated_to_google_limit():
    item = make(title="x" * 200)
    assert len(item.title) == 150


# --------------------------------------------------------------------------
# Google RSS output
# --------------------------------------------------------------------------

def test_google_rss_is_well_formed_and_carries_every_required_field():
    xml = build_google_rss(
        [make()],
        title="Jardin's Outpost",
        link="https://jardins-outpost.pages.dev",
        description="Inventory",
    )
    root = ET.fromstring(xml)  # raises if malformed
    item = root.find("./channel/item")
    assert item is not None

    def g(tag):
        node = item.find(f"g:{tag}", GOOGLE_NS)
        return node.text if node is not None else None

    assert g("id") == "CARD-001"
    assert g("price") == "24.99 USD"
    assert g("condition") == "used"
    assert g("availability") == "in_stock"
    assert g("brand") == "Topps"
    assert g("link").startswith("https://")
    assert g("image_link").startswith("https://")


def test_google_rss_escapes_xml_metacharacters():
    """An unescaped & in a title silently breaks the whole feed parse."""
    xml = build_google_rss(
        [make(title="Card & Sleeve <rare>")],
        title="Shop", link="https://example.com", description="d",
    )
    root = ET.fromstring(xml)
    node = root.find("./channel/item/g:title", GOOGLE_NS)
    assert node.text == "Card & Sleeve <rare>"


def test_google_rss_omits_absent_optional_identifiers():
    xml = build_google_rss(
        [make(brand="Topps", gtin=None, mpn=None)],
        title="Shop", link="https://example.com", description="d",
    )
    root = ET.fromstring(xml)
    assert root.find("./channel/item/g:gtin", GOOGLE_NS) is None
    assert root.find("./channel/item/g:mpn", GOOGLE_NS) is None


def test_google_rss_handles_multiple_items():
    xml = build_google_rss(
        [make(sku="A"), make(sku="B"), make(sku="C")],
        title="Shop", link="https://example.com", description="d",
    )
    root = ET.fromstring(xml)
    ids = [n.text for n in root.findall("./channel/item/g:id", GOOGLE_NS)]
    assert ids == ["A", "B", "C"]


# --------------------------------------------------------------------------
# Meta CSV output
# --------------------------------------------------------------------------

def test_meta_csv_has_the_required_header_and_row():
    text = build_meta_csv([make()])
    rows = list(csv.DictReader(io.StringIO(text)))
    assert len(rows) == 1
    row = rows[0]
    assert row["id"] == "CARD-001"
    assert row["price"] == "24.99 USD"
    assert row["condition"] == "used"
    assert row["availability"] == "in_stock"
    assert row["brand"] == "Topps"


def test_meta_csv_falls_back_to_mpn_when_brand_is_absent():
    text = build_meta_csv([make(brand=None, mpn="TC-123")])
    row = next(csv.DictReader(io.StringIO(text)))
    assert row["brand"] == "TC-123", "Meta requires brand; empty gets disapproved"


def test_meta_csv_quotes_fields_containing_commas():
    text = build_meta_csv([make(description="Mint, sleeved, and boxed")])
    row = next(csv.DictReader(io.StringIO(text)))
    assert row["description"] == "Mint, sleeved, and boxed"


def test_meta_and_google_describe_the_same_item_identically():
    """Both surfaces must agree — divergence shows up as price mismatches."""
    item = make()
    csv_row = next(csv.DictReader(io.StringIO(build_meta_csv([item]))))
    root = ET.fromstring(
        build_google_rss([item], title="s", link="https://e.com", description="d")
    )
    node = root.find("./channel/item/g:price", GOOGLE_NS)
    assert csv_row["price"] == node.text


# --------------------------------------------------------------------------
# Regressions found by review after the module had already been written.
# --------------------------------------------------------------------------

def test_infinite_price_is_rejected_not_serialised_as_the_word_Infinity():
    """Decimal('Infinity') <= 0 is False, so this once produced 'Infinity USD'."""
    with pytest.raises(FeedValidationError, match="finite"):
        format_price(float("inf"))
    with pytest.raises(FeedValidationError, match="finite"):
        format_price(float("-inf"))


def test_nan_price_raises_our_error_type_not_decimal_InvalidOperation():
    """Decimal('NaN') <= 0 raises from OUTSIDE the try; callers saw the wrong type."""
    with pytest.raises(FeedValidationError):
        format_price(float("nan"))


def test_half_cent_rounds_up_not_to_even():
    # Decimal formatting is half-to-even: 0.125 -> '0.12'. Retail wants 0.13.
    assert format_price("0.125") == "0.13 USD"
    assert format_price("2.005") == "2.01 USD"


def test_csv_formula_prefixes_are_neutralised():
    """A title starting '=' executes as a formula when the feed is opened in Excel."""
    text = build_meta_csv([make(title='=HYPERLINK("http://evil","x")')])
    row = next(csv.DictReader(io.StringIO(text)))
    assert row["title"].startswith("'="), row["title"]


def test_csv_neutralises_every_formula_trigger_character():
    for prefix in ("=", "+", "-", "@"):
        text = build_meta_csv([make(description=f"{prefix}cmd")])
        row = next(csv.DictReader(io.StringIO(text)))
        assert row["description"].startswith("'"), prefix


def test_csv_leaves_ordinary_values_untouched():
    row = next(csv.DictReader(io.StringIO(build_meta_csv([make()]))))
    assert not row["title"].startswith("'")
    assert row["title"] == "2024 Topps Chrome Refractor #123"


def test_meta_csv_keeps_gtin_and_mpn_in_their_own_columns():
    """Previously these were discarded whenever a brand was present."""
    text = build_meta_csv([make(brand="Topps", gtin="00012345678905", mpn="TC-123")])
    row = next(csv.DictReader(io.StringIO(text)))
    assert row["brand"] == "Topps"
    assert row["gtin"] == "00012345678905"
    assert row["mpn"] == "TC-123"
