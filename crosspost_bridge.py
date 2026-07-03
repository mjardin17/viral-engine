#!/usr/bin/env python3
"""
crosspost_bridge.py — CrossPost Publish Queue for Viral Engine
===============================================================
Empire OS writes publish jobs here. CrossPost agent reads and executes them.

Flow:
  1. empire_api.py POST /publish/<id>  →  writes job to crosspost_queue/
  2. crosspost_bridge.py --watch       →  monitors queue, calls CrossPost
  3. CrossPost uploads to YouTube / TikTok / Instagram / X

Can also be called directly by Empire OS:
  python crosspost_bridge.py --episode GG_EP012 --platforms youtube,tiktok

CrossPost config lives in crosspost_config.json (you set the API keys there).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

BASE_DIR      = Path(__file__).resolve().parent
CROSSPOST_DIR = BASE_DIR / "crosspost_queue"
RENDERS_DIR   = BASE_DIR / "renders"
PROMPTS_DIR   = BASE_DIR / "prompts"
CONFIG_PATH   = BASE_DIR / "crosspost_config.json"

CROSSPOST_DIR.mkdir(exist_ok=True)


# ── Config ─────────────────────────────────────────────────────────────────

DEFAULT_CONFIG = {
    "youtube": {
        "enabled": False,
        "channel_id": "",
        "playlist_id": "",
        "privacy": "unlisted",         # public / unlisted / private
        "category_id": "27",           # 27 = Education
        "default_tags": ["Gods and Glory", "history", "documentary", "battle"],
    },
    "tiktok": {
        "enabled": False,
        "account_id": "",
    },
    "instagram": {
        "enabled": False,
        "account_id": "",
    },
    "crosspost_api_url": "",           # Your CrossPost instance URL
    "crosspost_api_key": "",           # Set via env CROSSPOST_API_KEY
}


def load_config() -> dict:
    if CONFIG_PATH.exists():
        return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    # Write default config for Josh to fill in
    CONFIG_PATH.write_text(json.dumps(DEFAULT_CONFIG, indent=2), encoding="utf-8")
    return DEFAULT_CONFIG


# ── Script loader ───────────────────────────────────────────────────────────

def load_script(ep_id: str) -> dict | None:
    for p in PROMPTS_DIR.rglob(f"*{ep_id.lower()}*.json"):
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            pass
    return None


# ── Job builder ─────────────────────────────────────────────────────────────

def build_job(ep_id: str, platforms: list[str]) -> dict:
    """Build a CrossPost publish job for an episode."""
    ep_id  = ep_id.upper()
    final  = RENDERS_DIR / f"{ep_id}_final.mp4"
    if not final.exists() or final.stat().st_size < 1_000_000:
        raise FileNotFoundError(f"{ep_id}_final.mp4 not found in renders/")

    script = load_script(ep_id)
    config = load_config()

    title = script.get("youtube_title", script.get("title", ep_id)) if script else ep_id
    tagline   = script.get("tagline", "") if script else ""
    viral_hook = script.get("viral_hook", "") if script else ""
    lesson     = script.get("lesson", "") if script else ""

    description = "\n\n".join(filter(None, [
        tagline,
        viral_hook,
        lesson and f"The lesson: {lesson}",
        "─────────────────────────",
        "Subscribe to Gods and Glory for more cinematic history documentaries.",
        "#GodsAndGlory #History #Documentary #Battle #AncientHistory",
    ]))

    tags = list(set(
        config.get("youtube", {}).get("default_tags", []) +
        ["Gods and Glory", "history", "documentary", "battle", ep_id,
         script.get("title", "") if script else ""]
    ))

    return {
        "episode_id":   ep_id,
        "video_path":   str(final),
        "title":        title,
        "description":  description,
        "tags":         [t for t in tags if t],
        "platforms":    platforms,
        "youtube": {
            "privacy":     config.get("youtube", {}).get("privacy", "unlisted"),
            "category_id": config.get("youtube", {}).get("category_id", "27"),
            "playlist_id": config.get("youtube", {}).get("playlist_id", ""),
        },
        "thumbnail_prompt": (
            script.get("scenes", [{}])[0].get("visual_prompt", "") if script else ""
        ),
        "created_at":   time.time(),
        "status":       "pending",
    }


def queue_job(ep_id: str, platforms: list[str]) -> Path:
    """Write a job to crosspost_queue/ and return the job file path."""
    job  = build_job(ep_id, platforms)
    path = CROSSPOST_DIR / f"{ep_id}_{int(time.time())}.json"
    path.write_text(json.dumps(job, indent=2), encoding="utf-8")
    print(f"Queued: {path.name}")
    print(f"Title:  {job['title']}")
    print(f"Platforms: {', '.join(platforms)}")
    return path


def list_queue() -> list[dict]:
    """Return all pending jobs from crosspost_queue/."""
    jobs = []
    for f in sorted(CROSSPOST_DIR.glob("*.json")):
        try:
            job = json.loads(f.read_text(encoding="utf-8"))
            job["_file"] = f.name
            jobs.append(job)
        except Exception:
            pass
    return jobs


def mark_complete(job_file: str, result: dict) -> None:
    """Mark a job as complete with CrossPost's response."""
    path = CROSSPOST_DIR / job_file
    if path.exists():
        job = json.loads(path.read_text(encoding="utf-8"))
        job["status"]        = "complete"
        job["completed_at"]  = time.time()
        job["crosspost_result"] = result
        path.write_text(json.dumps(job, indent=2), encoding="utf-8")


def dispatch_to_crosspost(job: dict, config: dict) -> dict:
    """
    Send a job to your CrossPost API endpoint.
    Configure crosspost_api_url in crosspost_config.json.
    """
    import urllib.request as _req

    api_url = config.get("crosspost_api_url", "")
    api_key = os.environ.get("CROSSPOST_API_KEY", config.get("crosspost_api_key", ""))

    if not api_url:
        return {"error": "crosspost_api_url not configured", "status": "skipped"}

    data = json.dumps(job).encode("utf-8")
    headers = {
        "Content-Type":  "application/json",
        "Authorization": f"Bearer {api_key}",
    }
    request = _req.Request(api_url, data=data, headers=headers, method="POST")
    try:
        with _req.urlopen(request, timeout=60) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        return {"error": str(e), "status": "failed"}


def watch(interval: int = 30) -> None:
    """Watch crosspost_queue/ and dispatch pending jobs automatically."""
    config = load_config()
    api_url = config.get("crosspost_api_url", "")
    if not api_url:
        print("WARNING: crosspost_api_url not configured. Watching but not dispatching.")
    print(f"Watching {CROSSPOST_DIR} every {interval}s...")
    while True:
        jobs = [j for j in list_queue() if j.get("status") == "pending"]
        for job in jobs:
            print(f"Dispatching: {job['episode_id']} → {', '.join(job.get('platforms', []))}")
            result = dispatch_to_crosspost(job, config)
            mark_complete(job["_file"], result)
            print(f"  Result: {result.get('status', result)}")
        time.sleep(interval)


# ── CLI ─────────────────────────────────────────────────────────────────────

def main() -> None:
    ap = argparse.ArgumentParser(description="CrossPost queue for Viral Engine")
    sub = ap.add_subparsers(dest="cmd")

    q = sub.add_parser("queue", help="Queue an episode for publishing")
    q.add_argument("--episode",   required=True, help="Episode ID e.g. GG_EP012")
    q.add_argument("--platforms", default="youtube", help="Comma-separated: youtube,tiktok,instagram")

    sub.add_parser("list", help="List pending jobs")

    w = sub.add_parser("watch", help="Watch queue and dispatch to CrossPost")
    w.add_argument("--interval", type=int, default=30, help="Poll interval seconds")

    args = ap.parse_args()

    if args.cmd == "queue":
        platforms = [p.strip() for p in args.platforms.split(",")]
        try:
            path = queue_job(args.episode, platforms)
            print(f"\nJob ready: {path}")
        except FileNotFoundError as e:
            print(f"ERROR: {e}")
            sys.exit(1)

    elif args.cmd == "list":
        jobs = list_queue()
        if not jobs:
            print("No jobs in queue.")
        for j in jobs:
            print(f"  [{j.get('status','?'):10s}] {j['episode_id']} → {', '.join(j.get('platforms', []))} | {j['_file']}")

    elif args.cmd == "watch":
        watch(args.interval)

    else:
        ap.print_help()


if __name__ == "__main__":
    main()
