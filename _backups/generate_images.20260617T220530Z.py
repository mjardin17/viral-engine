#!/usr/bin/env python3
"""
generate_images.py — Free AI image generation for any episode.
No API key, no credits, no account required.

Uses Pollinations.ai (free public API, Flux model) to generate
1080x1920 images from visual_prompt fields and saves them where
voice_video_pipeline.py expects them.

Usage:
    python generate_images.py --episode GG_HIST_EP008
    python generate_images.py --episode ML_EP001 --scenes 3 4 5
    python generate_images.py --episode GG_HIST_EP008 --skip-existing

Requirements: pip install requests pillow
"""

import argparse
import json
import time
import urllib.parse
import urllib.request
from pathlib import Path

BASE_DIR    = Path(__file__).resolve().parent
PROMPTS_DIR = BASE_DIR / "prompts"
IMAGES_DIR  = BASE_DIR / "images"

WIDTH  = 1080
HEIGHT = 1920

# Pollinations.ai — free, no key, Flux model
# Docs: https://pollinations.ai
POLLINATIONS_URL = "https://image.pollinations.ai/prompt/{prompt}?width={w}&height={h}&model=flux&nologo=true&seed={seed}"

# Style suffix appended to every prompt for cinematic consistency
STYLE_SUFFIX = (
    "epic oil painting, cinematic composition, dramatic lighting, "
    "ultra detailed, 8k, vertical format, hyper realistic"
)


def find_episode_json(episode_id: str) -> Path:
    matches = sorted(PROMPTS_DIR.glob(f"**/*{episode_id}*.json"))
    if not matches:
        raise FileNotFoundError(f"No JSON found for '{episode_id}' in {PROMPTS_DIR}")
    return matches[0]


def download_image(prompt: str, out_path: Path, scene_num: int, retries: int = 3) -> bool:
    """Download one image from Pollinations. Returns True on success."""
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # Clean and encode prompt
    full_prompt = f"{prompt}, {STYLE_SUFFIX}"
    encoded = urllib.parse.quote(full_prompt, safe="")
    seed = 1000 + scene_num  # deterministic seed per scene so re-runs are consistent
    url = POLLINATIONS_URL.format(prompt=encoded, w=WIDTH, h=HEIGHT, seed=seed)

    for attempt in range(1, retries + 1):
        try:
            print(f"  [{attempt}/{retries}] Generating…")
            req = urllib.request.Request(url, headers={"User-Agent": "ViralEngine/1.0"})
            with urllib.request.urlopen(req, timeout=60) as resp:
                data = resp.read()
            if len(data) < 1000:
                raise ValueError(f"Response too small ({len(data)} bytes) — likely an error page")
            out_path.write_bytes(data)
            size_kb = len(data) // 1024
            print(f"  saved  → {out_path.name}  ({size_kb} KB)")
            return True
        except Exception as e:
            print(f"  error: {e}")
            if attempt < retries:
                wait = 5 * attempt
                print(f"  retrying in {wait}s…")
                time.sleep(wait)
    return False


def main():
    ap = argparse.ArgumentParser(description="Generate scene images for an episode (free, no API key).")
    ap.add_argument("--episode", required=True, help="Episode ID, e.g. GG_HIST_EP008")
    ap.add_argument("--scenes", nargs="+", type=int, default=None,
                    help="Only generate specific scene numbers (default: all)")
    ap.add_argument("--skip-existing", action="store_true",
                    help="Skip scenes that already have an image file")
    ap.add_argument("--delay", type=float, default=2.0,
                    help="Seconds between requests (default: 2.0)")
    args = ap.parse_args()

    ep_path = find_episode_json(args.episode)
    ep = json.loads(ep_path.read_text(encoding="utf-8"))
    episode_id = ep["episode_id"]
    scenes = ep["scenes"]

    if args.scenes:
        scenes = [s for s in scenes if s["scene_number"] in args.scenes]

    print(f"\n{'='*52}")
    print(f"  {episode_id}  —  {ep['title']}")
    print(f"  {len(scenes)} scene(s) to generate")
    print(f"  Output: images/{episode_id}/")
    print(f"  Model: Pollinations Flux (free)")
    print(f"{'='*52}\n")

    ok = 0
    fail = 0

    for scene in scenes:
        n = scene["scene_number"]
        out_path = IMAGES_DIR / episode_id / f"scene_{n:02d}.png"

        print(f"[{n:02d}/{len(ep['scenes']):02d}] {scene.get('title', '')}")

        if args.skip_existing and out_path.exists():
            print(f"  exists, skipping\n")
            ok += 1
            continue

        success = download_image(scene["visual_prompt"], out_path, n)
        if success:
            ok += 1
        else:
            fail += 1
            print(f"  FAILED — will use black frame in pipeline\n")
            continue

        if scene != scenes[-1]:
            time.sleep(args.delay)
        print()

    print(f"{'='*52}")
    print(f"  Done: {ok} generated, {fail} failed")
    if ok > 0:
        print(f"\nRun the pipeline:")
        print(f"  python voice_video_pipeline.py --episode {episode_id}")
    print(f"{'='*52}")


if __name__ == "__main__":
    main()
