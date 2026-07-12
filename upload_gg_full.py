#!/usr/bin/env python3
"""
upload_gg_full.py — Empire OS Smart GG Uploader
================================================
Rules:
  - Only uploads GG episodes that are >= MIN_DURATION_SEC (default 2400s = 40 min)
  - Skips episodes already in uploaded_videos.json
  - Auto-retries failed uploads up to MAX_RETRIES times with backoff
  - Logs everything to upload_gg_full.log
  - Uploads in episode order (EP001, EP002, ...)

Usage:
  python upload_gg_full.py              # dry run — shows what WOULD upload
  python upload_gg_full.py --go         # actually upload
  python upload_gg_full.py --min-min 45 --go  # strict 45-min gate
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
import logging
from pathlib import Path
from datetime import datetime

# ── Config ────────────────────────────────────────────────────────────────────
BASE_DIR         = Path(__file__).resolve().parent
RENDERS_DIR      = BASE_DIR / "renders"
UPLOADED_LOG     = BASE_DIR / "uploaded_videos.json"
LOG_FILE         = BASE_DIR / "upload_gg_full.log"
PYTHON           = sys.executable
UPLOADER         = BASE_DIR / "channel_uploader.py"

MIN_DURATION_SEC = 2400   # 40 min default — episodes below this are skipped
MAX_RETRIES      = 3
RETRY_DELAY_SEC  = 30     # wait 30s before retry

# All GG episode IDs in upload order
ALL_GG_EPISODES = [
    "GG_EP001", "GG_EP002", "GG_EP003", "GG_EP004", "GG_EP005",
    "GG_EP006", "GG_EP007", "GG_EP008", "GG_EP009", "GG_EP010",
    "GG_EP011", "GG_EP012", "GG_EP013", "GG_EP014", "GG_EP015",
    "GG_EP016", "GG_EP017", "GG_EP018", "GG_EP019", "GG_EP020",
    "GG_EP021", "GG_EP022", "GG_EP023", "GG_EP024", "GG_EP025",
]

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-7s  %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ]
)
log = logging.getLogger("gg_uploader")


def find_ffprobe() -> str:
    """Find ffprobe on Windows or PATH."""
    import shutil
    candidates = [
        "ffprobe",
        r"C:\ffmpeg\bin\ffprobe.exe",
        r"C:\Program Files\ffmpeg\bin\ffprobe.exe",
        str(BASE_DIR / "ffmpeg_bin" / "ffprobe.exe"),
    ]
    for c in candidates:
        if shutil.which(c) or Path(c).exists():
            return c
    return "ffprobe"  # fallback, will fail gracefully


def get_duration_sec(path: Path) -> float:
    """Return video duration in seconds via ffprobe."""
    try:
        ffprobe = find_ffprobe()
        result = subprocess.run(
            [ffprobe, "-v", "quiet",
             "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1",
             str(path)],
            capture_output=True, text=True, timeout=30
        )
        val = result.stdout.strip()
        return float(val) if val else 0.0
    except Exception:
        return 0.0


def find_render(ep_id: str) -> Path | None:
    """Find the final MP4 for a GG episode."""
    candidates = [
        RENDERS_DIR / f"{ep_id}_final.mp4",
        RENDERS_DIR / f"{ep_id.lower()}_final.mp4",
    ]
    for p in candidates:
        if p.exists():
            return p
    return None


def already_uploaded(ep_id: str) -> bool:
    """Check uploaded_videos.json for this episode."""
    if not UPLOADED_LOG.exists():
        return False
    data = json.loads(UPLOADED_LOG.read_text(encoding="utf-8"))
    return ep_id in data or ep_id.upper() in data


def upload_with_retry(ep_id: str, dry_run: bool) -> bool:
    """Call channel_uploader.py for one episode, retry on failure."""
    for attempt in range(1, MAX_RETRIES + 1):
        log.info(f"[{ep_id}] Upload attempt {attempt}/{MAX_RETRIES}")
        if dry_run:
            log.info(f"[{ep_id}] DRY RUN — would call: channel_uploader.py --channel gg --episodes {ep_id} --yes")
            return True

        result = subprocess.run(
            [PYTHON, str(UPLOADER), "--channel", "gg", "--episodes", ep_id, "--yes"],
            capture_output=False   # let output stream live to terminal + log
        )
        if result.returncode == 0:
            log.info(f"[{ep_id}] ✅ Upload succeeded")
            return True
        else:
            log.warning(f"[{ep_id}] ❌ Attempt {attempt} failed (exit code {result.returncode})")
            if attempt < MAX_RETRIES:
                log.info(f"[{ep_id}] Retrying in {RETRY_DELAY_SEC}s ...")
                time.sleep(RETRY_DELAY_SEC)

    log.error(f"[{ep_id}] FAILED after {MAX_RETRIES} attempts — skipping, will not retry")
    return False


def main():
    ap = argparse.ArgumentParser(description="Empire OS Smart GG Batch Uploader")
    ap.add_argument("--go",      action="store_true", help="Actually upload (default is dry run)")
    ap.add_argument("--min-min", type=int, default=40, help="Minimum episode length in minutes (default 40)")
    args = ap.parse_args()

    min_sec  = args.min_min * 60
    dry_run  = not args.go

    log.info("=" * 60)
    log.info(f"Empire OS GG Uploader — {datetime.now():%Y-%m-%d %H:%M:%S}")
    log.info(f"Mode: {'DRY RUN' if dry_run else 'LIVE UPLOAD'}")
    log.info(f"Min duration: {args.min_min} min ({min_sec}s)")
    log.info("=" * 60)

    queued    = []
    skipped   = []
    too_short = []
    missing   = []

    # ── Scan episodes ──────────────────────────────────────────────────────
    for ep_id in ALL_GG_EPISODES:
        render = find_render(ep_id)

        if render is None:
            log.info(f"[{ep_id}] No render found — skipping")
            missing.append(ep_id)
            continue

        dur = get_duration_sec(render)
        dur_min = dur / 60

        if already_uploaded(ep_id):
            log.info(f"[{ep_id}] Already uploaded — skipping ({dur_min:.0f} min, {render.stat().st_size//1024//1024}MB)")
            skipped.append(ep_id)
            continue

        if dur < min_sec:
            log.warning(f"[{ep_id}] TOO SHORT — {dur_min:.0f} min < {args.min_min} min gate — SKIP")
            too_short.append(ep_id)
            continue

        log.info(f"[{ep_id}] QUEUED — {dur_min:.0f} min, {render.stat().st_size//1024//1024}MB")
        queued.append(ep_id)

    # ── Summary before upload ──────────────────────────────────────────────
    log.info("")
    log.info(f"Already uploaded:  {len(skipped)}  — {skipped}")
    log.info(f"Too short (blocked): {len(too_short)} — {too_short}")
    log.info(f"No render yet:     {len(missing)} — {missing}")
    log.info(f"Queued to upload:  {len(queued)}  — {queued}")
    log.info("")

    if not queued:
        log.info("Nothing to upload. Done.")
        return

    if dry_run:
        log.info("DRY RUN complete. Run with --go to actually upload.")
        return

    # ── Upload loop ────────────────────────────────────────────────────────
    succeeded = []
    failed    = []

    for ep_id in queued:
        ok = upload_with_retry(ep_id, dry_run=False)
        if ok:
            succeeded.append(ep_id)
        else:
            failed.append(ep_id)
        # Small pause between uploads to avoid quota hammering
        if ep_id != queued[-1]:
            log.info("Pausing 10s before next upload ...")
            time.sleep(10)

    # ── Final report ───────────────────────────────────────────────────────
    log.info("")
    log.info("=" * 60)
    log.info(f"DONE. Succeeded: {succeeded}")
    if failed:
        log.error(f"FAILED:    {failed}")
        log.error("Run script again — it will retry only the failed ones.")
    log.info("=" * 60)


if __name__ == "__main__":
    main()
