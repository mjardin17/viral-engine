"""Tests for the eBay half of scripts/listing_service.py — the localhost
HTTP bridge that lets boss-listers-mvp (Node) call lib/ebay_listing.py (the
canonical, tested client) without a second implementation in JavaScript.

Renamed from scripts/ebay_listing_service.py, which now also serves Etsy
(see tests/etsy/test_listing_service_etsy.py for that half) — a file named
ebay_* serving two platforms was a naming lie waiting to mislead a reader.

Emphasis: the per-platform live-publish safety design, and that a partial
publish failure (an offer exists but isn't live) maps to 409, not a plain
502 that a caller might treat as safe-to-retry-from-scratch.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import pytest
from fastapi.testclient import TestClient

import lib.ebay_listing as ebay_listing
from scripts.listing_service import create_app

VALID_PRODUCT = {
    "sku": "CARD-001",
    "title": "2024 Topps Chrome Refractor #123",
    "description": "Near mint, stored in a sleeve.",
    "price": "24.99",
    "category_id": "261328",
    "quantity": 1,
    "condition": "USED_EXCELLENT",
    "image_urls": ["https://example.com/front.jpg"],
}

VALID_POLICIES = {
    "fulfillment_policy_id": "FUL-1",
    "payment_policy_id": "PAY-1",
    "return_policy_id": "RET-1",
    "merchant_location_key": "LOC-1",
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
    def transport(method, url, headers, body):
        if not responses:
            raise AssertionError(f"unexpected extra call: {method} {url}")
        return responses.pop(0)
    return transport


@pytest.fixture
def dry_run_client():
    """Service started WITHOUT --allow-live — the default posture."""
    app = create_app(armed_platforms=frozenset())
    return TestClient(app)


@pytest.fixture
def live_client(monkeypatch):
    """Service started with eBay armed via --allow-live and a known
    shared secret. Etsy stays unarmed — proves arming is per-platform."""
    monkeypatch.setenv("LISTING_SERVICE_TOKEN", "test-secret-123")
    app = create_app(armed_platforms=frozenset({"ebay"}))
    return TestClient(app)


# --------------------------------------------------------------------------
# Health
# --------------------------------------------------------------------------

def test_health_reports_live_publish_state(dry_run_client, live_client):
    assert dry_run_client.get("/health").json()["live_publish_allowed"] == {"ebay": False, "etsy": False}
    assert live_client.get("/health").json()["live_publish_allowed"] == {"ebay": True, "etsy": False}


# --------------------------------------------------------------------------
# Dry run (the only mode reachable without --allow-live)
# --------------------------------------------------------------------------

def test_dry_run_never_touches_the_network(dry_run_client, monkeypatch):
    def explode(*a, **k):
        raise AssertionError("dry run must not make a network call")
    monkeypatch.setattr(ebay_listing, "_requests_transport", explode)

    res = dry_run_client.post("/ebay/create-listing", json={
        "access_token": "fake-token",
        "product": VALID_PRODUCT,
        "policies": VALID_POLICIES,
        "dry_run": True,
    })

    assert res.status_code == 200
    body = res.json()
    assert body["ok"] is True
    assert body["dry_run"] is True
    assert body["published"] is False
    assert "inventory_item" in body["payloads"] and "offer" in body["payloads"]


def test_dry_run_is_the_default_when_flag_omitted(dry_run_client, monkeypatch):
    monkeypatch.setattr(
        ebay_listing, "_requests_transport",
        lambda *a, **k: (_ for _ in ()).throw(AssertionError("no network expected")),
    )

    res = dry_run_client.post("/ebay/create-listing", json={
        "access_token": "fake-token",
        "product": VALID_PRODUCT,
        "policies": VALID_POLICIES,
        # dry_run omitted entirely
    })

    assert res.status_code == 200
    assert res.json()["dry_run"] is True


def test_stringified_false_does_not_arm_a_live_publish(dry_run_client):
    """StrictBool must reject the JSON string "false" rather than coerce it —
    a JS caller that accidentally stringified the flag must not silently
    arm real publishing."""
    res = dry_run_client.post("/ebay/create-listing", json={
        "access_token": "fake-token",
        "product": VALID_PRODUCT,
        "policies": VALID_POLICIES,
        "dry_run": "false",
    })
    assert res.status_code == 422  # Pydantic schema rejection, not a publish


def test_validation_error_maps_to_400_before_any_network_call(dry_run_client, monkeypatch):
    monkeypatch.setattr(
        ebay_listing, "_requests_transport",
        lambda *a, **k: (_ for _ in ()).throw(AssertionError("no network expected")),
    )
    bad_product = {**VALID_PRODUCT, "category_id": ""}

    res = dry_run_client.post("/ebay/create-listing", json={
        "access_token": "fake-token",
        "product": bad_product,
        "policies": VALID_POLICIES,
        "dry_run": True,
    })

    assert res.status_code == 400
    assert res.json()["detail"]["code"] == "validation_error"


# --------------------------------------------------------------------------
# Live-publish gates — a dry_run_client (no --allow-live) must refuse ALL
# live requests regardless of what else is in the body.
# --------------------------------------------------------------------------

def test_live_request_refused_when_service_not_armed(dry_run_client):
    res = dry_run_client.post("/ebay/create-listing", json={
        "access_token": "fake-token",
        "product": VALID_PRODUCT,
        "policies": VALID_POLICIES,
        "dry_run": False,
        "confirm": "PUBLISH_LIVE",
    })
    assert res.status_code == 403
    assert res.json()["detail"]["code"] == "live_publish_disabled"


def test_live_request_refused_without_confirm_literal(live_client):
    res = live_client.post(
        "/ebay/create-listing",
        headers={"X-Listing-Service-Token": "test-secret-123"},
        json={
            "access_token": "fake-token",
            "product": VALID_PRODUCT,
            "policies": VALID_POLICIES,
            "dry_run": False,
            "confirm": "yes please",  # wrong literal
        },
    )
    assert res.status_code == 400
    assert res.json()["detail"]["code"] == "confirmation_required"


def test_live_request_refused_without_shared_secret_header(live_client):
    res = live_client.post("/ebay/create-listing", json={
        "access_token": "fake-token",
        "product": VALID_PRODUCT,
        "policies": VALID_POLICIES,
        "dry_run": False,
        "confirm": "PUBLISH_LIVE",
        # no X-Listing-Service-Token header
    })
    assert res.status_code == 401
    assert res.json()["detail"]["code"] == "unauthorized"


def test_live_request_refused_with_wrong_shared_secret(live_client):
    res = live_client.post(
        "/ebay/create-listing",
        headers={"X-Listing-Service-Token": "wrong-token"},
        json={
            "access_token": "fake-token",
            "product": VALID_PRODUCT,
            "policies": VALID_POLICIES,
            "dry_run": False,
            "confirm": "PUBLISH_LIVE",
        },
    )
    assert res.status_code == 401


def test_all_three_gates_satisfied_reaches_ebay(live_client, monkeypatch):
    """Positive control: with every gate correctly satisfied, the request
    really does proceed to a (faked) network call — proves the gates aren't
    accidentally blocking a legitimate, fully-authorized live request too."""
    transport = make_fake_transport([
        FakeResponse(204),
        FakeResponse(201, {"offerId": "OFFER-9"}),
        FakeResponse(200, {"listingId": "LISTING-42"}),
    ])
    monkeypatch.setattr(ebay_listing, "_requests_transport", transport)

    res = live_client.post(
        "/ebay/create-listing",
        headers={"X-Listing-Service-Token": "test-secret-123"},
        json={
            "access_token": "fake-token",
            "product": VALID_PRODUCT,
            "policies": VALID_POLICIES,
            "dry_run": False,
            "confirm": "PUBLISH_LIVE",
        },
    )

    assert res.status_code == 200
    body = res.json()
    assert body["published"] is True
    assert body["listing_id"] == "LISTING-42"


# --------------------------------------------------------------------------
# Error mapping — the 409 case is the important one: it means real,
# recoverable state exists on eBay's side and must not look like a plain
# retryable failure.
# --------------------------------------------------------------------------

def test_orphaned_offer_maps_to_409_not_a_plain_502(live_client, monkeypatch):
    transport = make_fake_transport([
        FakeResponse(204),
        FakeResponse(201, {"offerId": "OFFER-7"}),
        FakeResponse(400, {"errors": [{"message": "missing shipping policy"}]}),
    ])
    monkeypatch.setattr(ebay_listing, "_requests_transport", transport)

    res = live_client.post(
        "/ebay/create-listing",
        headers={"X-Listing-Service-Token": "test-secret-123"},
        json={
            "access_token": "fake-token",
            "product": VALID_PRODUCT,
            "policies": VALID_POLICIES,
            "dry_run": False,
            "confirm": "PUBLISH_LIVE",
        },
    )

    assert res.status_code == 409
    detail = res.json()["detail"]
    assert detail["code"] == "offer_created_not_published"
    assert detail["offer_id"] == "OFFER-7"


def test_auth_failure_maps_to_401(live_client, monkeypatch):
    transport = make_fake_transport([FakeResponse(401, {"errors": ["bad token"]})])
    monkeypatch.setattr(ebay_listing, "_requests_transport", transport)

    res = live_client.post(
        "/ebay/create-listing",
        headers={"X-Listing-Service-Token": "test-secret-123"},
        json={
            "access_token": "expired-token",
            "product": VALID_PRODUCT,
            "policies": VALID_POLICIES,
            "dry_run": False,
            "confirm": "PUBLISH_LIVE",
        },
    )

    assert res.status_code == 401
    assert res.json()["detail"]["code"] == "ebay_auth_failed"


def test_generic_ebay_failure_with_no_offer_maps_to_502(live_client, monkeypatch):
    transport = make_fake_transport([FakeResponse(500, {"errors": ["server error"]})])
    monkeypatch.setattr(ebay_listing, "_requests_transport", transport)

    res = live_client.post(
        "/ebay/create-listing",
        headers={"X-Listing-Service-Token": "test-secret-123"},
        json={
            "access_token": "fake-token",
            "product": VALID_PRODUCT,
            "policies": VALID_POLICIES,
            "dry_run": False,
            "confirm": "PUBLISH_LIVE",
        },
    )

    assert res.status_code == 502
    assert res.json()["detail"]["code"] == "ebay_error"


# --------------------------------------------------------------------------
# Secrets must never appear in a response body
# --------------------------------------------------------------------------

def test_access_token_never_echoed_back_in_any_response(dry_run_client, monkeypatch):
    monkeypatch.setattr(
        ebay_listing, "_requests_transport",
        lambda *a, **k: (_ for _ in ()).throw(AssertionError("no network expected")),
    )
    secret_token = "v^1.1#SUPER-SECRET-TOKEN-VALUE"

    res = dry_run_client.post("/ebay/create-listing", json={
        "access_token": secret_token,
        "product": VALID_PRODUCT,
        "policies": VALID_POLICIES,
        "dry_run": True,
    })

    assert secret_token not in res.text
