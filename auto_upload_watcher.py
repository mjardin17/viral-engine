#!/usr/bin/env python3
"""
auto_upload_watcher.py — Watches renders/ and auto-uploads finished GG episodes
================================================================================
Polls every 5 minutes. When a new GG_EP*_final.mp4 appears that is:
  - At least 35 minutes long
  - Not already in uploaded_videos.json
It uploads automatically to the Gods & Glory channel.

Usage:
    python auto_upload_watcher.py
"""
from __future__ import annotations
import json, pickle, shutil, subprocess, sys, time
from pathlib import Path
from datetime import datetime

BASE_DIR     = Path(__file__).resolve().parent
RENDERS_DIR  = BASE_DIR / "renders"
UPLOADED_LOG = BASE_DIR / "uploaded_videos.json"
TOKEN_PATH   = BASE_DIR / "token_gg.pickle"
PYTHON       = r"C:\Users\jjard\AppData\Local\Programs\Python\Python314\python.exe"
MIN_DURATION = 35 * 60  # 35 minutes minimum

def find_ffprobe() -> str:
    """Find ffprobe — same search order as auto_render.py."""
    candidates = [
        shutil.which("ffprobe"),
        str(Path(__file__).parent / "ffmpeg_bin" / "ffprobe.exe"),
        r"C:\ffmpeg\bin\ffprobe.exe",
        r"C:\Program Files\ffmpeg\bin\ffprobe.exe",
        r"C:\Program Files (x86)\ffmpeg\bin\ffprobe.exe",
        str(Path.home() / "ffmpeg" / "bin" / "ffprobe.exe"),
    ]
    for c in candidates:
        if c and Path(c).exists():
            return c
    return "ffprobe"  # fall back to PATH — will surface a real error in logs

FFPROBE = find_ffprobe()

def log(msg: str) -> None:
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)

def get_duration(path: Path) -> float:
    try:
        result = subprocess.run(
            [FFPROBE, "-v", "quiet", "-show_entries", "format=duration",
             "-of", "csv=p=0", str(path)],
            capture_output=True, text=True
        )
        return float(result.stdout.strip())
    except:
        return 0.0

def get_uploaded() -> set:
    if not UPLOADED_LOG.exists():
        return set()
    try:
        return set(json.loads(UPLOADED_LOG.read_text()).keys())
    except:
        return set()

def upload(ep_id: str) -> bool:
    log(f"Uploading {ep_id}...")
    result = subprocess.run(
        [PYTHON, "channel_uploader.py", "--channel", "gg",
         "--episodes", ep_id, "--yes"],
        cwd=str(BASE_DIR)
    )
    return result.returncode == 0

def main():
    log("Auto-upload watcher started. Checking every 5 minutes.")
    log(f"Minimum duration: {MIN_DURATION//60} minutes")

    while True:
        uploaded = get_uploaded()
        renders = sorted(RENDERS_DIR.glob("GG_EP*_final.mp4"))

        for render in renders:
            ep_id = render.stem.replace("_final", "").upper()
            if ep_id in uploaded:
                continue
            dur = get_duration(render)
            if dur < MIN_DURATION:
                log(f"SKIP {ep_id} — only {dur/60:.1f} min (need {MIN_DURATION//60}+)")
                continue
            log(f"FOUND {ep_id} — {dur/60:.1f} min — uploading now...")
            success = upload(ep_id)
            if success:
                log(f"SUCCESS: {ep_id} uploaded to Gods & Glory")
            else:
                log(f"FAILED: {ep_id} — check logs")

        log("Sleeping 5 minutes...")
        time.sleep(300)

if __name__ == "__main__":
    main()
