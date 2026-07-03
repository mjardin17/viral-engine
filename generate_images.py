#!/usr/bin/env python3
"""
generate_images.py — AI image generation for any episode.

Backends:
  --openai   DALL-E 3 via OpenAI API (best quality, ~$0.04/image)
  --free     Pollinations.ai Flux model (no key, no cost, good quality)

Default: tries OpenAI if OPENAI_API_KEY is set, otherwise falls back to Pollinations.

Usage:
    python generate_images.py --episode ML_EP001
    python generate_images.py --episode GG_HIST_EP008 --openai
    python generate_images.py --episode ML_EP001 --free
    python generate_images.py --episode ML_EP001 --scenes 1 2 3
    python generate_images.py --episode ML_EP001 --skip-existing
"""

import argparse
import json
import os
import time
import urllib.parse
import urllib.request
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR    = Path(__file__).resolve().parent
PROMPTS_DIR = BASE_DIR / "prompts"
IMAGES_DIR  = BASE_DIR / "images"

# DALL-E 3 max supported size closest to 9:16 portrait
DALLE_SIZE = "1024x1792"

# Pollinations free API
POLLINATIONS_URL = (
    "https://image.pollinations.ai/prompt/{prompt}"
    "?width=1080&height=1920&model=flux&nologo=true&seed={seed}"
)

STYLE_SUFFIX = (
    "epic oil painting, cinematic composition, dramatic lighting, "
    "ultra detailed, 8k, vertical format, hyper realistic"
)


def find_episode_json(episode_id: str) -> Path:
    # exact match first
    matches = sorted(PROMPTS_DIR.glob(f"**/{episode_id}.json"))
    if not matches:
        matches = sorted(PROMPTS_DIR.glob(f"**/*{episode_id.lower()}*.json"))
    if not matches:
        raise FileNotFoundError(f"No JSON found for '{episode_id}' in {PROMPTS_DIR}")
    return matches[0]


# ── DALL-E 3 ──────────────────────────────────────────────────────────────────

def generate_dalle(prompt: str, out_path: Path, retries: int = 3) -> bool:
    try:
        from openai import OpenAI
    except ImportError:
        print("  openai package not installed — run: pip install openai")
        return False

    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("  OPENAI_API_KEY not set in .env")
        return False

    client = OpenAI(api_key=api_key)
    full_prompt = f"{prompt}, {STYLE_SUFFIX}"

    for attempt in range(1, retries + 1):
        try:
            print(f"  [{attempt}/{retries}] DALL-E 3 generating…")
            response = client.images.generate(
                model="dall-e-3",
                prompt=full_prompt,
                size=DALLE_SIZE,
                quality="standard",
                n=1,
            )
            image_url = response.data[0].url
            req = urllib.request.Request(image_url, headers={"User-Agent": "ViralEngine/1.0"})
            with urllib.request.urlopen(req, timeout=60) as resp:
                data = resp.read()
            out_path.parent.mkdir(parents=True, exist_ok=True)
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


# ── Pollinations (free) ───────────────────────────────────────────────────────

def generate_pollinations(prompt: str, out_path: Path, scene_num: int, retries: int = 3) -> bool:
    full_prompt = f"{prompt}, {STYLE_SUFFIX}"
    encoded = urllib.parse.quote(full_prompt, safe="")
    seed = 1000 + scene_num
    url = POLLINATIONS_URL.format(prompt=encoded, seed=seed)

    for attempt in range(1, retries + 1):
        try:
            print(f"  [{attempt}/{retries}] Pollinations generating…")
            req = urllib.request.Request(url, headers={"User-Agent": "ViralEngine/1.0"})
            with urllib.request.urlopen(req, timeout=60) as resp:
                data = resp.read()
            if len(data) < 1000:
                raise ValueError(f"Response too small ({len(data)} bytes)")
            out_path.parent.mkdir(parents=True, exist_ok=True)
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


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser(description="Generate scene images for an episode.")
    ap.add_argument("--episode", required=True, help="Episode ID, e.g. ML_EP001")
    ap.add_argument("--scenes", nargs="+", type=int, default=None,
                    help="Only generate specific scene numbers (default: all)")
    ap.add_argument("--skip-existing", action="store_true",
                    help="Skip scenes that already have an image file")
    ap.add_argument("--openai", action="store_true",
                    help="Force DALL-E 3 via OpenAI API")
    ap.add_argument("--free", action="store_true",
                    help="Force Pollinations (free, no key)")
    ap.add_argument("--delay", type=float, default=1.5,
                    help="Seconds between requests (default: 1.5)")
    args = ap.parse_args()

    # Decide backend
    load_dotenv()
    if args.free:
        backend = "pollinations"
    elif args.openai or os.getenv("OPENAI_API_KEY"):
        backend = "dalle"
    else:
        backend = "pollinations"

    ep_path = find_episode_json(args.episode)
    ep = json.loads(ep_path.read_text(encoding="utf-8"))
    episode_id = ep["episode_id"]
    scenes = ep["scenes"]

    if args.scenes:
        scenes = [s for s in scenes if s["scene_number"] in args.scenes]

    print(f"\n{'='*52}")
    print(f"  {episode_id}  —  {ep['title']}")
    print(f"  {len(scenes)} scene(s) to generate")
    print(f"  Backend: {'DALL-E 3 (OpenAI)' if backend == 'dalle' else 'Pollinations (free)'}")
    print(f"  Output:  images/{episode_id}/")
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

        if backend == "dalle":
            success = generate_dalle(scene["visual_prompt"], out_path)
        else:
            success = generate_pollinations(scene["visual_prompt"], out_path, n)

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
        print(f"\nNext step:")
        print(f"  python voice_video_pipeline.py --episode {episode_id}")
    print(f"{'='*52}")


if __name__ == "__main__":
    main()
