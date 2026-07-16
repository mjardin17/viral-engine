#!/usr/bin/env python3
"""
fix_yt_titles.py — Bulk-fix YouTube episode titles for Gods & Glory
====================================================================
Scans all videos on the GG channel, finds ones missing the EP### prefix,
shows you the before/after, then updates them with your approval.

Usage:
    python fix_yt_titles.py           # dry run — shows what WOULD change
    python fix_yt_titles.py --go      # actually update titles on YouTube
"""

from __future__ import annotations

import argparse
import pickle
import re
import sys
from pathlib import Path

from google.auth.transport.requests import Request
from googleapiclient.discovery import build

BASE_DIR   = Path(__file__).resolve().parent
TOKEN_PATH = BASE_DIR / "token_gg.pickle"
CREDS_PATH = BASE_DIR / "credentials.json"
SCOPES     = ["https://www.googleapis.com/auth/youtube"]

# Maps episode title keywords → EP number (for already-uploaded episodes)
# Built from the episode JSON scripts
EP_MAP: dict[str, str] = {
    "300 spartans":          "EP001",
    "macedonian king":       "EP002",
    "cannae":                "EP003",
    "mongol war machine":    "EP004",
    "constantinople 1453":   "EP005",
    "pearl harbor":          "EP006",
    "d-day":                 "EP007",
    "stalingrad":            "EP008",
    "iwo jima":              "EP009",
    "vietnam":               "EP010",
    "ia drang":              "EP011",
    "last emperor":          "EP012",
    "crusader kingdoms":     "EP013",
    "waterloo":              "EP014",
    "marathon":              "EP015",
    "agincourt":             "EP016",
    "battle of tours":       "EP017",
    "hastings 1066":         "EP018",
    "kamikaze":              "EP019",
    "siege of vienna":       "EP020",
    "midway":                "EP021",
    "battle of the bulge":   "EP022",
    "operation market garden":"EP023",
    "inchon":                "EP024",
    "yorktown":              "EP025",
}


def get_youtube():
    """Authenticate using token_gg.pickle."""
    if not TOKEN_PATH.exists():
        sys.exit(f"ERROR: {TOKEN_PATH} not found. Run: python channel_uploader.py --channel gg --verify")

    with open(TOKEN_PATH, "rb") as f:
        creds = pickle.load(f)

    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        with open(TOKEN_PATH, "wb") as f:
            pickle.dump(creds, f)

    return build("youtube", "v3", credentials=creds)


def get_channel_videos(youtube) -> list[dict]:
    """Fetch all videos from the authenticated channel."""
    # Get channel ID
    ch_resp = youtube.channels().list(part="id,snippet", mine=True).execute()
    if not ch_resp.get("items"):
        sys.exit("ERROR: No channel found for this token.")
    ch = ch_resp["items"][0]
    ch_id   = ch["id"]
    ch_name = ch["snippet"]["title"]
    print(f"Channel: {ch_name} ({ch_id})")

    # Get uploads playlist
    pl_resp = youtube.channels().list(part="contentDetails", id=ch_id).execute()
    uploads_pl = pl_resp["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]

    # Page through all videos
    videos = []
    page_token = None
    while True:
        resp = youtube.playlistItems().list(
            part="snippet",
            playlistId=uploads_pl,
            maxResults=50,
            pageToken=page_token,
        ).execute()
        for item in resp.get("items", []):
            sn = item["snippet"]
            videos.append({
                "video_id":    sn["resourceId"]["videoId"],
                "title":       sn["title"],
                "description": sn.get("description", ""),
            })
        page_token = resp.get("nextPageToken")
        if not page_token:
            break

    print(f"Found {len(videos)} videos on channel.\n")
    return videos


def detect_ep_num(title: str) -> str | None:
    """Try to detect what EP number this title belongs to."""
    title_lower = title.lower()
    for keyword, ep_num in EP_MAP.items():
        if keyword in title_lower:
            return ep_num
    return None


def clean_title(raw: str, ep_num: str) -> str:
    """Strip any existing malformed EP tags and prepend correct EP### prefix."""
    title = re.sub(r"\|\s*Gods\s*&\s*Glory\s*EP\d+\s*$", "", raw, flags=re.IGNORECASE).strip()
    title = re.sub(r"\bEP\d+\b\s*\|?\s*", "", title, flags=re.IGNORECASE).strip()
    title = title.strip(" |").strip()
    return f"{ep_num} | {title}"


def already_correct(title: str) -> bool:
    """Return True if title already starts with EP### |"""
    return bool(re.match(r"^EP\d{3}\s*\|", title))


def update_title(youtube, video_id: str, new_title: str, description: str) -> None:
    """Update a video's title via YouTube Data API."""
    youtube.videos().update(
        part="snippet",
        body={
            "id": video_id,
            "snippet": {
                "title":       new_title[:100],
                "description": description,
                "categoryId":  "27",
            },
        },
    ).execute()


def main() -> None:
    ap = argparse.ArgumentParser(description="Fix GG YouTube episode titles")
    ap.add_argument("--go", action="store_true", help="Actually update titles (default: dry run)")
    args = ap.parse_args()

    dry_run = not args.go
    if dry_run:
        print("=== DRY RUN — no changes will be made ===\n")
    else:
        print("=== LIVE UPDATE — titles will be changed on YouTube ===\n")

    youtube = get_youtube()
    videos  = get_channel_videos(youtube)

    to_fix    = []
    already_ok = []
    unknown   = []

    for v in videos:
        title = v["title"]
        if already_correct(title):
            already_ok.append(title)
            continue

        ep_num = detect_ep_num(title)
        if ep_num:
            new_title = clean_title(title, ep_num)
            to_fix.append({**v, "ep_num": ep_num, "new_title": new_title})
        else:
            unknown.append(title)

    # ── Report ────────────────────────────────────────────────────────────────
    print(f"✅ Already correct ({len(already_ok)}):")
    for t in already_ok:
        print(f"   {t}")

    print(f"\n🔧 Need fixing ({len(to_fix)}):")
    for v in to_fix:
        print(f"   BEFORE: {v['title']}")
        print(f"   AFTER:  {v['new_title']}")
        print()

    if unknown:
        print(f"❓ Could not detect EP number ({len(unknown)}) — skipping:")
        for t in unknown:
            print(f"   {t}")

    if not to_fix:
        print("\nNothing to fix!")
        return

    if dry_run:
        print(f"\nDRY RUN complete. Run with --go to apply {len(to_fix)} title fixes.")
        return

    # ── Update ────────────────────────────────────────────────────────────────
    print(f"\nUpdating {len(to_fix)} titles...")
    success = []
    failed  = []
    for v in to_fix:
        try:
            update_title(youtube, v["video_id"], v["new_title"], v["description"])
            print(f"  ✅ {v['ep_num']} — {v['new_title'][:60]}")
            success.append(v["ep_num"])
        except Exception as e:
            print(f"  ❌ {v['ep_num']} FAILED: {e}")
            failed.append(v["ep_num"])

    print(f"\nDone. Updated: {success}")
    if failed:
        print(f"Failed: {failed} — run again to retry.")


if __name__ == "__main__":
    main()
