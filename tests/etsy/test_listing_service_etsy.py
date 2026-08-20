"""Tests for the Etsy half of scripts/listing_service.py.

Emphasis: draft creation stays free/safe even with dry_run:false (only
ACTIVATING costs money and needs the live gates), and that arming is
per-platform — arming eBay must not accidentally arm Etsy or vice versa.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import pytest
from fastapi.testclient import TestClient

import lib.etsy_listing as etsy_listing
from scripts.listing_service import create_app

VALID_PRODUCT = {
    "sku": "CARD-VINTAGE-001",
    "title": "1986 Vintage Topps Card",
    "description": "Genuine vintage trading card, stored in a sleeve.",
    "price": "24.99",
    "who_made": "someone_else",
    "when_made": "1980s",
    "taxonomy_id": "1234",
    "shipping_profile_id": "SHIP-1",
    "images": [{"local_path": "/tmp/card.jpg"}],
}


class FakeResponse:
    def __init__(self, status_code: int, payload=None):
        self.status_code = status_code
        self._payload = payload

    def json(self):
        if self._payload is None:
            raise ValueError("no json body")
        return self._payload


def make_fake_transport(responses):
    def transport(method, url, headers, body_kind, body):
        if not responses:
            raise AssertionError(f"unexpected extra call: {method} {url}")
        return responses.pop(0)
    return transport


@pytest.fixture
def dry_run_client():
    app = create_app(armed_platforms=frozenset())
    return TestClient(app)


@pytest.fixture
def etsy_live_client(monkeypatch):
    """Etsy armed, eBay NOT armed — proves per-platform arming both ways."""
    monkeypatch.setenv("LISTING_SERVICE_TOKEN", "test-secret-123")
    app = create_app(armed_platforms=frozenset({"etsy"}))
    return TestClient(app)


# --------------------------------------------------------------------------
# Draft creation is free/safe — stays reachable even with dry_run:false
# --------------------------------------------------------------------------

def test_draft_target_state_never_requires_live_gates(dry_run_client, monkeypatch):
    """dry_run:false + target_state:draft must succeed WITHOUT the service
    being armed at all — creating a draft is free and buyer-invisible,
    unlike eBay where dry_run:false always means "really publish"."""
    transport = make_fake_transport([
        FakeResponse(201, {"listing_id": "L123"}),
        FakeResponse(201, {"image_id": "IMG1"}),
    ])
    monkeypatch.setattr(etsy_listing, "_requests_transport", transport)

    res = dry_run_client.post("/etsy/create-listing", json={
        "access_token": "fake-token",
        "shop_id": "SHOP1",
        "api_key": "apikey",
        "product": VALID_PRODUCT,
        "dry_run": False,
        "target_state": "draft",
    })

    assert res.status_code == 200
    body = res.json()
    assert body["listing_id"] == "L123"
    assert body["published"] is False


def test_dry_run_true_never_touches_the_network(dry_run_client, monkeypatch):
    monkeypatch.setattr(
        etsy_listing, "_requests_transport",
        lambda *a, **k: (_ for _ in ()).throw(AssertionError("no network expected")),
    )

    res = dry_run_client.post("/etsy/create-listing", json={
        "access_token": "fake-token",
        "shop_id": "SHOP1",
        "api_key": "apikey",
        "product": VALID_PRODUCT,
        "dry_run": True,
    })

    assert res.status_code == 200
    assert res.json()["dry_run"] is True


def test_default_target_state_is_draft(dry_run_client, monkeypatch):
    monkeypatch.setattr(
        etsy_listing, "_requests_transport",
        lambda *a, **k: (_ for _ in ()).throw(AssertionError("no network expected")),
    )
    res = dry_run_client.post("/etsy/create-listing", json={
        "access_token": "fake-token",
        "shop_id": "SHOP1",
        "api_key": "apikey",
        "product": VALID_PRODUCT,
        # dry_run and target_state both omitted
    })
    assert res.status_code == 200
    assert res.json()["dry_run"] is True


# --------------------------------------------------------------------------
# Activation IS the money/live boundary — needs all three gates
# --------------------------------------------------------------------------

def test_activation_refused_when_etsy_not_armed(dry_run_client):
    res = dry_run_client.post("/etsy/create-listing", json={
        "access_token": "fake-token",
        "shop_id": "SHOP1",
        "api_key": "apikey",
        "product": VALID_PRODUCT,
        "dry_run": False,
        "target_state": "active",
        "confirm": "PUBLISH_LIVE",
    })
    assert res.status_code == 403
    assert res.json()["detail"]["code"] == "live_publish_disabled"


def test_activation_refused_without_confirm_literal(etsy_live_client):
    res = etsy_live_client.post(
        "/etsy/create-listing",
        headers={"X-Listing-Service-Token": "test-secret-123"},
        json={
            "access_token": "fake-token",
            "shop_id": "SHOP1",
            "api_key": "apikey",
            "product": VALID_PRODUCT,
            "dry_run": False,
            "target_state": "active",
            "confirm": "yes please",
        },
    )
    assert res.status_code == 400
    assert res.json()["detail"]["code"] == "confirmation_required"


def test_activation_refused_without_shared_secret(etsy_live_client):
    res = etsy_live_client.post("/etsy/create-listing", json={
        "access_token": "fake-token",
        "shop_id": "SHOP1",
        "api_key": "apikey",
        "product": VALID_PRODUCT,
        "dry_run": False,
        "target_state": "active",
        "confirm": "PUBLISH_LIVE",
    })
    assert res.status_code == 401


def test_all_gates_satisfied_reaches_etsy(etsy_live_client, monkeypatch):
    transport = make_fake_transport([
        FakeResponse(201, {"listing_id": "L123"}),
        FakeResponse(201, {"image_id": "IMG1"}),
        FakeResponse(200, {"state": "active"}),
    ])
    monkeypatch.setattr(etsy_listing, "_requests_transport", transport)

    res = etsy_live_client.post(
        "/etsy/create-listing",
        headers={"X-Listing-Service-Token": "test-secret-123"},
        json={
            "access_token": "fake-token",
            "shop_id": "SHOP1",
            "api_key": "apikey",
            "product": VALID_PRODUCT,
            "dry_run": False,
            "target_state": "active",
            "confirm": "PUBLISH_LIVE",
        },
    )
    assert res.status_code == 200
    assert res.json()["published"] is True


# --------------------------------------------------------------------------
# Per-platform arming — the property that motivated this whole rename
# --------------------------------------------------------------------------

def test_arming_etsy_does_not_arm_ebay(etsy_live_client):
    """etsy_live_client arms ONLY etsy — an eBay live request must still
    be refused, proving arming doesn't leak across platforms."""
    res = etsy_live_client.post(
        "/ebay/create-listing",
        headers={"X-Listing-Service-Token": "test-secret-123"},
        json={
            "access_token": "fake-token",
            "product": {
                "sku": "X", "title": "X", "description": "X", "price": "9.99",
                "category_id": "1", "image_urls": ["https://example.com/a.jpg"],
            },
            "policies": {
                "fulfillment_policy_id": "F", "payment_policy_id": "P",
                "return_policy_id": "R", "merchant_location_key": "L",
            },
            "dry_run": False,
            "confirm": "PUBLISH_LIVE",
        },
    )
    assert res.status_code == 403
    assert res.json()["detail"]["code"] == "live_publish_disabled"


# --------------------------------------------------------------------------
# Error mapping — orphaned draft states map to distinct 409 codes
# --------------------------------------------------------------------------

def test_image_upload_failure_maps_to_409_images_incomplete(etsy_live_client, monkeypatch):
    transport = make_fake_transport([
        FakeResponse(201, {"listing_id": "L123"}),
        FakeResponse(500, {"error": "upload failed"}),
    ])
    monkeypatch.setattr(etsy_listing, "_requests_transport", transport)

    res = etsy_live_client.post(
        "/etsy/create-listing",
        headers={"X-Listing-Service-Token": "test-secret-123"},
        json={
            "access_token": "fake-token",
            "shop_id": "SHOP1",
            "api_key": "apikey",
            "product": VALID_PRODUCT,
            "dry_run": False,
            "target_state": "active",
            "confirm": "PUBLISH_LIVE",
        },
    )
    assert res.status_code == 409
    detail = res.json()["detail"]
    assert detail["code"] == "draft_created_images_incomplete"
    assert detail["listing_id"] == "L123"


def test_activation_failure_maps_to_409_not_activated(etsy_live_client, monkeypatch):
    transport = make_fake_transport([
        FakeResponse(201, {"listing_id": "L123"}),
        FakeResponse(201, {"image_id": "IMG1"}),
        FakeResponse(400, {"error": "missing return policy"}),
    ])
    monkeypatch.setattr(etsy_listing, "_requests_transport", transport)

    res = etsy_live_client.post(
        "/etsy/create-listing",
        headers={"X-Listing-Service-Token": "test-secret-123"},
        json={
            "access_token": "fake-token",
            "shop_id": "SHOP1",
            "api_key": "apikey",
            "product": VALID_PRODUCT,
            "dry_run": False,
            "target_state": "active",
            "confirm": "PUBLISH_LIVE",
        },
    )
    assert res.status_code == 409
    detail = res.json()["detail"]
    assert detail["code"] == "draft_created_not_activated"
    assert detail["listing_id"] == "L123"


def test_validation_error_maps_to_400(dry_run_client, monkeypatch):
    monkeypatch.setattr(
        etsy_listing, "_requests_transport",
        lambda *a, **k: (_ for _ in ()).throw(AssertionError("no network expected")),
    )
    bad_product = {**VALID_PRODUCT, "taxonomy_id": ""}
    res = dry_run_client.post("/etsy/create-listing", json={
        "access_token": "fake-token",
        "shop_id": "SHOP1",
        "api_key": "apikey",
        "product": bad_product,
        "dry_run": True,
    })
    assert res.status_code == 400
    assert res.json()["detail"]["code"] == "validation_error"


def test_access_token_never_echoed_in_any_response(dry_run_client, monkeypatch):
    monkeypatch.setattr(
        etsy_listing, "_requests_transport",
        lambda *a, **k: (_ for _ in ()).throw(AssertionError("no network expected")),
    )
    secret_token = "etsy-secret-abc123"
    res = dry_run_client.post("/etsy/create-listing", json={
        "access_token": secret_token,
        "shop_id": "SHOP1",
        "api_key": "apikey",
        "product": VALID_PRODUCT,
        "dry_run": True,
    })
    assert secret_token not in res.text
