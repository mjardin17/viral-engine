"""Product feed generation for Google Merchant Center and Meta (Facebook/Instagram).

One product record -> three surfaces:
  * Google Shopping        (RSS 2.0 XML with the g: namespace)
  * Facebook Shops         (CSV)
  * Instagram Shopping     (same CSV -- Meta reads one catalog for both)

Both specs descend from Google's product data spec, so the field set is nearly
identical; only the serialisation and a few enum spellings differ. That's why
this is one module with two writers rather than two integrations.

⚠ HARD REQUIREMENT YOU CANNOT CODE AROUND: every item needs a `link` to a
product page **on a domain you own and have verified** with Google Merchant
Center / Meta Commerce Manager. Neither platform accepts a feed that links
straight to an eBay listing on ebay.com -- the destination has to be your
domain. So a feed is only useful once a product page exists somewhere you
control. This module takes the URL as input and validates its shape; it
cannot conjure the page.

⚠ Written from the published Google/Meta product-data specs and NOT submitted
to a live Merchant Center or Commerce Manager account. Field names and enum
values are [Likely], not verified against a real feed ingestion.
"""

from __future__ import annotations

import csv
import io
import re
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from typing import Iterable, Optional
from xml.sax.saxutils import escape

# Google caps title at 150 and description at 5000. Meta is the same or looser,
# so the stricter Google limits are used for both.
TITLE_MAX = 150
DESCRIPTION_MAX = 5000

# Feed-spec condition values. Both platforms accept exactly these three.
FEED_CONDITIONS = frozenset({"new", "refurbished", "used"})

# Maps the condition vocabularies already used in this codebase onto the three
# values the feeds accept. eBay's Inventory API enum (lib/ebay_listing.py) and
# the free-text conditions in the products table both land here.
CONDITION_MAP = {
    "new": "new",
    "new_other": "new",
    "new_with_defects": "new",
    "like_new": "used",
    "used_excellent": "used",
    "used_very_good": "used",
    "used_good": "used",
    "used_acceptable": "used",
    "for_parts_or_not_working": "used",
    "refurbished": "refurbished",
    "manufacturer refurbished": "refurbished",
    "seller refurbished": "refurbished",
    "pre-owned": "used",
    "pre-owned - excellent": "used",
    "very good": "used",
    "good": "used",
    "acceptable": "used",
}


class FeedValidationError(ValueError):
    """Item rejected before it can poison a feed."""


def normalise_condition(raw: Optional[str]) -> str:
    """Map an arbitrary condition string onto a feed-legal value.

    Raises rather than defaulting to 'used'. A silently wrong condition is a
    listing-quality problem that surfaces as buyer complaints, not as an error.
    """
    key = str(raw or "").strip().lower()
    if not key:
        raise FeedValidationError(
            "condition is required; feeds reject items without one"
        )
    if key in FEED_CONDITIONS:
        return key
    if key in CONDITION_MAP:
        return CONDITION_MAP[key]
    raise FeedValidationError(
        f"condition {raw!r} does not map to a feed value "
        f"({', '.join(sorted(FEED_CONDITIONS))}). Add it to CONDITION_MAP "
        "deliberately rather than guessing."
    )


def format_price(price: str | float | Decimal, currency: str = "USD") -> str:
    """Feeds want '24.99 USD' -- value, space, ISO currency code.

    Two subtleties, both found by review after they had already shipped here:

    * `Decimal('Infinity') <= 0` is False, so a non-finite price sailed past
      the positivity check and serialised as the literal string
      "Infinity USD" into a live feed. `Decimal('NaN') <= 0` meanwhile RAISES
      InvalidOperation -- from outside the try block, so callers got an
      undocumented exception type instead of FeedValidationError.
    * `f"{Decimal('0.125'):.2f}"` is '0.12', not '0.13'. Decimal formatting
      rounds half-to-even; retail pricing expects half-up.
    """
    try:
        value = Decimal(str(price))
    except (InvalidOperation, ValueError) as exc:
        raise FeedValidationError(f"price is not a number: {price!r}") from exc
    if not value.is_finite():
        raise FeedValidationError(f"price must be a finite number, got {price!r}")
    if value <= 0:
        raise FeedValidationError(f"price must be positive, got {price!r}")
    if not re.fullmatch(r"[A-Z]{3}", currency):
        raise FeedValidationError(
            f"currency must be a 3-letter ISO code, got {currency!r}"
        )
    try:
        cents = value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    except InvalidOperation as exc:
        raise FeedValidationError(
            f"price is too large to express in cents: {price!r}"
        ) from exc
    return f"{cents} {currency}"


@dataclass(frozen=True)
class FeedProduct:
    """A single feed item, normalised and validated on construction."""

    id: str
    title: str
    description: str
    link: str
    image_link: str
    price: str
    condition: str
    availability: str
    brand: Optional[str] = None
    gtin: Optional[str] = None
    mpn: Optional[str] = None

    @staticmethod
    def from_product(
        *,
        sku: str,
        title: str,
        description: str,
        price: str | float | Decimal,
        image_url: Optional[str],
        condition: Optional[str],
        quantity: int,
        link: str,
        currency: str = "USD",
        brand: Optional[str] = None,
        gtin: Optional[str] = None,
        mpn: Optional[str] = None,
    ) -> "FeedProduct":
        """Build from the shape used by `storefront_products` / ProductRow."""
        if not str(sku or "").strip():
            raise FeedValidationError("sku is required (becomes the feed 'id')")
        if not str(title or "").strip():
            raise FeedValidationError("title is required")
        if not str(description or "").strip():
            raise FeedValidationError(
                "description is required; both Google and Meta reject empty ones"
            )
        if not _is_http_url(link):
            raise FeedValidationError(
                f"link must be an http(s) URL on a domain you own and have "
                f"verified with Google/Meta, got {link!r}"
            )
        if not _is_http_url(image_url):
            raise FeedValidationError(
                f"image_link must be a publicly fetchable http(s) URL, got "
                f"{image_url!r}. Feeds crawl images; local paths fail."
            )
        # Identifier requirement: Google needs brand + (gtin or mpn) for most
        # categories, but accepts brand alone for one-of-a-kind/used goods,
        # which is what resale inventory is. Requiring at least one identifier
        # catches the item that would silently be disapproved.
        if not any(str(v or "").strip() for v in (brand, gtin, mpn)):
            raise FeedValidationError(
                "at least one of brand / gtin / mpn is required; items with no "
                "identifier are disapproved by Google Merchant Center"
            )

        return FeedProduct(
            id=str(sku).strip(),
            title=_truncate(title, TITLE_MAX),
            description=_truncate(description, DESCRIPTION_MAX),
            link=link.strip(),
            image_link=str(image_url).strip(),
            price=format_price(price, currency),
            condition=normalise_condition(condition),
            availability="in_stock" if quantity > 0 else "out_of_stock",
            brand=_clean(brand),
            gtin=_clean(gtin),
            mpn=_clean(mpn),
        )


def _clean(value: Optional[str]) -> Optional[str]:
    text = str(value or "").strip()
    return text or None


def _is_http_url(value: Optional[str]) -> bool:
    return str(value or "").startswith(("http://", "https://"))


def _truncate(text: str, limit: int) -> str:
    text = str(text).strip()
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"


# --------------------------------------------------------------------------
# Google Merchant Center -- RSS 2.0 with the g: namespace
# --------------------------------------------------------------------------

GOOGLE_NS = "http://base.google.com/ns/1.0"


def build_google_rss(products: Iterable[FeedProduct], *, title: str,
                     link: str, description: str) -> str:
    """Serialise to the RSS 2.0 feed Google Merchant Center fetches."""
    items: list[str] = []
    for p in products:
        fields = [
            ("g:id", p.id),
            ("g:title", p.title),
            ("g:description", p.description),
            ("g:link", p.link),
            ("g:image_link", p.image_link),
            ("g:availability", p.availability),
            ("g:price", p.price),
            ("g:condition", p.condition),
        ]
        if p.brand:
            fields.append(("g:brand", p.brand))
        if p.gtin:
            fields.append(("g:gtin", p.gtin))
        if p.mpn:
            fields.append(("g:mpn", p.mpn))
        body = "".join(
            f"      <{tag}>{escape(str(value))}</{tag}>\n" for tag, value in fields
        )
        items.append(f"    <item>\n{body}    </item>\n")

    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<rss version="2.0" xmlns:g="{GOOGLE_NS}">\n'
        "  <channel>\n"
        f"    <title>{escape(title)}</title>\n"
        f"    <link>{escape(link)}</link>\n"
        f"    <description>{escape(description)}</description>\n"
        + "".join(items)
        + "  </channel>\n</rss>\n"
    )


# --------------------------------------------------------------------------
# Meta (Facebook Shops + Instagram Shopping) -- CSV
# --------------------------------------------------------------------------

META_COLUMNS = [
    "id", "title", "description", "availability", "condition",
    "price", "link", "image_link", "brand", "gtin", "mpn",
]

# Characters that make a spreadsheet treat a cell as a formula. A feed CSV is
# routinely opened in Excel/Sheets for a manual look before upload, so a title
# beginning '=' becomes executable there even though Meta itself treats it as
# text. Neutralised on write rather than at input, so the stored product data
# stays clean and only the export is defensive.
_FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")


def _csv_safe(value: str) -> str:
    text = str(value or "")
    if text.startswith(_FORMULA_PREFIXES):
        return "'" + text
    return text


def build_meta_csv(products: Iterable[FeedProduct]) -> str:
    """Serialise to the CSV catalog Meta Commerce Manager ingests.

    One catalog feeds both Facebook Shops and Instagram Shopping -- there is
    no separate Instagram feed.
    """
    buffer = io.StringIO()
    # lineterminator is explicit: csv defaults to \r\n, and Meta's importer is
    # fine with it, but tests and diffs are far easier to read with \n.
    writer = csv.DictWriter(buffer, fieldnames=META_COLUMNS, lineterminator="\n")
    writer.writeheader()
    for p in products:
        writer.writerow({
            "id": _csv_safe(p.id),
            "title": _csv_safe(p.title),
            "description": _csv_safe(p.description),
            "availability": p.availability,
            "condition": p.condition,
            "price": p.price,
            "link": p.link,
            "image_link": p.image_link,
            # Meta requires brand; fall back rather than emitting empty. gtin
            # and mpn also get their own columns so the identifier data is not
            # discarded when a brand is present.
            "brand": _csv_safe(p.brand or p.mpn or p.gtin or ""),
            "gtin": _csv_safe(p.gtin or ""),
            "mpn": _csv_safe(p.mpn or ""),
        })
    return buffer.getvalue()
