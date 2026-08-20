#!/usr/bin/env python3
"""
facebook_publisher.py — Facebook Page video publishing via the Graph API
===========================================================================
Implements the real resumable upload flow. Replaces the TODO stub that
previously lived in social_clips/auto_publisher.py:210.

API surface: Facebook Graph API resumable upload protocol
(https://graph.facebook.com), pinned to v25.0 explicitly — never call
unversioned, Meta defaults unversioned calls to the oldest live version.

Flow:
    1. start_upload_session()  POST /{APP_ID}/uploads?file_name&file_length&file_type
                                -> upload session ID
    2. upload_file()           POST /upload:{SESSION_ID}, binary body,
                                file_offset header -> file handle (h)
    3. publish_video()         POST /{PAGE_ID}/videos, multipart form:
                                fbuploader_video_file_chunk=<handle>, title,
                                description -> video ID

Required environment (.env):
    FB_ACCESS_TOKEN   PAGE access token (not a user token — must belong to
                       someone with CREATE_CONTENT permission on the page)
    FB_PAGE_ID        numeric Facebook Page ID
    FB_APP_ID         the Meta app ID that owns the upload session

Hard prerequisites (cannot be worked around in code):
    - The token must be a Page access token, not a user token — pages_show_list,
      pages_read_engagement, and pages_manage_posts must all be granted.
    - Uploading requires CREATE_CONTENT permission on the target Page.

Docs:
    https://developers.facebook.com/docs/video-api/guides/publishing
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any

# ── Constants ─────────────────────────────────────────────────────────────────

GRAPH_VERSION = "v25.0"
GRAPH_HOST = "https://graph.facebook.com"

HTTP_TIMEOUT_SEC = 180  # video bodies can be large; longer than IG/TikTok


class FacebookError(RuntimeError):
    """A publish attempt failed. `permanent` gates whether retrying is useful."""

    def __init__(self, message: str, *, code: int | None = None,
                 subcode: int | None = None, permanent: bool = False) -> None:
        super().__init__(message)
        self.code = code
        self.subcode = subcode
        self.permanent = permanent


@dataclass(frozen=True)
class PublishResult:
    """Outcome of a successful publish."""
    video_id: str
    upload_session_id: str


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
        raise FacebookError(f"network error contacting Meta: {e.reason}") from e

    if not body.strip():
        return {}
    try:
        return json.loads(body)
    except json.JSONDecodeError as e:
        raise FacebookError(f"non-JSON response from Meta: {body[:300]}") from e


def _error_from_body(raw: str, *, fallback: str) -> FacebookError:
    try:
        err = json.loads(raw).get("error", {})
    except json.JSONDecodeError:
        return FacebookError(f"{fallback}: {raw[:300]}")

    code = err.get("code")
    subcode = err.get("error_subcode")
    message = err.get("message", fallback)
    # Permission/config errors won't fix themselves on retry.
    permanent = code in (190, 200, 10)  # invalid token, permission, disabled feature
    return FacebookError(f"[{code}/{subcode}] {message}",
                         code=code, subcode=subcode, permanent=permanent)


# ── Config ────────────────────────────────────────────────────────────────────

def _config() -> tuple[str, str, str]:
    """Return (token, page_id, app_id). Raises if unconfigured."""
    token = os.environ.get("FB_ACCESS_TOKEN", "").strip()
    page_id = os.environ.get("FB_PAGE_ID", "").strip()
    app_id = os.environ.get("FB_APP_ID", "").strip()

    if not token:
        raise FacebookError("FB_ACCESS_TOKEN not set", permanent=True)
    if not page_id:
        raise FacebookError("FB_PAGE_ID not set", permanent=True)
    if not app_id:
        raise FacebookError(
            "FB_APP_ID not set — needed to open the resumable upload "
            "session, separate from the page access token", permanent=True)
    return token, page_id, app_id


# ── Pre-flight validation ─────────────────────────────────────────────────────

def validate_clip(clip_path: Path) -> int:
    """Returns the file size in bytes."""
    if not clip_path.exists():
        raise FacebookError(f"clip not found: {clip_path}", permanent=True)
    size = clip_path.stat().st_size
    if size == 0:
        raise FacebookError(f"clip is 0 bytes: {clip_path}", permanent=True)
    if clip_path.suffix.lower() not in (".mp4", ".mov"):
        raise FacebookError(
            f"unsupported container '{clip_path.suffix}' — Facebook video "
            f"upload accepts .mp4/.mov", permanent=True)
    return size


# ── Publish steps ─────────────────────────────────────────────────────────────

def start_upload_session(clip_path: Path, size: int) -> str:
    """Step 1 — declare the upcoming upload. Returns the upload session ID."""
    token, _, app_id = _config()
    content_type = "video/mp4" if clip_path.suffix.lower() == ".mp4" else "video/quicktime"

    params = urllib.parse.urlencode({
        "file_name": clip_path.name,
        "file_length": size,
        "file_type": content_type,
        "access_token": token,
    })
    body = _request(f"{GRAPH_HOST}/{GRAPH_VERSION}/{app_id}/uploads?{params}",
                    method="POST")
    session_id = body.get("id")
    if not session_id:
        raise FacebookError(f"upload session start returned no id: {body}")
    return str(session_id)


def upload_file(upload_session_id: str, clip_path: Path) -> str:
    """Step 2 — upload the raw bytes. Returns the file handle (h) needed to
    publish. Single-shot (file_offset=0) — Meta's resumable protocol allows
    multi-part resume on failure, which is not implemented here; a failed
    upload simply needs to be retried from the start."""
    token, _, _ = _config()
    data = clip_path.read_bytes()

    body = _request(
        f"{GRAPH_HOST}/{GRAPH_VERSION}/upload:{upload_session_id}",
        method="POST", data=data,
        headers={
            "Authorization": f"OAuth {token}",
            "file_offset": "0",
        },
    )
    handle = body.get("h")
    if not handle:
        raise FacebookError(f"file upload returned no handle: {body}")
    return str(handle)


def publish_video(file_handle: str, title: str, description: str) -> str:
    """Step 3 — attach the uploaded file handle to a new Page video post.
    Returns the published video ID."""
    token, page_id, _ = _config()
    payload = urllib.parse.urlencode({
        "access_token": token,
        "title": title,
        "description": description,
        "fbuploader_video_file_chunk": file_handle,
    }).encode("utf-8")

    body = _request(
        f"{GRAPH_HOST}/{GRAPH_VERSION}/{page_id}/videos",
        method="POST", data=payload,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    video_id = body.get("id")
    if not video_id:
        raise FacebookError(f"video publish returned no id: {body}")
    return str(video_id)


# ── Orchestration ─────────────────────────────────────────────────────────────

def publish_page_video(clip_path: Path, title: str, description: str, *,
                       log=print) -> PublishResult:
    """
    Publish a local video file to the configured Facebook Page. Raises
    FacebookError.

    ⚠ This posts publicly and immediately once Meta finishes processing —
    there is no dry-run mode built into the Graph API for this endpoint.
    """
    clip_path = Path(clip_path)
    size = validate_clip(clip_path)

    session_id = start_upload_session(clip_path, size)
    log(f"[facebook] upload session {session_id} started, "
        f"{size / 1024 / 1024:.1f} MB")

    handle = upload_file(session_id, clip_path)
    log(f"[facebook] file uploaded, handle acquired")

    video_id = publish_video(handle, title, description)
    log(f"[facebook] published video {video_id}")

    return PublishResult(video_id=video_id, upload_session_id=session_id)


# ── CLI (diagnostics only — never posts) ──────────────────────────────────────

if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser(
        description="Facebook publisher diagnostics. Does NOT post.")
    ap.add_argument("--check", action="store_true",
                    help="verify required env vars are set")
    ap.add_argument("--validate", metavar="CLIP",
                    help="check a clip against upload requirements without uploading")
    args = ap.parse_args()

    try:
        if args.check:
            _config()
            print("credentials present — FB_ACCESS_TOKEN, FB_PAGE_ID, FB_APP_ID all set")
        if args.validate:
            size = validate_clip(Path(args.validate))
            print(f"{args.validate}: {size / 1024 / 1024:.1f} MB, passes format check")
        if not args.check and not args.validate:
            ap.print_help()
    except FacebookError as exc:
        raise SystemExit(f"FAILED: {exc}")
