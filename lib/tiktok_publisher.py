#!/usr/bin/env python3
"""
tiktok_publisher.py — TikTok video publishing via the Content Posting API
===========================================================================
Implements the real Direct Post flow. Replaces the TODO stub that
previously lived in social_clips/auto_publisher.py:192.

API surface: TikTok Content Posting API, Direct Post
(https://open.tiktokapis.com), requiring the `video.publish` scope.

Upload strategy: **chunked binary upload**. Unlike Instagram's single-shot
resumable upload, TikTok requires the caller to pre-declare the total file
size and chunk count at init time, then PUT each chunk with an explicit
`Content-Range` header. Chunk math is not optional — get the byte ranges
wrong and the upload silently fails to assemble.

Flow:
    1. init_post()      POST https://open.tiktokapis.com/v2/post/publish/video/init/
                         -> {publish_id, upload_url}  (upload_url valid 1 hour)
    2. upload_video()   PUT  {upload_url}, one call per chunk, Content-Range set
    3. (TikTok processes asynchronously; there is no documented status-poll
       endpoint equivalent to Instagram's container status — publish_id is
       the only handle returned to the caller.)

Required environment (.env):
    TIKTOK_ACCESS_TOKEN   user access token with video.publish scope

Hard prerequisites (cannot be worked around in code):
    - Unaudited apps (the default until TikTok reviews yours) can only post
      to accounts set to PRIVATE visibility ("SELF_ONLY") — PUBLIC posting
      requires App Review. [Per TikTok's own docs, verified 2026-08-20]
    - `privacy_level` must be one of the values TikTok's own
      /creator_info/query/ endpoint returns as available for that specific
      account — passing an unsupported value is rejected, not silently
      downgraded.
    - Each user access_token is rate-limited to 6 requests/minute.

Docs:
    https://developers.tiktok.com/doc/content-posting-api-reference-direct-post
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any

# ── Constants ─────────────────────────────────────────────────────────────────

API_HOST = "https://open.tiktokapis.com"
INIT_ENDPOINT = f"{API_HOST}/v2/post/publish/video/init/"
CREATOR_INFO_ENDPOINT = f"{API_HOST}/v2/post/publish/creator_info/query/"

#: TikTok's documented chunking rule: each chunk must be 5-64 MB, except the
#: final chunk (which may be smaller), and a max of 1000 chunks per upload.
MIN_CHUNK_BYTES = 5 * 1024 * 1024
MAX_CHUNK_BYTES = 64 * 1024 * 1024
#: Single-chunk uploads are allowed and simplest; only chunk when the file
#: exceeds this, matching TikTok's own documented threshold for when
#: multi-chunk becomes mandatory rather than optional.
SINGLE_CHUNK_LIMIT_BYTES = 64 * 1024 * 1024

MAX_TITLE_CHARS = 2200  # UTF-16 runes per TikTok's docs; treated as chars here
HTTP_TIMEOUT_SEC = 120

VALID_PRIVACY_LEVELS = frozenset({
    "PUBLIC_TO_EVERYONE", "MUTUAL_FOLLOW_FRIENDS",
    "FOLLOWER_OF_CREATOR", "SELF_ONLY",
})


class TikTokError(RuntimeError):
    """A publish attempt failed. `permanent` gates whether retrying is useful."""

    def __init__(self, message: str, *, code: str | None = None,
                 permanent: bool = False) -> None:
        super().__init__(message)
        self.code = code
        self.permanent = permanent


@dataclass(frozen=True)
class PublishResult:
    """Outcome of a successful init+upload. TikTok processes asynchronously —
    this does NOT mean the post is live yet, only that TikTok accepted the
    upload for processing."""
    publish_id: str
    chunks_uploaded: int


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
        raise TikTokError(f"network error contacting TikTok: {e.reason}") from e

    if not body.strip():
        return {}
    try:
        return json.loads(body)
    except json.JSONDecodeError as e:
        raise TikTokError(f"non-JSON response from TikTok: {body[:300]}") from e


def _error_from_body(raw: str, *, fallback: str) -> TikTokError:
    try:
        parsed = json.loads(raw)
        err = parsed.get("error", {})
    except json.JSONDecodeError:
        return TikTokError(f"{fallback}: {raw[:300]}")

    code = err.get("code")
    message = err.get("message", fallback)
    # Config/permission problems will not resolve on retry; rate limits will.
    permanent = code in ("access_token_invalid", "scope_not_authorized",
                         "spam_risk_too_many_posts", "unaudited_client_can_only_post_private")
    return TikTokError(f"[{code}] {message}", code=code, permanent=permanent)


# ── Config ────────────────────────────────────────────────────────────────────

def _token() -> str:
    token = os.environ.get("TIKTOK_ACCESS_TOKEN", "").strip()
    if not token:
        raise TikTokError("TIKTOK_ACCESS_TOKEN not set", permanent=True)
    return token


# ── Pre-flight validation ─────────────────────────────────────────────────────

def validate_clip(clip_path: Path) -> int:
    """Returns the file size in bytes. Raises TikTokError for anything TikTok
    will reject outright."""
    if not clip_path.exists():
        raise TikTokError(f"clip not found: {clip_path}", permanent=True)
    size = clip_path.stat().st_size
    if size == 0:
        raise TikTokError(f"clip is 0 bytes: {clip_path}", permanent=True)
    if clip_path.suffix.lower() not in (".mp4", ".mov", ".webm"):
        raise TikTokError(
            f"unsupported container '{clip_path.suffix}' — TikTok accepts "
            f".mp4/.mov/.webm", permanent=True)
    return size


def validate_title(title: str) -> str:
    if len(title) > MAX_TITLE_CHARS:
        title = title[:MAX_TITLE_CHARS - 1].rstrip() + "…"
    return title


def _chunk_plan(size: int) -> tuple[int, int]:
    """Returns (chunk_size, total_chunk_count) per TikTok's documented rule:
    single chunk if the file fits, otherwise split at MAX_CHUNK_BYTES."""
    if size <= SINGLE_CHUNK_LIMIT_BYTES:
        return size, 1
    chunk_size = MAX_CHUNK_BYTES
    total_chunks = (size + chunk_size - 1) // chunk_size
    return chunk_size, total_chunks


# ── Creator info (required before choosing privacy_level) ───────────────────

def query_creator_info() -> dict[str, Any]:
    """
    TikTok requires checking which privacy_level values and posting
    permissions are actually available for THIS account before init — an
    unaudited app's account may be restricted to SELF_ONLY, and passing a
    privacy_level TikTok didn't offer is rejected outright.
    """
    token = _token()
    body = _request(
        CREATOR_INFO_ENDPOINT, method="POST",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json; charset=UTF-8",
        },
    )
    if "data" not in body:
        raise TikTokError(f"creator_info query returned no data: {body}")
    return body["data"]


def _resolve_privacy_level(requested: str) -> str:
    info = query_creator_info()
    available = set(info.get("privacy_level_options") or [])
    if requested in available:
        return requested
    if available:
        raise TikTokError(
            f"privacy_level '{requested}' not available for this account — "
            f"TikTok offers: {sorted(available)}", permanent=True)
    # No options returned at all — fall back to the caller's request and let
    # TikTok's own init call be the source of truth, rather than blocking
    # on a possibly-incomplete creator_info response.
    return requested


# ── Publish steps ─────────────────────────────────────────────────────────────

def init_post(title: str, size: int, *, privacy_level: str = "SELF_ONLY",
             disable_duet: bool = False, disable_stitch: bool = False,
             disable_comment: bool = False) -> tuple[str, str, int, int]:
    """
    Step 1 — declare the post and file shape. Returns
    (publish_id, upload_url, chunk_size, total_chunk_count).

    Defaults to SELF_ONLY (private) rather than public — an unaudited app
    can only post privately anyway (TikTok rejects PUBLIC_TO_EVERYONE
    otherwise), and defaulting to the safer option means a misconfigured
    caller fails closed, not open.
    """
    if privacy_level not in VALID_PRIVACY_LEVELS:
        raise TikTokError(
            f"invalid privacy_level '{privacy_level}' — must be one of "
            f"{sorted(VALID_PRIVACY_LEVELS)}", permanent=True)

    token = _token()
    chunk_size, total_chunks = _chunk_plan(size)

    payload = json.dumps({
        "post_info": {
            "title": title,
            "privacy_level": privacy_level,
            "disable_duet": disable_duet,
            "disable_stitch": disable_stitch,
            "disable_comment": disable_comment,
        },
        "source_info": {
            "source": "FILE_UPLOAD",
            "video_size": size,
            "chunk_size": chunk_size,
            "total_chunk_count": total_chunks,
        },
    }).encode("utf-8")

    body = _request(
        INIT_ENDPOINT, method="POST", data=payload,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json; charset=UTF-8",
        },
    )
    data = body.get("data") or {}
    publish_id = data.get("publish_id")
    upload_url = data.get("upload_url")
    if not publish_id or not upload_url:
        raise TikTokError(f"init returned no publish_id/upload_url: {body}")
    return str(publish_id), str(upload_url), chunk_size, total_chunks


def upload_video(upload_url: str, clip_path: Path, *,
                 chunk_size: int, total_chunks: int) -> int:
    """
    Step 2 — PUT the file to upload_url, one call per chunk with an explicit
    Content-Range header. Returns the number of chunks uploaded.

    TikTok's `upload_url` is a fully-formed, single-use URL (not the API
    host) — no Authorization header is sent here, matching TikTok's own
    documented example (the URL itself carries the auth context).
    """
    size = clip_path.stat().st_size
    data = clip_path.read_bytes()

    content_type = {
        ".mp4": "video/mp4", ".mov": "video/quicktime", ".webm": "video/webm",
    }[clip_path.suffix.lower()]

    for i in range(total_chunks):
        start = i * chunk_size
        end = min(start + chunk_size, size) - 1
        chunk = data[start:end + 1]
        _request(
            upload_url, method="PUT", data=chunk,
            headers={
                "Content-Type": content_type,
                "Content-Length": str(len(chunk)),
                "Content-Range": f"bytes {start}-{end}/{size}",
            },
        )
    return total_chunks


# ── Orchestration ─────────────────────────────────────────────────────────────

def publish_video(clip_path: Path, title: str, *,
                  privacy_level: str = "SELF_ONLY",
                  disable_duet: bool = False,
                  disable_stitch: bool = False,
                  disable_comment: bool = False,
                  log=print) -> PublishResult:
    """
    Publish a local video file to TikTok via Direct Post. Raises TikTokError.

    ⚠ TikTok processes the upload asynchronously after this returns — a
    successful return means TikTok ACCEPTED the file, not that it is live.
    There is no documented status-poll endpoint to confirm final publish
    state; check the account directly to confirm.

    ⚠ Defaults to SELF_ONLY (private) — see init_post()'s docstring. Pass
    privacy_level="PUBLIC_TO_EVERYONE" explicitly only once the TikTok app
    has passed App Review; otherwise TikTok rejects the request.
    """
    clip_path = Path(clip_path)
    size = validate_clip(clip_path)
    title = validate_title(title)
    privacy_level = _resolve_privacy_level(privacy_level)

    publish_id, upload_url, chunk_size, total_chunks = init_post(
        title, size, privacy_level=privacy_level,
        disable_duet=disable_duet, disable_stitch=disable_stitch,
        disable_comment=disable_comment,
    )
    log(f"[tiktok] publish_id {publish_id} — {total_chunks} chunk(s) planned")

    chunks_uploaded = upload_video(
        upload_url, clip_path, chunk_size=chunk_size, total_chunks=total_chunks)
    log(f"[tiktok] uploaded {chunks_uploaded} chunk(s), "
        f"{size / 1024 / 1024:.1f} MB total — processing async")

    return PublishResult(publish_id=publish_id, chunks_uploaded=chunks_uploaded)


# ── CLI (diagnostics only — never posts) ──────────────────────────────────────

if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser(
        description="TikTok publisher diagnostics. Does NOT post.")
    ap.add_argument("--check", action="store_true",
                    help="verify credentials and show available privacy levels")
    ap.add_argument("--validate", metavar="CLIP",
                    help="check a clip against TikTok limits without uploading")
    args = ap.parse_args()

    try:
        if args.check:
            info = query_creator_info()
            print(f"credentials OK — privacy options: "
                  f"{info.get('privacy_level_options')}")
        if args.validate:
            size = validate_clip(Path(args.validate))
            chunk_size, total_chunks = _chunk_plan(size)
            print(f"{args.validate}: {size / 1024 / 1024:.1f} MB, "
                  f"would upload as {total_chunks} chunk(s)")
        if not args.check and not args.validate:
            ap.print_help()
    except TikTokError as exc:
        raise SystemExit(f"FAILED: {exc}")
