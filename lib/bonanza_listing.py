#!/usr/bin/env python3
"""
bonanza_listing.py — Bonanza marketplace listing integration via REST API
==========================================================================
Bonanza is a marketplace alternative to eBay supporting both vintage and modern
goods. Uses their official REST API with OAuth 2.0.

API Surface: Bonanza REST API v2
- https://api.bonanza.com/api_ref/

Flow:
    1. Authenticate via OAuth 2.0 (client credentials or user login)
    2. Create listings via POST /listings/create
    3. Update listings via POST /listings/update
    4. Delete listings via POST /listings/delete
    5. Fetch inventory via GET /listings

Required environment (.env):
    BONANZA_APP_ID        OAuth app ID (client_id)
    BONANZA_APP_SECRET    OAuth app secret
    BONANZA_ACCESS_TOKEN  OAuth access token (long-lived or refresh token flow)
    BONANZA_USER_ID       Optional - seller account ID for multi-account setups

Bonanza API docs:
    https://api.bonanza.com/api_ref/
    https://bonanza.com/sell
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional
from decimal import Decimal

# ── Constants ─────────────────────────────────────────────────────────────────

BONANZA_API_HOST = "https://api.bonanza.com"
BONANZA_API_VERSION = "v2"
BONANZA_API_BASE = f"{BONANZA_API_HOST}/api_ref/{BONANZA_API_VERSION}"

HTTP_TIMEOUT_SEC = 60


class BonanzaError(RuntimeError):
    """A Bonanza API call failed."""

    def __init__(
        self,
        message: str,
        *,
        code: int | None = None,
        step: str = "api_call",
        permanent: bool = False,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.step = step
        self.permanent = permanent


@dataclass(frozen=True)
class BonanzaListing:
    """A Bonanza marketplace listing."""

    title: str
    description: str
    price: Decimal
    quantity: int
    sku: str
    category_id: str  # Bonanza category ID
    condition: str = "new"  # new | like_new | good | acceptable
    tags: list[str] = field(default_factory=list)  # max 5 tags
    image_urls: list[str] = field(default_factory=list)  # primary image first
    shipping_weight_lbs: Optional[Decimal] = None
    returns_accepted: bool = True

    def validate(self) -> None:
        """Pre-flight validation before creating on Bonanza."""
        if len(self.title) < 5 or len(self.title) > 120:
            raise BonanzaError(
                f"title must be 5-120 chars, got {len(self.title)}", step="validation"
            )

        if self.price <= 0:
            raise BonanzaError(
                f"price must be > 0, got {self.price}", step="validation"
            )

        if self.quantity < 1:
            raise BonanzaError(
                f"quantity must be >= 1, got {self.quantity}", step="validation"
            )

        if self.condition not in ("new", "like_new", "good", "acceptable"):
            raise BonanzaError(
                f"condition must be new|like_new|good|acceptable, got {self.condition}",
                step="validation",
            )

        if len(self.tags) > 5:
            raise BonanzaError(
                f"max 5 tags, got {len(self.tags)}", step="validation"
            )

        if len(self.image_urls) > 12:
            raise BonanzaError(
                f"max 12 images, got {len(self.image_urls)}", step="validation"
            )


@dataclass(frozen=True)
class BonanzaListingResult:
    """Outcome of a successful listing creation."""

    listing_id: str
    url: str


# ── HTTP plumbing ─────────────────────────────────────────────────────────────


def _request(
    method: str,
    path: str,
    *,
    data: dict[str, Any] | None = None,
    token: str = "",
    timeout: int = HTTP_TIMEOUT_SEC,
) -> dict[str, Any]:
    """Make an authenticated request to Bonanza API."""
    url = f"{BONANZA_API_BASE}{path}"

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}" if token else "",
    }

    body = json.dumps(data).encode() if data else None

    try:
        req = urllib.request.Request(
            url,
            data=body,
            method=method,
            headers={k: v for k, v in headers.items() if v},
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            response_body = resp.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", errors="replace")
        try:
            error_data = json.loads(raw)
            message = error_data.get("error_message", raw[:300])
        except json.JSONDecodeError:
            message = raw[:300]
        permanent = e.code in (401, 403, 400)  # auth/permission/invalid request
        raise BonanzaError(
            f"HTTP {e.code}: {message}",
            code=e.code,
            step="api_call",
            permanent=permanent,
        ) from e
    except urllib.error.URLError as e:
        raise BonanzaError(
            f"network error: {e.reason}", step="api_call", permanent=False
        ) from e

    if not response_body.strip():
        return {}

    try:
        return json.loads(response_body)
    except json.JSONDecodeError as e:
        raise BonanzaError(
            f"non-JSON response: {response_body[:300]}", step="api_call"
        ) from e


# ── Configuration ─────────────────────────────────────────────────────────────


def _get_token() -> str:
    """Retrieve Bonanza access token from environment."""
    token = os.environ.get("BONANZA_ACCESS_TOKEN", "").strip()
    if not token:
        raise BonanzaError(
            "BONANZA_ACCESS_TOKEN not set", step="config", permanent=True
        )
    return token


# ── Listing operations ────────────────────────────────────────────────────────


class BonanzaListingClient:
    """Client for creating and managing Bonanza listings."""

    def __init__(
        self, access_token: str, transport=None, sandbox: bool = False
    ) -> None:
        if not access_token:
            raise BonanzaError(
                "access_token required", step="config", permanent=True
            )
        self.token = access_token
        self.transport = transport or _request
        self.sandbox = sandbox
        self.base_url = (
            f"{BONANZA_API_HOST}/api_ref/sandbox" if sandbox else BONANZA_API_BASE
        )

    def create_listing(
        self,
        listing: BonanzaListing,
        *,
        dry_run: bool = True,
    ) -> BonanzaListingResult | dict[str, Any]:
        """Create a listing on Bonanza."""
        listing.validate()

        payload = {
            "title": listing.title,
            "description": listing.description,
            "price": float(listing.price),
            "quantity": listing.quantity,
            "sku": listing.sku,
            "category_id": listing.category_id,
            "condition": listing.condition,
            "tags": listing.tags,
            "shipping_weight_lbs": (
                float(listing.shipping_weight_lbs)
                if listing.shipping_weight_lbs
                else None
            ),
            "returns_accepted": listing.returns_accepted,
            "images": listing.image_urls,
        }

        if dry_run:
            return {
                "status": "dry_run",
                "payload": payload,
                "note": "would create listing on Bonanza",
            }

        try:
            response = self.transport(
                "POST",
                "/listings/create",
                data=payload,
                token=self.token,
            )

            if "error" in response:
                raise BonanzaError(
                    response.get("error_message", "unknown error"),
                    code=400,
                    step="create_listing",
                )

            listing_id = response.get("listing_id")
            if not listing_id:
                raise BonanzaError(
                    "no listing_id in response", step="create_listing"
                )

            return BonanzaListingResult(
                listing_id=listing_id,
                url=f"https://bonanza.com/listings/{listing_id}",
            )
        except BonanzaError:
            raise
        except Exception as e:
            raise BonanzaError(
                f"listing creation failed: {e}", step="create_listing"
            ) from e

    def update_listing(
        self, listing_id: str, updates: dict[str, Any], *, dry_run: bool = True
    ) -> dict[str, Any]:
        """Update an existing Bonanza listing."""
        if dry_run:
            return {
                "status": "dry_run",
                "listing_id": listing_id,
                "updates": updates,
                "note": "would update listing on Bonanza",
            }

        try:
            response = self.transport(
                "POST",
                f"/listings/{listing_id}/update",
                data=updates,
                token=self.token,
            )

            if "error" in response:
                raise BonanzaError(
                    response.get("error_message", "unknown error"),
                    code=400,
                    step="update_listing",
                )

            return response
        except BonanzaError:
            raise
        except Exception as e:
            raise BonanzaError(
                f"listing update failed: {e}", step="update_listing"
            ) from e

    def delete_listing(self, listing_id: str, *, dry_run: bool = True) -> dict[str, Any]:
        """Delete a Bonanza listing."""
        if dry_run:
            return {
                "status": "dry_run",
                "listing_id": listing_id,
                "note": "would delete listing on Bonanza",
            }

        try:
            response = self.transport(
                "POST",
                f"/listings/{listing_id}/delete",
                token=self.token,
            )

            if "error" in response:
                raise BonanzaError(
                    response.get("error_message", "unknown error"),
                    code=400,
                    step="delete_listing",
                )

            return response
        except BonanzaError:
            raise
        except Exception as e:
            raise BonanzaError(
                f"listing deletion failed: {e}", step="delete_listing"
            ) from e


if __name__ == "__main__":
    import sys

    token = os.environ.get("BONANZA_ACCESS_TOKEN")
    if not token:
        print("ERROR: BONANZA_ACCESS_TOKEN not set")
        sys.exit(1)

    client = BonanzaListingClient(token)
    print("Bonanza client initialized successfully")
