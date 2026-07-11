"""
upload_watcher.py — Empire OS Auto-Upload Watcher
Watches renders/ for completed finals, runs QC, queues upload automatically.

Usage:
    python upload_watcher.py --channel gg
    python upload_watcher.py --channel gg --workers 1 --interval 60
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

# ── Paths ────────────────────────────────────────────────────────────────────
REPO         = Path(__file__).parent
RENDERS_DIR  = REPO / "renders"
LOG_FILE     = REPO / "upload_watcher_log.json"
FFPROBE      = str(REPO / "ffmpeg_bin" / "ffprobe.exe")
UPLOADER     = str(REPO / "channel_uploader.py")
PYTHON       = r"C:\Users\jjard\AppData\Local\Programs\Python\Python314\python.exe"

# ── QC thresholds ────────────────────────────────────────────────────────────
MIN_DURATION_S  = 2700   # 45 min
MIN_SIZE_MB     = 50

# ── Channel → token mapping (never use token.pickle) ─────────────────────────
CHANNEL_TOKENS: dict[str, str] = {
    "gg": "token_gg.pickle",
    "il": "token_il.pickle",
    "lo": "token_lo.pickle",
    "ed": "token_ed.pickle",
}


def load_log() -> dict:
    if LOG_FILE.exists():
        return json.loads(LOG_FILE.read_text(encoding="utf-8"))
    return {"uploaded": [], "failed_qc": [], "skipped": []}


def save_log(data: dict) -> None:
    LOG_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")


def get_duration(mp4: Path) -> float:
    """Return duration in seconds via ffprobe, or 0.0 on error."""
    try:
        result = subprocess.run(
            [FFPROBE, "-v", "error", "-show_entries", "format=duration",
             "-of", "csv=p=0", str(mp4)],
            capture_output=True, text=True, timeout=30,
        )
        return float(result.stdout.strip())
    except Exception:
        return 0.0


def qc_pass(mp4: Path) -> tuple[bool, str]:
    """Returns (pass, reason). Checks size + duration."""
    size_mb = mp4.stat().st_size / (1024 * 1024)
    if size_mb < MIN_SIZE_MB:
        return False, f"Too small: {size_mb:.1f}MB (min {MIN_SIZE_MB}MB)"

    duration = get_duration(mp4)
    if duration < MIN_DURATION_S:
        return False, f"Too short: {duration/60:.1f}min (min {MIN_DURATION_S/60:.0f}min)"

    return True, f"OK — {size_mb:.0f}MB, {duration/60:.1f}min"


def extract_episode_id(mp4: Path) -> str:
    """GG_EP012_final.mp4 → GG_EP012"""
    return mp4.stem.replace("_final", "")


def find_channel(episode_id: str) -> str:
    """GG_EP012 → gg"""
    prefix = episode_id.split("_")[0].lower()
    return prefix


def upload_episode(episode_id: str, channel: str) -> bool:
    """Run channel_uploader.py for a single episode. Returns True on success."""
    token = CHANNEL_TOKENS.get(channel)
    if not token:
        print(f"  [WATCHER] No token configured for channel '{channel}' — skipping")
        return False

    print(f"  [WATCHER] Uploading {episode_id} → channel={channel} ...")
    result = subprocess.run(
        [PYTHON, UPLOADER, "--channel", channel,
         "--episodes", episode_id, "--privacy", "public", "--yes"],
        cwd=str(REPO),
        timeout=600,
    )
    return result.returncode == 0


def watch(channel_filter: str | None, interval: int, workers: int) -> None:
    log = load_log()
    already_handled: set[str] = set(log["uploaded"] + log["failed_qc"] + log["skipped"])

    print(f"\n[WATCHER] Started — watching {RENDERS_DIR}")
    print(f"          Channel filter: {channel_filter or 'all'}")
    print(f"          Poll interval: {interval}s\n")

    while True:
        finals = sorted(RENDERS_DIR.glob("*_final.mp4"))

        for mp4 in finals:
            ep_id    = extract_episode_id(mp4)
            channel  = find_channel(ep_id)

            if ep_id in already_handled:
                continue

            if channel_filter and channel != channel_filter:
                continue

            ts = datetime.now().strftime("%H:%M:%S")
            print(f"[{ts}] New final detected: {mp4.name}")

            passed, reason = qc_pass(mp4)
            if not passed:
                print(f"  [QC FAIL] {ep_id} — {reason} — skipping upload")
                log["failed_qc"].append(ep_id)
                already_handled.add(ep_id)
                save_log(log)
                continue

            print(f"  [QC PASS] {ep_id} — {reason}")
            success = upload_episode(ep_id, channel)

            if success:
                log["uploaded"].append(ep_id)
                print(f"  [UPLOADED] {ep_id} ✓")
            else:
                log["skipped"].append(ep_id)
                print(f"  [UPLOAD FAILED] {ep_id} — check terminal output above")

            already_handled.add(ep_id)
            save_log(log)

        time.sleep(interval)


def main() -> None:
    parser = argparse.ArgumentParser(description="Empire OS Upload Watcher")
    parser.add_argument("--channel",  default=None,
                        help="Only upload episodes for this channel (gg, il, lo, ed)")
    parser.add_argument("--interval", type=int, default=60,
                        help="Poll interval in seconds (default: 60)")
    parser.add_argument("--workers",  type=int, default=1,
                        help="Max simultaneous uploads (default: 1)")
    args = parser.parse_args()

    try:
        watch(args.channel, args.interval, args.workers)
    except KeyboardInterrupt:
        print("\n[WATCHER] Stopped by user.")
        sys.exit(0)


if __name__ == "__main__":
    main()
