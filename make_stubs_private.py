#!/usr/bin/env python3
"""
make_stubs_private.py — Set stub episodes to Private on YouTube
===============================================================
Finds and sets ALL S2 stub episodes (EP006-EP011) to Private on YouTube.
These are short, wrong-content stubs that were uploaded before the full
54-scene scripts were written. Good versions will replace them.

Stubs to kill:
  EP006 — Salamis/Greece stub   (real: Pearl Harbor — already re-uploaded)
  EP007 — Gaugamela stub        (real: D-Day — already re-uploaded)
  EP008 — Stalingrad stub       (real: Stalingrad full — pending re-render)
  EP009 — Iwo Jima stub         (real: Iwo Jima full — pending re-render)
  EP010 — Vietnam stub          (real: Vietnam full — pending re-render)
  EP011 — Constantinople stub   (real: Ia Drang/Khe Sanh/Tet — pending re-render)

Usage:
    python make_stubs_private.py           # dry run — shows what WOULD change
    python make_stubs_private.py --go      # actually set to Private
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
SCOPES     = ["https://www.googleapis.com/auth/youtube"]

# All S2 stub episodes to make private.
# Matched by keywords found anywhere in the YouTube video title (case-insensitive).
TARGET_EPISODES = {
    "EP006-stub": ["salamis", "plataea"],           # old Greece stub
    "EP007-stub": ["gaugamela", "alexander's gamble"],  # old Gaugamela stub
    "EP008-stub": ["stalingrad"],
    "EP009-stub": ["iwo jima"],
    "EP010-stub": ["vietnam"],
    "EP011-stub": ["constantinople", "fall of const"],  # old Constantinople stub
}


def get_youtube():
    if not TOKEN_PATH.exists():
        sys.exit(f"ERROR: {TOKEN_PATH} not found.")
    with open(TOKEN_PATH, "rb") as f:
        creds = pickle.load(f)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        with open(TOKEN_PATH, "wb") as f:
            pickle.dump(creds, f)
    return build("youtube", "v3", credentials=creds)


def get_channel_videos(youtube) -> list[dict]:
    ch_resp = youtube.channels().list(part="id,snippet,contentDetails", mine=True).execute()
    if not ch_resp.get("items"):
        sys.exit("ERROR: No channel found for this token.")
    ch = ch_resp["items"][0]
    print(f"Channel: {ch['snippet']['title']} ({ch['id']})")
    uploads_pl = ch["contentDetails"]["relatedPlaylists"]["uploads"]

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
                "video_id": sn["resourceId"]["videoId"],
                "title":    sn["title"],
            })
        page_token = resp.get("nextPageToken")
        if not page_token:
            break

    # Get privacy status for each video
    ids = [v["video_id"] for v in videos]
    enriched = []
    for i in range(0, len(ids), 50):
        chunk = ids[i:i+50]
        vresp = youtube.videos().list(part="status,snippet", id=",".join(chunk)).execute()
        for item in vresp.get("items", []):
            enriched.append({
                "video_id":      item["id"],
                "title":         item["snippet"]["title"],
                "privacy_status": item["status"]["privacyStatus"],
            })

    print(f"Found {len(enriched)} videos.\n")
    return enriched


def match_target(title: str) -> str | None:
    """Return the EP key if this title matches a target episode."""
    title_lower = title.lower()
    for ep_key, keywords in TARGET_EPISODES.items():
        if any(kw in title_lower for kw in keywords):
            return ep_key
    return None


def set_private(youtube, video_id: str) -> None:
    youtube.videos().update(
        part="status",
        body={
            "id": video_id,
            "status": {"privacyStatus": "private"},
        },
    ).execute()


def main() -> None:
    ap = argparse.ArgumentParser(description="Set stub GG episodes to Private")
    ap.add_argument("--go", action="store_true", help="Actually set to Private (default: dry run)")
    args = ap.parse_args()

    dry_run = not args.go
    if dry_run:
        print("=== DRY RUN — no changes will be made ===\n")
    else:
        print("=== LIVE UPDATE — setting videos to Private on YouTube ===\n")

    youtube = get_youtube()
    videos  = get_channel_videos(youtube)

    to_private  = []
    already_priv = []
    no_match    = []

    for v in videos:
        ep_key = match_target(v["title"])
        if ep_key:
            if v["privacy_status"] == "private":
                already_priv.append(f"{ep_key} — {v['title']} (already private)")
            else:
                to_private.append({**v, "ep_key": ep_key})

    print(f"✅ Already private ({len(already_priv)}):")
    for t in already_priv:
        print(f"   {t}")

    print(f"\n🔒 Will set to Private ({len(to_private)}):")
    for v in to_private:
        print(f"   {v['ep_key']} — {v['title']} [{v['privacy_status']} → private]")
        print(f"   https://youtu.be/{v['video_id']}")

    if not to_private:
        print("\nNothing to do!")
        return

    if dry_run:
        print(f"\nDRY RUN complete. Run with --go to set {len(to_private)} videos to Private.")
        return

    print(f"\nSetting {len(to_private)} videos to Private...")
    for v in to_private:
        try:
            set_private(youtube, v["video_id"])
            print(f"  🔒 {v['ep_key']} — {v['title'][:60]}")
        except Exception as e:
            print(f"  ❌ {v['ep_key']} FAILED: {e}")

    print("\nDone. Videos are now Private on YouTube.")


if __name__ == "__main__":
    main()
