#!/usr/bin/env python3
"""
pinterest_publisher.py — Pinterest image Pin publishing via API v5
===========================================================================
Implements the real base64-embedded image pin flow. Replaces the TODO stub
that previously lived in social_clips/auto_publisher.py:256.

API surface: Pinterest API v5 (https://api.pinterest.com/v5), OAuth2.

This pipeline's Pinterest asset is a static thumbnail JPG
(social_clips/clip_generator.py's make_pinterest_pin(), 1000x1500), not a
video — so this is deliberately the SIMPLE Pinterest flow. Image pins can
embed the image directly as base64 in the same request that creates the
pin; there is no separate media-registration/upload/poll cycle like video
pins require (that three-step flow exists in this project's git history
from an earlier draft that assumed a video asset — wrong for this call
site, replaced here).

Flow (one real step):
    create_pin()   POST /v5/pins  {board_id, title, description,
                    media_source: {source_type: "image_base64",
                    content_type: "image/jpeg", data: <base64>}}

Required environment (.env):
    PINTEREST_ACCESS_TOKEN   OAuth2 user token
    PINTEREST_BOARD_ID       target board to pin to

Limits (Pinterest-documented):
    Title: 100 characters. Description: 800 characters.
    Base64 image payload: Pinterest does not publish a hard byte cap for
    image_base64 specifically, but the pipeline's thumbnails are small
    (1000x1500 JPG) and well within any reasonable request-body limit.

Docs:
    https://developers.pinterest.com/docs/api/v5/
"""

from __future__ import annotations

import base64
import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any

# ── Constants ─────────────────────────────────────────────────────────────────

API_HOST = "https://api.pinterest.com/v5"

MAX_TITLE_CHARS = 100
MAX_DESCRIPTION_CHARS = 800

HTTP_TIMEOUT_SEC = 60


class PinterestError(RuntimeError):
    """A publish attempt failed. `permanent` gates whether retrying is useful."""

    def __init__(self, message: str, *, code: int | None = None,
                 permanent: bool = False) -> None:
        super().__init__(message)
        self.code = code
        self.permanent = permanent


@dataclass(frozen=True)
class PublishResult:
    """Outcome of a successful publish."""
    pin_id: str


# ── HTTP plumbing ─────────────────────────────────────────────────────────────

def _request(url: str, *, method: str = "GET",
             data: bytes | None = None,
             headers: dict[str, str] | None = None,
             timeout: int = HTTP_TIMEOUT_SEC) -> dict[str, Any]:
    req = urllib.request.Request(url, data=data, method=method,
                                 headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", errors="replace")
        raise _error_from_body(raw, fallback=f"HTTP {e.code}") from e
    except urllib.error.URLError as e:
        raise PinterestError(f"network error contacting Pinterest: {e.reason}") from e

    if not body.strip():
        return {}
    try:
        return json.loads(body)
    except json.JSONDecodeError as e:
        raise PinterestError(f"non-JSON response from Pinterest: {body[:300]}") from e


def _error_from_body(raw: str, *, fallback: str) -> PinterestError:
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return PinterestError(f"{fallback}: {raw[:300]}")

    code = parsed.get("code")
    message = parsed.get("message", fallback)
    # Auth/permission/validation errors won't resolve on retry.
    permanent = code in (1, 2, 3, 7, 8)
    return PinterestError(f"[{code}] {message}", code=code, permanent=permanent)


# ── Config ────────────────────────────────────────────────────────────────────

def _config() -> tuple[str, str]:
    """Return (token, board_id). Raises if unconfigured."""
    token = os.environ.get("PINTEREST_ACCESS_TOKEN", "").strip()
    board_id = os.environ.get("PINTEREST_BOARD_ID", "").strip()

    if not token:
        raise PinterestError("PINTEREST_ACCESS_TOKEN not set", permanent=True)
    if not board_id:
        raise PinterestError("PINTEREST_BOARD_ID not set", permanent=True)
    return token, board_id


# ── Pre-flight validation ─────────────────────────────────────────────────────

def validate_image(image_path: Path) -> bytes:
    """Returns the raw image bytes."""
    if not image_path.exists():
        raise PinterestError(f"image not found: {image_path}", permanent=True)
    data = image_path.read_bytes()
    if len(data) == 0:
        raise PinterestError(f"image is 0 bytes: {image_path}", permanent=True)
    if image_path.suffix.lower() not in (".jpg", ".jpeg", ".png"):
        raise PinterestError(
            f"unsupported image format '{image_path.suffix}' — Pinterest "
            f"accepts .jpg/.jpeg/.png", permanent=True)
    return data


def validate_title(title: str) -> str:
    if len(title) > MAX_TITLE_CHARS:
        title = title[:MAX_TITLE_CHARS - 1].rstrip() + "…"
    return title


def validate_description(description: str) -> str:
    if len(description) > MAX_DESCRIPTION_CHARS:
        description = description[:MAX_DESCRIPTION_CHARS - 1].rstrip() + "…"
    return description


def _content_type_for(image_path: Path) -> str:
    return "image/png" if image_path.suffix.lower() == ".png" else "image/jpeg"


# ── Publish ───────────────────────────────────────────────────────────────────

def create_pin(image_path: Path, title: str, description: str, *,
              board_id: str | None = None) -> str:
    """One-shot pin creation with the image embedded as base64. Returns the
    pin ID."""
    token, configured_board_id = _config()
    board_id = board_id or configured_board_id

    image_bytes = validate_image(image_path)
    encoded = base64.b64encode(image_bytes).decode("ascii")

    payload = json.dumps({
        "board_id": board_id,
        "title": title,
        "description": description,
        "media_source": {
            "source_type": "image_base64",
            "content_type": _content_type_for(image_path),
            "data": encoded,
        },
    }).encode("utf-8")

    body = _request(
        f"{API_HOST}/pins", method="POST", data=payload,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
    )
    pin_id = body.get("id")
    if not pin_id:
        raise PinterestError(f"pin creation returned no id: {body}")
    return str(pin_id)


# ── Orchestration ─────────────────────────────────────────────────────────────

def publish_pin(image_path: Path, title: str, description: str, *,
                board_id: str | None = None, log=print) -> PublishResult:
    """
    Publish a local image file as a Pinterest Pin. Raises PinterestError.

    ⚠ This posts publicly and immediately — Pinterest has no dry-run mode
    and no unpublish-via-API for this endpoint.
    """
    image_path = Path(image_path)
    title = validate_title(title)
    description = validate_description(description)

    pin_id = create_pin(image_path, title, description, board_id=board_id)
    log(f"[pinterest] published pin {pin_id}")

    return PublishResult(pin_id=pin_id)


# ── CLI (diagnostics only — never posts) ──────────────────────────────────────

if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser(
        description="Pinterest publisher diagnostics. Does NOT post.")
    ap.add_argument("--check", action="store_true",
                    help="verify required env vars are set")
    ap.add_argument("--validate", metavar="IMAGE",
                    help="check an image against Pinterest requirements without posting")
    args = ap.parse_args()

    try:
        if args.check:
            _config()
            print("credentials present — PINTEREST_ACCESS_TOKEN, "
                  "PINTEREST_BOARD_ID both set")
        if args.validate:
            data = validate_image(Path(args.validate))
            print(f"{args.validate}: {len(data) / 1024:.1f} KB, passes format check")
        if not args.check and not args.validate:
            ap.print_help()
    except PinterestError as exc:
        raise SystemExit(f"FAILED: {exc}")
