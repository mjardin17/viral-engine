"""
tests/storyforge2/test_cover_spec.py — cover spec math validation.

Verify: spine calculations match KDP constants, trim math is correct.
"""

import pytest

from storyforge2.cover.spec import (
    CoverSpecError, compute_cover_spec, get_spine_width_in, inches_to_px,
    PAPER_SPINE_FACTORS, STANDARD_BLEED_IN, MIN_PAGES_FOR_SPINE_TEXT,
)
from storyforge2.brief import TRIM_SIZES


def test_paper_spine_factors_are_kdp():
    """Verify spine factors match Amazon KDP's published constants."""
    assert PAPER_SPINE_FACTORS["white"] == 0.002252
    assert PAPER_SPINE_FACTORS["cream"] == 0.0025
    # Only two paper types in the table — anything else requires override
    assert len(PAPER_SPINE_FACTORS) == 2


def test_standard_bleed_is_1_8_inch():
    """Verify bleed is the print-industry standard 1/8 inch."""
    assert STANDARD_BLEED_IN == 0.125


def test_get_spine_width_white_paper():
    """Spine width calculation for white paper."""
    spine = get_spine_width_in(page_count=200, paper_type="white")
    expected = round(200 * 0.002252, 4)
    assert spine == expected
    assert spine == round(0.4504, 4)  # 200 * 0.002252


def test_get_spine_width_cream_paper():
    """Spine width calculation for cream paper."""
    spine = get_spine_width_in(page_count=100, paper_type="cream")
    expected = round(100 * 0.0025, 4)
    assert spine == expected
    assert spine == 0.25


def test_get_spine_width_with_override():
    """Override allows custom spine factor."""
    spine = get_spine_width_in(page_count=200, paper_type="white", spine_factor_override=0.003)
    expected = round(200 * 0.003, 4)
    assert spine == expected


def test_get_spine_width_rejects_unknown_paper():
    """Unknown paper type raises error unless override provided."""
    with pytest.raises(CoverSpecError):
        get_spine_width_in(page_count=100, paper_type="glossy")


def test_get_spine_width_edge_case_1_page():
    """Edge case: single page book (technically invalid but shouldn't crash)."""
    spine = get_spine_width_in(page_count=1, paper_type="white")
    assert spine == round(1 * 0.002252, 4)


def test_get_spine_width_rejects_zero_pages():
    """Zero pages is invalid."""
    with pytest.raises(CoverSpecError):
        get_spine_width_in(page_count=0, paper_type="white")


def test_compute_cover_spec_6x9():
    """Full cover spec for standard 6x9 trim size."""
    spec = compute_cover_spec(trim_size="6x9", page_count=220, paper_type="white")
    assert spec.trim_width_in == 6.0
    assert spec.trim_height_in == 9.0
    assert spec.page_count == 220
    assert spec.paper_type == "white"
    assert spec.bleed_in == STANDARD_BLEED_IN
    assert spec.include_spine_text is True  # 220 >= MIN_PAGES_FOR_SPINE_TEXT
    # Full wrap = bleed + back + spine + front + bleed
    expected_width = round((2 * 0.125) + (2 * 6.0) + spec.spine_width_in, 4)
    assert spec.full_wrap_width_in == expected_width


def test_compute_cover_spec_small_book_no_spine_text():
    """Small book (< 79 pages) has no spine text."""
    spec = compute_cover_spec(trim_size="6x9", page_count=50)
    assert spec.include_spine_text is False
    # Spine is still calculated, just not labeled


def test_compute_cover_spec_large_book():
    """Large book (350+ pages) has spine text."""
    spec = compute_cover_spec(trim_size="6x9", page_count=350)
    assert spec.include_spine_text is True
    # Spine width should be substantial
    assert spec.spine_width_in > 0.7


def test_compute_cover_spec_all_trim_sizes():
    """All documented trim sizes work without error."""
    for trim_size in TRIM_SIZES:
        spec = compute_cover_spec(trim_size=trim_size, page_count=200)
        assert spec.trim_width_in > 0
        assert spec.trim_height_in > 0


def test_compute_cover_spec_unknown_trim_size():
    """Unknown trim size raises error."""
    with pytest.raises(CoverSpecError):
        compute_cover_spec(trim_size="10x12", page_count=200)


def test_inches_to_px_standard_dpi():
    """Convert inches to pixels at standard 300 DPI."""
    px = inches_to_px(1.0, dpi=300)
    assert px == 300


def test_inches_to_px_fractional():
    """Convert fractional inches."""
    px = inches_to_px(0.125, dpi=300)  # 1/8 inch = standard bleed
    assert px == 38  # 37.5 rounds to even


def test_inches_to_px_various_dpi():
    """DPI parameter works correctly."""
    px_72 = inches_to_px(1.0, dpi=72)
    px_150 = inches_to_px(1.0, dpi=150)
    px_300 = inches_to_px(1.0, dpi=300)
    assert px_72 == 72
    assert px_150 == 150
    assert px_300 == 300
