"""
tests/storyforge2/test_merch_artwork.py -- artwork classification for POD.

The case that matters: the shipped MerchPulse Design stores its artwork as a
`data:image/svg+xml` URI. That is not submittable to any POD vendor, and the
whole point of this module is saying so before a connector tries.
"""

import pytest

from storyforge2.merch.artwork import (
    MIN_PRINT_PIXELS, ArtworkKind, ArtworkSource,
)

# The real Design record from merchpulse_full_export.json, trimmed to the
# fields this module reads.
SHIPPED_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="1200" '
    'viewBox="0 0 1200 1200"><rect width="1200" height="1200" fill="#1f3a5f"/>'
    '<circle cx="600" cy="600" r="570" fill="none" stroke="#ffffff" '
    'stroke-width="12"/><text x="600" y="540">Rooted</text></svg>'
)
SHIPPED_DESIGN = {
    "id": "6a7fe393835ceecbd4131f67",
    "title": "Rooted & Ready",
    "product_type": "tshirt",
    "dimensions": "4500x5400",
    "print_quality_ok": True,
    "artwork_url": "data:image/svg+xml;utf8,%3Csvg%20xmlns%3D...%3C%2Fsvg%3E",
    "svg_source": SHIPPED_SVG,
}


# -- the shipped design ----------------------------------------------------

def test_shipped_design_is_a_data_uri():
    art = ArtworkSource.from_design(SHIPPED_DESIGN)
    assert art.kind is ArtworkKind.DATA_URI
    assert art.mime == "image/svg+xml"


def test_shipped_design_is_not_pod_ready():
    """It passed MerchPulse's own print_quality_ok check and still cannot be
    submitted -- that flag is about the design, not about deliverability."""
    ok, reason = ArtworkSource.from_design(SHIPPED_DESIGN).is_pod_ready()
    assert ok is False
    assert "data: URI" in reason and "hosted" in reason


def test_shipped_design_declared_size_contradicts_the_asset():
    """The record claims 4500x5400 print resolution; the SVG is 1200x1200.
    The claim is metadata nobody recomputes."""
    art = ArtworkSource.from_design(SHIPPED_DESIGN)
    assert art.declared_dimensions == (4500, 5400)
    assert art.intrinsic_dimensions == (1200, 1200)
    discrepancy = art.dimension_discrepancy()
    assert discrepancy is not None
    assert "unverified metadata" in discrepancy


def test_shipped_design_reports_both_problems():
    warnings = ArtworkSource.from_design(SHIPPED_DESIGN).warnings()
    assert len(warnings) == 2


# -- classification --------------------------------------------------------

@pytest.mark.parametrize("url,expected", [
    ("https://cdn.example.com/art.png", ArtworkKind.HOSTED_RASTER),
    ("https://cdn.example.com/art.jpg", ArtworkKind.HOSTED_RASTER),
    ("https://cdn.example.com/art.JPEG", ArtworkKind.HOSTED_RASTER),
    ("https://cdn.example.com/art.svg", ArtworkKind.HOSTED_VECTOR),
    ("https://cdn.example.com/art.eps", ArtworkKind.HOSTED_VECTOR),
    ("data:image/png;base64,iVBORw0KGgo=", ArtworkKind.DATA_URI),
    ("C:/art/design.png", ArtworkKind.LOCAL_FILE),
    ("https://cdn.example.com/no-extension", ArtworkKind.UNKNOWN),
    ("", ArtworkKind.MISSING),
])
def test_url_classification(url, expected):
    assert ArtworkSource.from_url(url).kind is expected


def test_design_with_no_artwork_is_missing():
    art = ArtworkSource.from_design({"id": "d1"})
    assert art.kind is ArtworkKind.MISSING
    ok, reason = art.is_pod_ready()
    assert ok is False
    assert "no artwork" in reason


def test_design_falls_back_to_svg_source_when_url_absent():
    art = ArtworkSource.from_design({"id": "d1", "svg_source": SHIPPED_SVG})
    assert art.kind is ArtworkKind.INLINE_MARKUP
    assert art.intrinsic_dimensions == (1200, 1200)


def test_inline_markup_needs_rasterising():
    art = ArtworkSource.from_design({"id": "d1", "svg_source": SHIPPED_SVG})
    ok, reason = art.is_pod_ready()
    assert ok is False
    assert "rasterised" in reason


# -- readiness -------------------------------------------------------------

def test_hosted_raster_is_pod_ready():
    ok, reason = ArtworkSource.from_url("https://cdn.example.com/art.png").is_pod_ready()
    assert ok is True, reason


def test_http_is_rejected():
    """Vendors fetch print files over HTTPS."""
    ok, reason = ArtworkSource.from_url("http://cdn.example.com/art.png").is_pod_ready()
    assert ok is False
    assert "HTTPS" in reason


def test_hosted_vector_is_rejected_as_a_print_file():
    ok, reason = ArtworkSource.from_url("https://cdn.example.com/art.svg").is_pod_ready()
    assert ok is False
    assert "raster" in reason


def test_local_file_must_be_uploaded_first():
    ok, reason = ArtworkSource.from_url("C:/art/design.png").is_pod_ready()
    assert ok is False
    assert "uploaded" in reason


def test_unknown_format_is_not_assumed_printable():
    ok, reason = ArtworkSource.from_url("https://cdn.example.com/thing").is_pod_ready()
    assert ok is False
    assert "unrecognised" in reason


# -- resolution ------------------------------------------------------------

def test_undersized_artwork_is_rejected():
    small = f'<svg width="800" height="800"></svg>'
    art = ArtworkSource.from_design({"id": "d1", "svg_source": small})
    problem = art.resolution_problem()
    assert problem is not None
    assert str(MIN_PRINT_PIXELS) in problem


def test_print_resolution_artwork_passes_the_size_check():
    big = '<svg width="4500" height="5400"></svg>'
    art = ArtworkSource.from_design({"id": "d1", "svg_source": big})
    assert art.resolution_problem() is None


def test_unknown_size_is_not_treated_as_a_failure():
    """No intrinsic size means unknown, not too small."""
    art = ArtworkSource.from_url("https://cdn.example.com/art.png")
    assert art.intrinsic_dimensions is None
    assert art.resolution_problem() is None


def test_declared_size_alone_never_satisfies_the_size_check():
    """A record cannot pass by claiming a resolution -- only the asset counts."""
    art = ArtworkSource.from_design({
        "id": "d1", "dimensions": "4500x5400",
        "svg_source": '<svg width="600" height="600"></svg>',
    })
    assert art.resolution_problem() is not None


def test_malformed_dimensions_are_ignored_not_guessed():
    art = ArtworkSource.from_design({"id": "d1", "dimensions": "big"})
    assert art.declared_dimensions is None


def test_hyphenated_attributes_are_not_read_as_the_svg_size():
    """Regression: `\\bwidth` matches inside `stroke-width` because a hyphen is
    a non-word char. The real export read as 12x1200 off its border width."""
    art = ArtworkSource.from_design({"id": "d1", "svg_source": SHIPPED_SVG})
    assert art.intrinsic_dimensions == (1200, 1200)


def test_stroke_width_alone_yields_no_size():
    art = ArtworkSource.from_design({
        "id": "d1",
        "svg_source": '<svg viewBox="0 0 100 100"><rect stroke-width="12"/></svg>',
    })
    assert art.intrinsic_dimensions is None


def test_svg_with_unit_suffixed_size_is_not_guessed():
    """'100mm' is not 100px -- an unknown size beats a wrong one."""
    art = ArtworkSource.from_design({
        "id": "d1", "svg_source": '<svg width="100mm" height="100mm"></svg>',
    })
    assert art.intrinsic_dimensions is None


def test_matching_declared_and_intrinsic_sizes_report_no_discrepancy():
    art = ArtworkSource.from_design({
        "id": "d1", "dimensions": "4500x5400",
        "svg_source": '<svg width="4500" height="5400"></svg>',
    })
    assert art.dimension_discrepancy() is None
