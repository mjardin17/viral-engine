"""
render_guardian.py — Viral Engine Council
Scans output folders for broken scene clips and short finals.
Usage:
    py render_guardian.py                  # check all episodes
    py render_guardian.py --episode GG_EP006
    py render_guardian.py --fix            # attempt re-render of 0KB clips
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).parent
OUTPUT_DIR = BASE_DIR / "output"
RENDERS_DIR = BASE_DIR / "renders"

# Thresholds
MIN_CLIP_BYTES = 500_000       # < 500KB = suspicious for a multi-second clip
MIN_FINAL_SECONDS = 300        # < 5 min final = broken
TARGET_FINAL_SECONDS = 600     # < 10 min = short warning


def find_ffmpeg() -> str:
    for candidate in ["ffmpeg", r"C:\ffmpeg\bin\ffmpeg.exe",
                      r"C:\Program Files\ffmpeg\bin\ffmpeg.exe"]:
        try:
            subprocess.run([candidate, "-version"], capture_output=True, check=True)
            return candidate
        except (FileNotFoundError, subprocess.CalledProcessError):
            continue
    return "ffmpeg"


def find_ffprobe() -> str:
    for candidate in ["ffprobe", r"C:\ffmpeg\bin\ffprobe.exe",
                      r"C:\Program Files\ffmpeg\bin\ffprobe.exe"]:
        try:
            subprocess.run([candidate, "-version"], capture_output=True, check=True)
            return candidate
        except (FileNotFoundError, subprocess.CalledProcessError):
            continue
    return "ffprobe"


def get_duration(path: Path, ffprobe: str) -> float:
    try:
        r = subprocess.run(
            [ffprobe, "-v", "quiet", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
            capture_output=True, text=True, timeout=15
        )
        return float(r.stdout.strip() or 0)
    except Exception:
        return 0.0


def check_episode(ep_dir: Path, ffprobe: str) -> dict:
    ep_id = ep_dir.name
    result = {
        "episode_id": ep_id,
        "clips": [],
        "broken_clips": [],
        "final_path": None,
        "final_duration": 0.0,
        "final_status": "missing",
        "overall": "ok",
    }

    # Check scene clips
    clips = sorted(ep_dir.glob("scene_[0-9][0-9].mp4"))
    for clip in clips:
        size = clip.stat().st_size
        dur = get_duration(clip, ffprobe) if size > 0 else 0.0
        info = {"name": clip.name, "size": size, "duration": dur, "status": "ok"}
        if size == 0:
            info["status"] = "empty"
            result["broken_clips"].append(clip.name)
        elif size < MIN_CLIP_BYTES:
            info["status"] = "tiny"
            result["broken_clips"].append(clip.name)
        result["clips"].append(info)

    # Check final
    final = RENDERS_DIR / f"{ep_id}_final.mp4"
    if final.exists():
        result["final_path"] = str(final)
        result["final_duration"] = get_duration(final, ffprobe)
        if result["final_duration"] < MIN_FINAL_SECONDS:
            result["final_status"] = "broken"
        elif result["final_duration"] < TARGET_FINAL_SECONDS:
            result["final_status"] = "short"
        else:
            result["final_status"] = "good"
    
    # Overall
    if result["broken_clips"] or result["final_status"] in ("broken", "missing"):
        result["overall"] = "broken"
    elif result["final_status"] == "short":
        result["overall"] = "short"

    return result


def try_fix_clip(ep_dir: Path, clip_name: str, ffmpeg: str) -> bool:
    """Attempt to re-render a broken scene clip from its audio + images."""
    num = clip_name.replace("scene_", "").replace(".mp4", "")
    audio = ep_dir / f"scene_{num}.mp3"
    out = ep_dir / clip_name

    if not audio.exists() or audio.stat().st_size == 0:
        print(f"     [SKIP] No audio for {clip_name}")
        return False

    # Collect images
    images = []
    for i in range(1, 5):
        img = ep_dir / f"scene_{num}_{i}.jpg"
        if not img.exists():
            img = ep_dir / f"scene_{num}_{i}.png"
        if img.exists() and img.stat().st_size > 5000:
            images.append(img)

    if not images:
        print(f"     [SKIP] No valid images for {clip_name}")
        return False

    # Get audio duration
    r = subprocess.run(
        ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(audio)],
        capture_output=True, text=True
    )
    try:
        total_dur = float(r.stdout.strip())
    except ValueError:
        total_dur = 30.0

    seg_dur = total_dur / len(images)
    W, H = 1920, 1080

    # Build filter_complex for Ken Burns
    inputs = []
    for img in images:
        inputs += ["-loop", "1", "-t", str(seg_dur), "-i", str(img)]

    filter_parts = []
    for idx in range(len(images)):
        filter_parts.append(
            f"[{idx}:v]scale=8000:-1,zoompan=z='min(zoom+0.0015,1.5)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
            f":d={int(seg_dur * 25)}:s={W}x{H}:fps=25[v{idx}]"
        )

    concat_inputs = "".join(f"[v{i}]" for i in range(len(images)))
    filter_parts.append(f"{concat_inputs}concat=n={len(images)}:v=1:a=0[vout]")
    filter_complex = ";".join(filter_parts)

    cmd = (
        [ffmpeg, "-y"]
        + inputs
        + ["-i", str(audio),
           "-filter_complex", filter_complex,
           "-map", "[vout]", "-map", f"{len(images)}:a",
           "-c:v", "libx264", "-preset", "fast", "-crf", "23",
           "-c:a", "aac", "-shortest", str(out)]
    )

    result = subprocess.run(cmd, capture_output=True, timeout=300)
    if result.returncode == 0 and out.exists() and out.stat().st_size > 10000:
        print(f"     [FIXED] {clip_name} rebuilt ({out.stat().st_size // 1024}KB)")
        return True
    else:
        print(f"     [FAIL] Could not rebuild {clip_name}")
        if out.exists() and out.stat().st_size == 0:
            out.unlink()
        return False


def main():
    parser = argparse.ArgumentParser(description="Viral Engine — Render Guardian")
    parser.add_argument("--episode", help="Check single episode (e.g. GG_EP006)")
    parser.add_argument("--fix", action="store_true", help="Attempt to fix broken clips")
    args = parser.parse_args()

    ffprobe = find_ffprobe()
    ffmpeg = find_ffmpeg() if args.fix else None

    if args.episode:
        ep_dirs = [OUTPUT_DIR / args.episode.upper()]
    else:
        ep_dirs = sorted(d for d in OUTPUT_DIR.iterdir()
                        if d.is_dir() and not d.name.startswith("_"))

    all_results = []
    any_broken = False

    print(f"\n{'='*60}")
    print(f"  VIRAL ENGINE — RENDER GUARDIAN")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}\n")

    for ep_dir in ep_dirs:
        if not ep_dir.exists():
            print(f"  {ep_dir.name}: NOT FOUND")
            continue

        r = check_episode(ep_dir, ffprobe)
        all_results.append(r)

        valid = len(r["clips"]) - len(r["broken_clips"])
        total = len(r["clips"])
        dur_str = f"{r['final_duration']:.0f}s ({r['final_duration']/60:.1f}min)" if r["final_duration"] else "N/A"

        if r["overall"] == "ok":
            icon = "✓"
        elif r["overall"] == "short":
            icon = "⚠"
        else:
            icon = "✗"
            any_broken = True

        print(f"  {icon} {r['episode_id']:15s}  clips={valid}/{total}  final={dur_str}  [{r['final_status']}]")

        if r["broken_clips"]:
            print(f"      Broken clips: {', '.join(r['broken_clips'])}")
            if args.fix:
                for clip_name in r["broken_clips"]:
                    print(f"    Attempting fix: {clip_name}…")
                    try_fix_clip(ep_dir, clip_name, ffmpeg)

    # Summary
    good = sum(1 for r in all_results if r["overall"] == "ok")
    short = sum(1 for r in all_results if r["overall"] == "short")
    broken = sum(1 for r in all_results if r["overall"] == "broken")
    print(f"\n  Summary: {good} good  {short} short  {broken} broken\n")

    # Write JSON report
    report = {
        "generated_at": datetime.now().isoformat(),
        "summary": {"good": good, "short": short, "broken": broken},
        "episodes": all_results,
    }
    report_path = BASE_DIR / "guardian_report.json"
    report_path.write_text(json.dumps(report, indent=2))
    print(f"  Report written → guardian_report.json\n")

    sys.exit(1 if any_broken else 0)


if __name__ == "__main__":
    main()
