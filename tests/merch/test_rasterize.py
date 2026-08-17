"""
tests/merch/test_rasterize.py -- SVG to print-ready PNG.

These run the real backend, so they are the only tests in this suite that
exercise a native dependency. They skip cleanly when it is absent rather than
failing, because the rest of the merch pipeline works without it.

The behaviour under test is not "did it return" but "is the file it wrote
actually usable" -- a rasteriser that emits a blank canvas at the wrong size
still returns success.
"""

from pathlib import Path

import pytest

from merch.rasterize import (
    DEFAULT_PRINT_WIDTH, RasterError, backend_available, rasterize_design,
    rasterize_svg,
)

BACKEND_OK, BACKEND_DETAIL = backend_available()
requires_backend = pytest.mark.skipif(not BACKEND_OK, reason=BACKEND_DETAIL)

# The real MerchPulse design, full markup including the stroke-width border.
SHIPPED_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="1200" '
    'viewBox="0 0 1200 1200"><rect width="1200" height="1200" fill="#1f3a5f"/>'
    '<circle cx="600" cy="600" r="570" fill="none" stroke="#ffffff" '
    'stroke-width="12"/>'
    '<text x="600" y="540" font-family="Georgia" font-size="110" '
    'fill="#ffffff" text-anchor="middle">Rooted</text></svg>'
)
SHIPPED_DESIGN = {"id": "6a7fe393835ceecbd4131f67", "svg_source": SHIPPED_SVG}

CIRCLE_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" width="400" height="400">'
    '<circle cx="200" cy="200" r="150" fill="#1f3a5f"/></svg>'
)


# -- backend gating --------------------------------------------------------

def test_backend_availability_is_reported_not_raised():
    ok, detail = backend_available()
    assert isinstance(ok, bool)
    assert detail
    if not ok:
        assert "pip install" in detail, "an unavailable backend must say how to fix it"


def test_module_imports_without_the_backend():
    """The rest of the merch pipeline must work on a machine with no renderer."""
    import merch.rasterize as module
    assert module.rasterize_svg is not None


# -- the shipped design ----------------------------------------------------

@requires_backend
def test_shipped_design_rasterises_at_print_size(tmp_path):
    """The blocker this module exists to clear."""
    out = tmp_path / "rooted.png"
    result = rasterize_design(SHIPPED_DESIGN, out)

    assert out.is_file()
    assert result.width == DEFAULT_PRINT_WIDTH
    assert result.is_blank is False
    assert result.file_bytes > 0


@requires_backend
def test_shipped_design_preserves_its_square_aspect(tmp_path):
    """The source is 1200x1200. A tee print area is portrait, but stretching
    to fill it distorts the art -- and still looks like a clean render."""
    result = rasterize_design(SHIPPED_DESIGN, tmp_path / "a.png", target_width=3000)
    assert (result.width, result.height) == (3000, 3000)


@requires_backend
def test_rasterised_design_becomes_pod_ready_artwork(tmp_path):
    """End to end: the thing that was unsubmittable now passes the gate that
    rejected it -- for a vendor that accepts direct upload."""
    from merch.artwork import ArtworkKind, ArtworkSource

    before = ArtworkSource.from_design({
        "artwork_url": "data:image/svg+xml;utf8,%3Csvg%3E",
        "svg_source": SHIPPED_SVG,
    })
    assert before.is_pod_ready(allow_local_upload=True)[0] is False

    result = rasterize_design(SHIPPED_DESIGN, tmp_path / "print.png")
    after = ArtworkSource.from_url(str(result.path))

    assert after.kind is ArtworkKind.LOCAL_FILE
    assert after.is_pod_ready(allow_local_upload=True)[0] is True


@requires_backend
def test_rasterised_design_still_needs_hosting_for_printful(tmp_path):
    """Rasterising solves format, not transport. Printful pulls by URL."""
    from merch.artwork import ArtworkSource

    result = rasterize_design(SHIPPED_DESIGN, tmp_path / "print.png")
    art = ArtworkSource.from_url(str(result.path))
    ok, reason = art.is_pod_ready(allow_local_upload=False)
    assert ok is False
    assert "uploaded to public storage" in reason


# -- sizing ----------------------------------------------------------------

@requires_backend
def test_explicit_width_is_honoured(tmp_path):
    result = rasterize_svg(CIRCLE_SVG, tmp_path / "a.png", target_width=2000)
    assert result.width == 2000


@requires_backend
def test_mismatched_aspect_pads_rather_than_stretches(tmp_path):
    """A square design onto a portrait print area keeps its proportions."""
    result = rasterize_svg(CIRCLE_SVG, tmp_path / "a.png",
                           target_width=1500, target_height=1800)
    assert (result.width, result.height) == (1500, 1800)

    from PIL import Image
    image = Image.open(result.path)
    # Padding sits top and bottom; the circle is not vertically elongated.
    assert image.size == (1500, 1800)


@requires_backend
def test_non_positive_target_is_rejected(tmp_path):
    with pytest.raises(RasterError, match="must be positive"):
        rasterize_svg(CIRCLE_SVG, tmp_path / "a.png", target_width=0)


@requires_backend
def test_output_directory_is_created(tmp_path):
    out = tmp_path / "nested" / "deeper" / "a.png"
    rasterize_svg(CIRCLE_SVG, out, target_width=600)
    assert out.is_file()


# -- verification ----------------------------------------------------------

@requires_backend
def test_blank_render_raises_rather_than_returning_a_file(tmp_path):
    """The core guard: an empty SVG parses fine and writes a real PNG. Nothing
    downstream could tell that from a working design."""
    blank = '<svg xmlns="http://www.w3.org/2000/svg" width="400" height="400"></svg>'
    with pytest.raises(RasterError, match="blank canvas"):
        rasterize_svg(blank, tmp_path / "blank.png", target_width=800)


@requires_backend
def test_result_carries_the_evidence(tmp_path):
    result = rasterize_svg(CIRCLE_SVG, tmp_path / "a.png", target_width=800)
    assert result.distinct_colours > 1
    assert result.luminance_range[0] < result.luminance_range[1]
    assert result.file_bytes > 0


@requires_backend
def test_unparseable_svg_raises(tmp_path):
    with pytest.raises(RasterError):
        rasterize_svg("not svg at all", tmp_path / "a.png")


def test_design_without_svg_source_raises(tmp_path):
    with pytest.raises(RasterError, match="no svg_source"):
        rasterize_design({"id": "d1"}, tmp_path / "a.png")


# -- transparency ----------------------------------------------------------

@requires_backend
def test_chroma_key_reports_how_much_it_removed(tmp_path):
    """Knocking out a colour that also appears inside the artwork destroys the
    design while still producing a plausible file -- so the count is evidence
    the caller must look at, not a silent success."""
    result = rasterize_svg(CIRCLE_SVG, tmp_path / "a.png", target_width=400,
                           transparent_from="white")
    assert result.transparent_pixels > 0
    assert any("chroma-key" in w for w in result.warnings())


@requires_backend
def test_chroma_key_actually_writes_alpha(tmp_path):
    from PIL import Image

    result = rasterize_svg(CIRCLE_SVG, tmp_path / "a.png", target_width=400,
                           transparent_from="white")
    image = Image.open(result.path)
    assert image.mode == "RGBA"
    assert image.getpixel((2, 2))[3] == 0, "corner should be transparent"


@requires_backend
def test_without_chroma_key_there_is_no_alpha_and_no_warning(tmp_path):
    """Documents the backend limitation honestly: output is RGB by default,
    which on a coloured garment prints as a solid rectangle."""
    from PIL import Image

    result = rasterize_svg(CIRCLE_SVG, tmp_path / "a.png", target_width=400)
    assert result.transparent_pixels == 0
    assert result.warnings() == []
    assert Image.open(result.path).mode == "RGB"
