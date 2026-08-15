"""
tests/storyforge2/test_merch_economics.py -- unit economics recompute.

The point of this module is catching a stored figure that has gone stale
against its own inputs. These tests pin the arithmetic to the real numbers
from the shipped MerchPulse export, so a change to the cost model shows up
as a failure rather than as a quietly different margin.
"""

import pytest

from storyforge2.merch.economics import (
    COST_FIELDS, THIN_MARGIN_PCT, verify_all_products, verify_product_economics,
)

# The one real Product record in merchpulse_full_export.json.
SHIPPED_PRODUCT = {
    "id": "6a7fe39359b3f6eeab033c96",
    "product_type": "tshirt",
    "retail_price": 24.99,
    "blank_cost": 4.5,
    "print_cost": 3,
    "shipping_cost": 4,
    "processing_fee": 0.72,
    "marketplace_fee": 2.5,
    "refund_allowance": 0.75,
    "profit_amount": 9.52,
    "desired_profit": 9.52,
    "margin_pct": 38.1,
}


def test_shipped_product_recomputes_to_its_stored_figures():
    """Regression against the real export: 4.50+3+4+0.72+2.50+0.75 = 15.47,
    24.99-15.47 = 9.52, which is 38.1% of retail."""
    econ = verify_product_economics(SHIPPED_PRODUCT)
    assert econ.unit_cost == 15.47
    assert econ.profit == 9.52
    assert econ.margin_pct == pytest.approx(38.1, abs=0.05)
    assert econ.is_consistent is True
    assert econ.warnings() == []


def test_every_cost_field_is_counted():
    """A component dropped from COST_FIELDS would silently inflate margin."""
    econ = verify_product_economics(SHIPPED_PRODUCT)
    assert set(econ.cost_breakdown) == set(COST_FIELDS)
    assert econ.unit_cost == pytest.approx(sum(econ.cost_breakdown.values()))


def test_stale_stored_profit_is_flagged():
    """The failure this module exists for: blank cost rose, nobody recomputed."""
    stale = {**SHIPPED_PRODUCT, "blank_cost": 6.5}  # +2.00 to cost
    econ = verify_product_economics(stale)
    assert econ.profit == 7.52
    assert econ.is_consistent is False
    drifted = {d.field for d in econ.drift}
    assert "profit_amount" in drifted
    assert any("stale" in w for w in econ.warnings())


def test_stale_stored_margin_is_flagged():
    econ = verify_product_economics({**SHIPPED_PRODUCT, "margin_pct": 55.0})
    assert [d.field for d in econ.drift] == ["margin_pct"]
    assert econ.drift[0].delta == pytest.approx(16.9, abs=0.05)


def test_absent_stored_figures_are_not_treated_as_drift():
    """A product that has never had its figures computed is not stale."""
    inputs_only = {k: v for k, v in SHIPPED_PRODUCT.items()
                   if k not in ("profit_amount", "desired_profit", "margin_pct")}
    econ = verify_product_economics(inputs_only)
    assert econ.is_consistent is True
    assert econ.profit == 9.52


def test_missing_cost_field_is_reported_not_hidden():
    """Counted as zero so the recompute still runs, but the caller is told --
    an absent cost is materially different from a zero one."""
    no_shipping = {k: v for k, v in SHIPPED_PRODUCT.items() if k != "shipping_cost"}
    econ = verify_product_economics(no_shipping)
    assert econ.missing_fields == ("shipping_cost",)
    assert any("shipping_cost" in w for w in econ.warnings())


def test_loss_making_product_is_flagged_as_not_viable():
    econ = verify_product_economics({**SHIPPED_PRODUCT, "retail_price": 12.00})
    assert econ.is_viable is False
    assert econ.profit < 0
    assert any("sells at a loss" in w for w in econ.warnings())


def test_thin_margin_is_warned_but_still_viable():
    """Retail 18.00 on 15.47 cost is 2.53 profit -- positive, but 14%."""
    econ = verify_product_economics({**SHIPPED_PRODUCT, "retail_price": 18.00})
    assert econ.is_viable is True
    assert econ.margin_pct < THIN_MARGIN_PCT
    assert any("thin margin" in w for w in econ.warnings())


def test_healthy_margin_produces_no_warning():
    """Stored figures are dropped alongside the price change -- keeping them
    would (correctly) report drift and mask what this test is checking."""
    repriced = {k: v for k, v in SHIPPED_PRODUCT.items()
                if k not in ("profit_amount", "desired_profit", "margin_pct")}
    econ = verify_product_economics({**repriced, "retail_price": 34.99})
    assert econ.margin_pct > THIN_MARGIN_PCT
    assert econ.warnings() == []


def test_zero_retail_does_not_divide_by_zero():
    econ = verify_product_economics({**SHIPPED_PRODUCT, "retail_price": 0})
    assert econ.margin_pct == 0.0
    assert econ.is_viable is False


def test_non_numeric_cost_is_an_error_not_a_drift():
    """A corrupt record must not be silently coerced into a plausible margin."""
    with pytest.raises(TypeError, match="not numeric"):
        verify_product_economics({**SHIPPED_PRODUCT, "print_cost": "three dollars"})


def test_boolean_cost_is_rejected():
    """bool is an int subclass in Python -- True must not become 1.00."""
    with pytest.raises(TypeError, match="not numeric"):
        verify_product_economics({**SHIPPED_PRODUCT, "print_cost": True})


def test_float_noise_within_half_a_cent_is_not_drift():
    econ = verify_product_economics({**SHIPPED_PRODUCT, "profit_amount": 9.5199999})
    assert econ.is_consistent is True


def test_verify_all_products_preserves_order():
    products = [SHIPPED_PRODUCT, {**SHIPPED_PRODUCT, "id": "second"}]
    assert [e.product_id for e in verify_all_products(products)] == [
        SHIPPED_PRODUCT["id"], "second",
    ]
