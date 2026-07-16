#!/usr/bin/env python3
"""
pipeline_status.py — Writes current pipeline state to pipeline_status.json
Called by render and upload scripts to report progress.
Claude reads this file to know what's running without asking Josh.
"""
import json, sys
from pathlib import Path
from datetime import datetime

BASE_DIR     = Path(__file__).resolve().parent
STATUS_FILE  = BASE_DIR / "pipeline_status.json"
RENDERS_DIR  = BASE_DIR / "renders"
UPLOADED_LOG = BASE_DIR / "uploaded_videos.json"

def get_status() -> dict:
    renders = {}
    for f in sorted(RENDERS_DIR.glob("GG_EP*_final.mp4")):
        ep = f.stem.replace("_final", "").upper()
        import subprocess
        r = subprocess.run(["ffprobe","-v","quiet","-show_entries","format=duration",
                           "-of","csv=p=0",str(f)], capture_output=True, text=True)
        try:
            dur = float(r.stdout.strip())
        except:
            dur = 0
        renders[ep] = {"duration_min": round(dur/60,1), "size_mb": round(f.stat().st_size/1048576,1),
                       "modified": datetime.fromtimestamp(f.stat().st_mtime).strftime("%Y-%m-%d %H:%M")}

    try:
        uploaded = list(json.loads(UPLOADED_LOG.read_text()).keys())
    except:
        uploaded = []

    # Check what's actively rendering (output files modified in last 10 min)
    import time
    now = time.time()
    active_renders = []
    output_dir = BASE_DIR / "output"
    if output_dir.exists():
        for f in output_dir.rglob("*.mp4"):
            if now - f.stat().st_mtime < 600:
                ep = f.parts[-2] if len(f.parts) > 1 else "unknown"
                if ep not in active_renders:
                    active_renders.append(ep)

    ready = [ep for ep, info in renders.items() 
             if info["duration_min"] >= 35 and ep not in uploaded]

    return {
        "last_checked": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "active_renders": active_renders,
        "renders_ready_to_upload": ready,
        "uploaded": uploaded,
        "all_renders": renders,
    }

if __name__ == "__main__":
    status = get_status()
    STATUS_FILE.write_text(json.dumps(status, indent=2))
    print(json.dumps(status, indent=2))
