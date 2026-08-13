#!/usr/bin/env python3
"""
instagram_publisher.py — Instagram Reels publishing via the Instagram Platform API
=================================================================================
Implements the real Content Publishing flow. Replaces the TODO stub that
previously lived in social_clips/auto_publisher.py:154.

API surface: **Instagram API with Instagram Login** (host graph.instagram.com).
Chosen over the Facebook Login path because it does NOT require the Instagram
account to be linked to a Facebook Page, and needs fewer permissions.

Upload strategy: **resumable binary upload**. Meta accepts raw bytes posted to
rupload.facebook.com, so the clip is sent straight from local disk. There is no
public-URL / CDN requirement. (The older `video_url=` flow, where Meta cURLs a
public HTTPS URL, is deliberately not used — it would require hosting unreleased
content publicly.)

Flow:
    1. create_container()   POST  /{IG_USER_ID}/media?upload_type=resumable
    2. upload_video()       POST  rupload.facebook.com/ig-api-upload/{version}/{container_id}
    3. wait_for_container() GET   /{container_id}?fields=status_code,status
    4. publish_container()  POST  /{IG_USER_ID}/media_publish

Required environment (.env):
    IG_ACCESS_TOKEN   long-lived Instagram user token (60-day lifetime)
    IG_USER_ID        Instagram professional account ID (NOT the @handle)

Optional:
    IG_GRAPH_VERSION  defaults to GRAPH_VERSION below
    IG_APP_SECRET     only needed by exchange_for_long_lived_token()

Hard prerequisites (cannot be worked around in code):
    - The Instagram account must be **Business or Creator**. Personal accounts
      cannot publish through this API under any configuration.
    - A Meta app must exist with the Instagram product added, and the account
      owner must hold an app role (Administrator/Developer/Tester) if the app is
      in Development Mode. Apps serving only businesses you own do not need
      App Review.

⚠ TOKEN EXPIRY — the single most likely cause of silent daemon death.
   A long-lived token lasts 60 days. It can be refreshed (see refresh_token())
   only while it is still valid AND at least 24h old. Once it lapses past 60
   days there is NO programmatic recovery — a human must re-run the OAuth
   consent screen. Refresh on a schedule around day 45-50 and alarm on failure.

Docs:
    https://developers.facebook.com/docs/instagram-platform/content-publishing/
    https://developers.facebook.com/docs/instagram-platform/instagram-graph-api/reference/ig-user/media/
"""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any

# ── Constants ─────────────────────────────────────────────────────────────────

#: Pin the Graph version explicitly. Never call unversioned — Meta defaults
#: unversioned calls to the oldest live version, which rotates without notice.
GRAPH_VERSION = "v26.0"

GRAPH_HOST = "https://graph.instagram.com"
RUPLOAD_HOST = "https://rupload.facebook.com/ig-api-upload"

#: Meta's documented guidance: "query a container's status once per minute,
#: for no more than 5 minutes." Typical Reel transcode is 5-60s.
POLL_INTERVAL_SEC = 15
POLL_TIMEOUT_SEC = 300

#: Reels media limits (Meta-documented).
MAX_FILE_BYTES = 300 * 1024 * 1024   # 300 MB
MIN_DURATION_SEC = 3
MAX_DURATION_SEC = 15 * 60           # 15 minutes
MAX_CAPTION_CHARS = 2200
MAX_HASHTAGS = 30

HTTP_TIMEOUT_SEC = 120

#: Error subcodes worth naming, so failures are actionable instead of numeric.
#: Source: developers.facebook.com/docs/instagram-platform/instagram-graph-api/reference/error-codes
ERROR_HINTS: dict[int, str] = {
    9004: "media could not be fetched from the URI (video_url unreachable/not public)",
    9007: "published before the container finished processing — poll until FINISHED",
    352: "unsupported video format — must be MOV/MP4, H.264/HEVC, AAC audio",
    36001: "unsupported image format",
    25: "the Instagram account is restricted or checkpointed",
    9: "daily publish limit reached for this account",
    4: "spam-protection restriction — back off and retry later",
    200: "missing permission (commonly ads_management when the Page role came "
         "via Business Manager)",
}

#: Container status_code values. Exhaustive per Meta docs.
STATUS_IN_PROGRESS = "IN_PROGRESS"
STATUS_FINISHED = "FINISHED"
STATUS_ERROR = "ERROR"
STATUS_EXPIRED = "EXPIRED"
STATUS_PUBLISHED = "PUBLISHED"


class InstagramError(RuntimeError):
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
    media_id: str
    container_id: str
    quota_used: int
    quota_total: int


# ── HTTP plumbing ─────────────────────────────────────────────────────────────

def _request(url: str, *, method: str = "GET",
             data: bytes | None = None,
             headers: dict[str, str] | None = None,
             timeout: int = HTTP_TIMEOUT_SEC) -> dict[str, Any]:
    """
    Issue a request and return the decoded JSON body.

    Meta returns structured errors with a non-2xx status, so HTTPError bodies
    are parsed rather than discarded — the subcode is the only actionable part.
    """
    req = urllib.request.Request(url, data=data, method=method,
                                 headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", errors="replace")
        raise _error_from_body(raw, fallback=f"HTTP {e.code}") from e
    except urllib.error.URLError as e:
        # Network-level: transient by definition, so not permanent.
        raise InstagramError(f"network error contacting Meta: {e.reason}") from e

    if not body.strip():
        return {}
    try:
        return json.loads(body)
    except json.JSONDecodeError as e:
        raise InstagramError(f"non-JSON response from Meta: {body[:300]}") from e


def _error_from_body(raw: str, *, fallback: str) -> InstagramError:
    """Turn a Meta error envelope into an InstagramError with a usable hint."""
    try:
        err = json.loads(raw).get("error", {})
    except json.JSONDecodeError:
        return InstagramError(f"{fallback}: {raw[:300]}")

    code = err.get("code")
    subcode = err.get("error_subcode")
    message = err.get("message", fallback)
    hint = ERROR_HINTS.get(code) or ERROR_HINTS.get(subcode)

    # Config/account problems will not fix themselves on retry; rate limits will.
    permanent = code in (352, 36001, 200, 25)

    detail = f"[{code}/{subcode}] {message}"
    if hint:
        detail = f"{detail} — {hint}"
    return InstagramError(detail, code=code, subcode=subcode, permanent=permanent)


def _post_form(url: str, params: dict[str, str]) -> dict[str, Any]:
    payload = urllib.parse.urlencode(params).encode("utf-8")
    return _request(url, method="POST", data=payload,
                    headers={"Content-Type": "application/x-www-form-urlencoded"})


# ── Config ────────────────────────────────────────────────────────────────────

def _config() -> tuple[str, str, str]:
    """Return (token, ig_user_id, graph_version). Raises if unconfigured."""
    token = os.environ.get("IG_ACCESS_TOKEN", "").strip()
    user_id = os.environ.get("IG_USER_ID", "").strip()
    version = os.environ.get("IG_GRAPH_VERSION", "").strip() or GRAPH_VERSION

    if not token:
        raise InstagramError("IG_ACCESS_TOKEN not set", permanent=True)
    if not user_id:
        raise InstagramError(
            "IG_USER_ID not set — this is the numeric Instagram professional "
            "account ID, not the @handle", permanent=True)
    return token, user_id, version


# ── Pre-flight validation ─────────────────────────────────────────────────────

def validate_clip(clip_path: Path) -> None:
    """
    Reject clips Meta will refuse, before burning an API call.

    Only checks what is knowable without ffprobe. Duration and codec are not
    verified here — a duration/codec violation surfaces as error 352 at publish.
    """
    if not clip_path.exists():
        raise InstagramError(f"clip not found: {clip_path}", permanent=True)

    size = clip_path.stat().st_size
    if size == 0:
        raise InstagramError(f"clip is 0 bytes: {clip_path}", permanent=True)
    if size > MAX_FILE_BYTES:
        raise InstagramError(
            f"clip is {size / 1024 / 1024:.1f} MB — Reels limit is 300 MB",
            permanent=True)
    if clip_path.suffix.lower() not in (".mp4", ".mov"):
        raise InstagramError(
            f"unsupported container '{clip_path.suffix}' — Reels accept .mp4/.mov",
            permanent=True)


def validate_caption(caption: str) -> str:
    """Trim a caption to Meta's limits rather than letting the API reject it."""
    if len(caption) > MAX_CAPTION_CHARS:
        caption = caption[:MAX_CAPTION_CHARS - 1].rstrip() + "…"
    if caption.count("#") > MAX_HASHTAGS:
        raise InstagramError(
            f"caption has {caption.count('#')} hashtags — Instagram allows "
            f"{MAX_HASHTAGS}", permanent=True)
    return caption


# ── Quota ─────────────────────────────────────────────────────────────────────

def check_quota() -> tuple[int, int]:
    """
    Return (used, total) publishes in the rolling 24h window.

    The total is read at runtime and never hardcoded: Meta's own docs currently
    contradict themselves (the Content Publishing guide says 100, the
    content_publishing_limit reference says 50), so the API is the only
    trustworthy source.
    """
    token, user_id, version = _config()
    url = (f"{GRAPH_HOST}/{version}/{user_id}/content_publishing_limit"
           f"?fields=config,quota_usage&access_token={urllib.parse.quote(token)}")
    body = _request(url)
    rows = body.get("data") or [{}]
    row = rows[0]
    used = int(row.get("quota_usage", 0))
    total = int(row.get("config", {}).get("quota_total", 0))
    return used, total


# ── Publish steps ─────────────────────────────────────────────────────────────

def create_container(caption: str, *, share_to_feed: bool = True,
                     is_ai_generated: bool = False) -> str:
    """
    Step 1 — create a resumable REELS container. Returns the container ID.

    `video_url` is deliberately omitted; passing `upload_type=resumable` tells
    Meta to expect the bytes via rupload instead of fetching a public URL.
    """
    token, user_id, version = _config()
    params = {
        "media_type": "REELS",
        "upload_type": "resumable",
        "caption": caption,
        "share_to_feed": "true" if share_to_feed else "false",
        "access_token": token,
    }
    if is_ai_generated:
        params["is_ai_generated"] = "true"

    body = _post_form(f"{GRAPH_HOST}/{version}/{user_id}/media", params)
    container_id = body.get("id")
    if not container_id:
        raise InstagramError(f"container create returned no id: {body}")
    return str(container_id)


def upload_video(container_id: str, clip_path: Path) -> None:
    """
    Step 2 — upload the raw bytes to rupload.

    Two details that break first attempts:
      - the auth scheme is `OAuth`, NOT `Bearer`
      - `offset` and `file_size` are required headers, and the body is the raw
        file (not multipart/form-data)
    """
    token, _, version = _config()
    size = clip_path.stat().st_size
    payload = clip_path.read_bytes()

    _request(
        f"{RUPLOAD_HOST}/{version}/{container_id}",
        method="POST",
        data=payload,
        headers={
            "Authorization": f"OAuth {token}",
            "offset": "0",
            "file_size": str(size),
            "Content-Type": "application/octet-stream",
        },
    )


def container_status(container_id: str) -> tuple[str, str]:
    """Return (status_code, status). `status` carries the subcode on ERROR."""
    token, _, version = _config()
    url = (f"{GRAPH_HOST}/{version}/{container_id}"
           f"?fields=status_code,status&access_token={urllib.parse.quote(token)}")
    body = _request(url)
    return str(body.get("status_code", "")), str(body.get("status", ""))


def wait_for_container(container_id: str, *,
                       timeout: int = POLL_TIMEOUT_SEC,
                       interval: int = POLL_INTERVAL_SEC,
                       log=print) -> None:
    """
    Step 3 — block until the container reports FINISHED.

    Publishing before FINISHED is error 9007 and is the single most common
    integration bug, so this is not optional.
    """
    deadline = time.monotonic() + timeout
    while True:
        code, detail = container_status(container_id)

        if code == STATUS_FINISHED:
            return
        if code == STATUS_ERROR:
            raise InstagramError(
                f"transcode failed for container {container_id}: {detail}")
        if code == STATUS_EXPIRED:
            raise InstagramError(
                f"container {container_id} expired unpublished (24h limit)",
                permanent=True)
        if code == STATUS_PUBLISHED:
            return  # already live; treat as success rather than double-publishing

        if time.monotonic() >= deadline:
            raise InstagramError(
                f"container {container_id} still {code or 'unknown'} after "
                f"{timeout}s — giving up")

        log(f"[instagram] container {container_id}: {code or 'unknown'}; "
            f"waiting {interval}s")
        time.sleep(interval)


def publish_container(container_id: str) -> str:
    """Step 4 — publish a FINISHED container. Returns the published media ID."""
    token, user_id, version = _config()
    body = _post_form(
        f"{GRAPH_HOST}/{version}/{user_id}/media_publish",
        {"creation_id": container_id, "access_token": token},
    )
    media_id = body.get("id")
    if not media_id:
        raise InstagramError(f"media_publish returned no id: {body}")
    return str(media_id)


# ── Orchestration ─────────────────────────────────────────────────────────────

def publish_reel(clip_path: Path, caption: str, *,
                 share_to_feed: bool = True,
                 is_ai_generated: bool = False,
                 log=print) -> PublishResult:
    """
    Publish a local video file as an Instagram Reel. Raises InstagramError.

    ⚠ This posts publicly and immediately. There is no dry-run mode and no
    unpublish API — the only way to remove a Reel afterwards is manually in
    the Instagram app.
    """
    clip_path = Path(clip_path)
    validate_clip(clip_path)
    caption = validate_caption(caption)

    used, total = check_quota()
    if total and used >= total:
        raise InstagramError(
            f"publish quota exhausted ({used}/{total} in the rolling 24h "
            f"window) — capacity frees 24h after each individual post")
    log(f"[instagram] quota {used}/{total}")

    container_id = create_container(caption, share_to_feed=share_to_feed,
                                    is_ai_generated=is_ai_generated)
    log(f"[instagram] container {container_id} created")

    upload_video(container_id, clip_path)
    log(f"[instagram] uploaded {clip_path.stat().st_size / 1024 / 1024:.1f} MB")

    wait_for_container(container_id, log=log)
    media_id = publish_container(container_id)
    log(f"[instagram] published media {media_id}")

    return PublishResult(media_id=media_id, container_id=container_id,
                         quota_used=used + 1, quota_total=total)


# ── Token lifecycle ───────────────────────────────────────────────────────────

def refresh_token() -> tuple[str, int]:
    """
    Refresh a long-lived token. Returns (new_token, expires_in_seconds).

    Constraints: the current token must be at least 24 HOURS OLD and NOT YET
    EXPIRED. Past 60 days there is no programmatic recovery — a human has to
    re-run the OAuth consent screen.

    The caller is responsible for persisting the new token; this function does
    not write .env, because a partial write here would lock the account out.
    """
    token, _, _ = _config()
    url = (f"{GRAPH_HOST}/refresh_access_token?grant_type=ig_refresh_token"
           f"&access_token={urllib.parse.quote(token)}")
    body = _request(url)
    new_token = body.get("access_token")
    if not new_token:
        raise InstagramError(f"refresh returned no token: {body}")
    return str(new_token), int(body.get("expires_in", 0))


def exchange_for_long_lived_token(short_lived_token: str) -> tuple[str, int]:
    """
    One-time: swap a 1-hour token for a 60-day one. Server-side only — this
    call carries the app secret and must never run in a browser.
    """
    secret = os.environ.get("IG_APP_SECRET", "").strip()
    if not secret:
        raise InstagramError("IG_APP_SECRET not set", permanent=True)
    url = (f"{GRAPH_HOST}/access_token?grant_type=ig_exchange_token"
           f"&client_secret={urllib.parse.quote(secret)}"
           f"&access_token={urllib.parse.quote(short_lived_token)}")
    body = _request(url)
    new_token = body.get("access_token")
    if not new_token:
        raise InstagramError(f"exchange returned no token: {body}")
    return str(new_token), int(body.get("expires_in", 0))


# ── CLI (diagnostics only — never posts) ──────────────────────────────────────

if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser(
        description="Instagram publisher diagnostics. Does NOT post.")
    ap.add_argument("--check", action="store_true",
                    help="verify credentials and show remaining publish quota")
    ap.add_argument("--validate", metavar="CLIP",
                    help="check a clip against Reels limits without uploading")
    args = ap.parse_args()

    try:
        if args.check:
            u, t = check_quota()
            print(f"credentials OK — quota {u}/{t} used in the last 24h")
        if args.validate:
            validate_clip(Path(args.validate))
            print(f"{args.validate}: passes size/container checks "
                  f"(codec + duration still verified server-side)")
        if not args.check and not args.validate:
            ap.print_help()
    except InstagramError as exc:
        raise SystemExit(f"FAILED: {exc}")
