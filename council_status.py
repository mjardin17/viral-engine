"""
council_status.py — Viral Engine Council
Quick one-screen pipeline health dashboard.
"""

import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).parent
RENDERS_DIR = BASE_DIR / "renders"
OUTPUT_DIR = BASE_DIR / "output"
REGISTRY_PATH = BASE_DIR / "script_registry.json"

def find_ffprobe() -> str:
    for c in ["ffprobe", r"C:\ffmpeg\bin\ffprobe.exe",
              r"C:\Program Files\ffmpeg\bin\ffprobe.exe"]:
        try:
            subprocess.run([c, "-version"], capture_output=True, check=True)
            return c
        except Exception:
            continue
    return "ffprobe"

def get_duration(path: Path, ffprobe: str) -> float:
    try:
        r = subprocess.run(
            [ffprobe, "-v", "quiet", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
            capture_output=True, text=True, timeout=10
        )
        return float(r.stdout.strip() or 0)
    except Exception:
        return 0.0

def load_registry() -> dict:
    if REGISTRY_PATH.exists():
        return json.loads(REGISTRY_PATH.read_text())
    return {}

def main():
    ffprobe = find_ffprobe()
    registry = load_registry()

    finals = sorted(RENDERS_DIR.glob("*_final.mp4"))

    print(f"\n{'='*72}")
    print(f"  VIRAL ENGINE — PIPELINE STATUS DASHBOARD")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*72}")
    print(f"\n  {'EPISODE':15s} {'DURATION':>10} {'SIZE':>8}  {'FINAL':8}  SCRIPT")
    print(f"  {'-'*65}")

    good = short = broken = 0
    script_issues = []

    for final in finals:
        ep_id = final.name.replace("_final.mp4", "")
        dur = get_duration(final, ffprobe)
        size_mb = final.stat().st_size / 1_048_576

        if dur >= 600:
            status = "GOOD"
            icon = "✓"
            good += 1
        elif dur >= 300:
            status = "SHORT"
            icon = "⚠"
            short += 1
        else:
            status = "BROKEN"
            icon = "✗"
            broken += 1

        dur_str = f"{dur:.0f}s ({dur/60:.1f}m)" if dur else "N/A"
        size_str = f"{size_mb:.0f}MB"

        # Script status from registry
        reg = registry.get(ep_id, {})
        if reg:
            # Count current clips in output
            ep_out = OUTPUT_DIR / ep_id
            current_clips = len(list(ep_out.glob("scene_[0-9][0-9].mp4"))) if ep_out.exists() else 0
            reg_scenes = reg.get("scene_count", 0)
            if current_clips < reg_scenes:
                script_note = f"⚠ clips {current_clips}/{reg_scenes}"
                script_issues.append(ep_id)
            else:
                script_note = f"✓ {reg_scenes} scenes"
        else:
            script_note = "(unregistered)"

        print(f"  {icon} {ep_id:14s} {dur_str:>10} {size_str:>8}  {status:8}  {script_note}")

    print(f"\n  Summary: {good} good  {short} short  {broken} broken")
    if script_issues:
        print(f"  Script warnings: {', '.join(script_issues)}")
    print()

    sys.exit(1 if (broken > 0 or script_issues) else 0)

if __name__ == "__main__":
    main()
