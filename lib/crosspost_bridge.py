#!/usr/bin/env python3
"""
Crosspost Bridge: Integrates video pipeline commercials with Crosspost social publishing.
Routes rendered commercials to Crosspost for multi-platform distribution.
"""

import json
import shutil
from pathlib import Path
from datetime import datetime

SOCIAL_CLIPS_DIR = Path(__file__).parent.parent / "social_clips"
CROSSPOST_QUEUE = Path(__file__).parent.parent / "crosspost_queue.json"

def queue_commercial_for_posting(commercial_mp4_path, product_name, product_id, platforms=None):
    """
    Queue a rendered commercial for Crosspost publishing.

    Args:
        commercial_mp4_path: Path to rendered commercial MP4
        product_name: Product name (used in caption)
        product_id: Product ID
        platforms: List of platforms to post to (default: all)

    Returns:
        bool: True if queued successfully
    """

    if platforms is None:
        platforms = ["instagram", "tiktok", "youtube_shorts", "facebook"]

    commercial_mp4_path = Path(commercial_mp4_path)

    if not commercial_mp4_path.exists():
        print(f"Error: Commercial file not found: {commercial_mp4_path}")
        return False

    # Ensure social_clips directory exists
    SOCIAL_CLIPS_DIR.mkdir(parents=True, exist_ok=True)

    # Copy commercial to social_clips for Crosspost to find
    dest_filename = f"commercial_{product_id}_{int(datetime.now().timestamp())}.mp4"
    dest_path = SOCIAL_CLIPS_DIR / dest_filename

    try:
        shutil.copy2(commercial_mp4_path, dest_path)
        print(f"✓ Copied to social_clips: {dest_path}")
    except Exception as e:
        print(f"Error copying file: {e}")
        return False

    # Create queue entry for Crosspost
    queue_entry = {
        "id": f"commercial-{product_id}",
        "type": "commercial",
        "file": str(dest_path),
        "product": {
            "id": product_id,
            "name": product_name
        },
        "platforms": platforms,
        "status": "queued",
        "created_at": datetime.now().isoformat(),
        "caption_template": f"🛍️ Check out this {product_name}!\n\n✨ Premium quality\n💰 Affordable prices\n🚚 Fast shipping\n\n#BossListers #Shopping #Quality"
    }

    # Load existing queue
    if CROSSPOST_QUEUE.exists():
        try:
            with open(CROSSPOST_QUEUE) as f:
                queue = json.load(f)
        except:
            queue = {"items": []}
    else:
        queue = {"items": []}

    # Add entry
    queue["items"].append(queue_entry)

    # Save queue
    try:
        with open(CROSSPOST_QUEUE, 'w') as f:
            json.dump(queue, f, indent=2)
        print(f"✓ Queued for Crosspost: {product_name}")
        return True
    except Exception as e:
        print(f"Error saving queue: {e}")
        return False

def get_crosspost_status(product_id):
    """Get publishing status for a commercial."""
    if not CROSSPOST_QUEUE.exists():
        return None

    try:
        with open(CROSSPOST_QUEUE) as f:
            queue = json.load(f)

        for item in queue.get("items", []):
            if item.get("product", {}).get("id") == product_id:
                return item.get("status")
    except:
        pass

    return None

# ══════════════════════════════════════════════════════════════════════════════
# QUEUE PROCESSOR — added 2026-08-12
#
# Before this existed, queue_commercial_for_posting() wrote crosspost_queue.json
# and *nothing read it*. Commercials were queued and silently went nowhere; the
# file had never even been created. This is the missing consumer.
#
# Publishing is irreversible — Instagram has no unpublish API — so the design
# priority here is "never double-post", ahead of throughput or elegance:
#
#   * per-PLATFORM results, not per-item: IG succeeding and TikTok failing must
#     not cause a retry to re-post to IG
#   * a platform is marked "posting" BEFORE the attempt. A crash mid-post leaves
#     it stuck in "posting", which is treated as UNKNOWN and quarantined for a
#     human — never auto-retried, because we cannot tell whether it went live
#   * atomic queue writes (temp + os.replace) so a crash cannot corrupt state
#   * a lock file so two agents polling concurrently cannot both post the same
#     item
# ══════════════════════════════════════════════════════════════════════════════

import os
import sys
import tempfile
import time
from contextlib import contextmanager

BASE_DIR = Path(__file__).resolve().parent.parent
LOCK_FILE = BASE_DIR / ".crosspost_queue.lock"
LOCK_STALE_SEC = 1800  # 30 min — longer than any plausible publish run

#: Terminal per-platform states. Never re-attempted.
_DONE_STATES = frozenset({"posted", "pending_approval", "skipped"})
#: Means "we started publishing and never saw the outcome." Requires a human.
_UNKNOWN_STATE = "posting"


@contextmanager
def _queue_lock():
    """
    Cross-process lock. O_EXCL create is atomic on Windows and POSIX alike.

    A stale lock (crashed run) is reclaimed after LOCK_STALE_SEC rather than
    blocking the pipeline forever.
    """
    if LOCK_FILE.exists():
        age = time.time() - LOCK_FILE.stat().st_mtime
        if age > LOCK_STALE_SEC:
            print(f"[crosspost] reclaiming stale lock ({age / 60:.0f} min old)")
            LOCK_FILE.unlink(missing_ok=True)

    try:
        fd = os.open(str(LOCK_FILE), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        raise RuntimeError(
            "another crosspost run holds the lock — refusing to run "
            "concurrently (double-post risk)") from None

    try:
        os.write(fd, str(os.getpid()).encode())
        os.close(fd)
        yield
    finally:
        LOCK_FILE.unlink(missing_ok=True)


def _save_queue_atomic(queue: dict) -> None:
    """
    Write the queue via temp file + os.replace.

    A plain open(w) truncates before writing; a crash in that window destroys
    the record of what has already been posted, which on a re-run means
    double-posting.
    """
    fd, tmp = tempfile.mkstemp(dir=str(CROSSPOST_QUEUE.parent),
                               prefix=".crosspost_", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(queue, f, indent=2, ensure_ascii=False)
        os.replace(tmp, CROSSPOST_QUEUE)
    except Exception:
        Path(tmp).unlink(missing_ok=True)
        raise


def _load_queue() -> dict:
    if not CROSSPOST_QUEUE.exists():
        return {"items": []}
    try:
        return json.loads(CROSSPOST_QUEUE.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise RuntimeError(
            f"{CROSSPOST_QUEUE.name} is corrupt ({e}) — refusing to process, "
            f"because we cannot tell what has already been posted") from e


def _publishers():
    """
    Map platform names to auto_publisher functions.

    Imported lazily: auto_publisher pulls in clip_generator and Gemini config at
    module load, which should not happen just because something imported the
    queue writer.
    """
    sys.path.insert(0, str(BASE_DIR))
    from social_clips import auto_publisher as ap

    return {
        "instagram": lambda clip, caption, item: ap.publish_instagram(clip, caption),
        "tiktok": lambda clip, caption, item: ap.publish_tiktok(clip, caption),
        "facebook": lambda clip, caption, item: ap.publish_facebook(clip, caption),
        # Standing rule: YouTube uploads need Josh's manual approval, so this
        # stages a .bat and returns pending_approval rather than posting.
        "youtube_shorts": lambda clip, caption, item: ap.publish_youtube_short(
            clip, item.get("product", {}).get("name", "Commercial"), caption,
            episode_id=item.get("id", "")),
    }, ap


def _pending_platforms(item: dict) -> tuple[list[str], list[str]]:
    """
    Split an item's platforms into (attemptable, quarantined).

    Quarantined = stuck in "posting" from a previous crashed run. We do not know
    whether those went live, so they are surfaced for a human instead of retried.
    """
    results = item.get("results", {})
    attemptable, quarantined = [], []
    for platform in item.get("platforms", []):
        state = results.get(platform, {}).get("status")
        if state in _DONE_STATES:
            continue
        if state == _UNKNOWN_STATE:
            quarantined.append(platform)
            continue
        attemptable.append(platform)
    return attemptable, quarantined


def process_queue(*, dry_run: bool = False, only_id: str | None = None) -> dict:
    """
    Publish every queued commercial to its platforms.

    Args:
        dry_run: report what would post and exit without calling any platform.
        only_id: restrict to a single queue item id.

    Returns a summary dict. Safe to call repeatedly — completed platforms are
    never re-attempted.
    """
    summary = {"items": 0, "posted": 0, "failed": 0,
               "quarantined": 0, "skipped_items": 0}

    with _queue_lock():
        queue = _load_queue()
        items = queue.get("items", [])
        if not items:
            print("[crosspost] queue is empty")
            return summary

        publishers, ap = (None, None) if dry_run else _publishers()

        for item in items:
            if only_id and item.get("id") != only_id:
                continue

            clip = Path(item.get("file", ""))
            caption = item.get("caption_template", "")
            attemptable, quarantined = _pending_platforms(item)

            if quarantined:
                summary["quarantined"] += len(quarantined)
                print(f"[crosspost] {item.get('id')}: QUARANTINED on "
                      f"{', '.join(quarantined)} — a previous run died mid-post. "
                      f"Verify manually whether these went live, then edit "
                      f"results[platform].status in {CROSSPOST_QUEUE.name}.")

            if not attemptable:
                summary["skipped_items"] += 1
                continue

            if not clip.exists():
                print(f"[crosspost] {item.get('id')}: clip missing ({clip}) — "
                      f"cannot publish")
                item["status"] = "failed"
                summary["failed"] += 1
                continue

            summary["items"] += 1

            if dry_run:
                print(f"[crosspost] WOULD POST {item.get('id')} → "
                      f"{', '.join(attemptable)}  ({clip.name})")
                continue

            results = item.setdefault("results", {})
            item["status"] = "posting"

            for platform in attemptable:
                fn = publishers.get(platform)
                if fn is None:
                    results[platform] = {
                        "status": "skipped",
                        "detail": f"no publisher wired for '{platform}'",
                        "at": datetime.now().isoformat(),
                    }
                    continue

                # Persist "posting" BEFORE the attempt. If we die during the
                # call, the restart sees "posting" and quarantines it rather
                # than posting a second time.
                results[platform] = {"status": _UNKNOWN_STATE,
                                     "at": datetime.now().isoformat()}
                _save_queue_atomic(queue)

                outcome = ap._publish_with_retry(platform, fn, clip, caption, item)
                outcome["at"] = datetime.now().isoformat()
                results[platform] = outcome
                _save_queue_atomic(queue)

                if outcome.get("status") == "posted":
                    summary["posted"] += 1
                    print(f"[crosspost] {item.get('id')} → {platform}: POSTED")
                elif outcome.get("status") in _DONE_STATES:
                    print(f"[crosspost] {item.get('id')} → {platform}: "
                          f"{outcome.get('status')} — {outcome.get('detail', '')}")
                else:
                    summary["failed"] += 1
                    print(f"[crosspost] {item.get('id')} → {platform}: FAILED — "
                          f"{outcome.get('detail', '?')}")

            done = all(results.get(p, {}).get("status") in _DONE_STATES
                       for p in item.get("platforms", []))
            item["status"] = "done" if done else "partial"
            _save_queue_atomic(queue)

    return summary


# ── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse

    ap_ = argparse.ArgumentParser(
        description="Crosspost queue: writer + processor for commercials.")
    sub = ap_.add_subparsers(dest="cmd")

    p = sub.add_parser("process", help="publish queued commercials")
    p.add_argument("--dry-run", action="store_true",
                   help="show what would post without posting (RECOMMENDED "
                        "first — publishing is irreversible)")
    p.add_argument("--id", help="process a single queue item by id")

    sub.add_parser("list", help="show the queue and per-platform status")

    args = ap_.parse_args()

    if args.cmd == "list":
        q = _load_queue()
        if not q.get("items"):
            print("queue is empty")
        for it in q.get("items", []):
            print(f"\n{it.get('id')}  [{it.get('status', '?')}]  {it.get('file')}")
            for plat in it.get("platforms", []):
                r = it.get("results", {}).get(plat, {})
                print(f"    {plat:16s} {r.get('status', 'queued'):16s} "
                      f"{r.get('detail', '')}")
    elif args.cmd == "process":
        print(json.dumps(process_queue(dry_run=args.dry_run,
                                       only_id=args.id), indent=2))
    else:
        ap_.print_help()
