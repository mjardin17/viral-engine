"""
music_gen.py — Auto-generate epic orchestral background music for GG episodes
Uses HuggingFace MusicGen API (free tier, no credits)

Requires: HF_TOKEN in .env  (free at huggingface.co/settings/tokens)

Usage:
    python music_gen.py --prompt "epic orchestral battle" --duration 120 --out music/ep012.wav
    python music_gen.py --episode GG_EP012 --duration 600 --out music/gg_ep012.wav
"""

import argparse
import os
import sys
import time
import urllib.request
import urllib.error
import json
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

HF_TOKEN = os.getenv("HF_TOKEN", "")

# MusicGen stereo gives best quality for cinematic use
# Options: facebook/musicgen-small | facebook/musicgen-medium | facebook/musicgen-stereo-small | facebook/musicgen-stereo-medium
MODEL = "facebook/musicgen-stereo-medium"
HF_API_URL = f"https://api-inference.huggingface.co/models/{MODEL}"

# Genre prompts per channel — keeps music consistent and on-brand
CHANNEL_PROMPTS = {
    "GG": (
        "epic cinematic orchestral battle music, powerful brass fanfare, war drums, "
        "dramatic strings, majestic and powerful, no vocals, history documentary "
        "background score, cinematic tension builds"
    ),
    "LO": (
        "playful whimsical kids adventure music, bright flutes and pizzicato strings, "
        "fun and magical, ancient Greek mythology theme, upbeat and cheerful, no vocals"
    ),
    "IL": (
        "80s anime synth orchestral hybrid, dramatic mech battle theme, "
        "powerful brass meets synthesizer, action and tension, no vocals"
    ),
    "ED": (
        "modern tech documentary music, electronic ambient with orchestral elements, "
        "forward-thinking and intelligent, no vocals, AI and innovation theme"
    ),
}


def generate_music(
    prompt: str,
    duration: int = 120,
    out_path: str = "music/output.wav",
) -> bool:
    """
    Generate music via HuggingFace MusicGen API.

    Args:
        prompt: Text description of the music to generate
        duration: Duration in seconds (max 300 for free tier)
        out_path: Output WAV file path

    Returns:
        True if successful
    """
    if not HF_TOKEN:
        print(
            "[music_gen] ❌ HF_TOKEN not set in .env\n"
            "  Get a free token at: https://huggingface.co/settings/tokens\n"
            "  Add to .env: HF_TOKEN=hf_xxxxxxxxxxxxxx",
            file=sys.stderr,
        )
        return False

    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)

    payload = json.dumps({
        "inputs": prompt,
        "parameters": {
            "max_new_tokens": duration * 50,  # ~50 tokens per second
            "do_sample": True,
            "guidance_scale": 3.0,
        }
    }).encode("utf-8")

    headers = {
        "Authorization": f"Bearer {HF_TOKEN}",
        "Content-Type": "application/json",
    }

    print(f"[music_gen] Generating {duration}s of music...")
    print(f"[music_gen] Prompt: {prompt[:80]}...")
    print(f"[music_gen] Model: {MODEL}")

    # HuggingFace may return 503 while model loads — retry up to 3 times
    for attempt in range(1, 4):
        req = urllib.request.Request(HF_API_URL, data=payload, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=300) as resp:
                if resp.status == 200:
                    audio_bytes = resp.read()
                    with open(out_path, "wb") as f:
                        f.write(audio_bytes)
                    size_kb = len(audio_bytes) // 1024
                    print(f"[music_gen] ✅ Saved {out_path} ({size_kb}KB)")
                    return True
                else:
                    body = resp.read().decode()
                    print(f"[music_gen] HTTP {resp.status}: {body[:200]}", file=sys.stderr)
        except urllib.error.HTTPError as e:
            body = e.read().decode()
            if e.code == 503 and "loading" in body.lower():
                wait = 20 * attempt
                print(f"[music_gen] Model loading, retrying in {wait}s... (attempt {attempt}/3)")
                time.sleep(wait)
                continue
            print(f"[music_gen] HTTP {e.code}: {body[:300]}", file=sys.stderr)
            return False
        except Exception as e:
            print(f"[music_gen] Error: {e}", file=sys.stderr)
            if attempt < 3:
                time.sleep(10)
                continue
            return False

    print("[music_gen] ❌ All attempts failed", file=sys.stderr)
    return False


def get_or_generate(
    channel: str,
    episode_id: str,
    duration: int = 600,
    music_dir: str = "music",
) -> str | None:
    """
    Get cached music file or generate a new one for the episode.
    Caches by episode ID so we never regenerate the same track twice.

    Returns path to music file, or None on failure.
    """
    out_path = os.path.join(music_dir, f"{episode_id.lower()}_bg.wav")

    # Return cached version if it exists
    if os.path.exists(out_path) and os.path.getsize(out_path) > 10000:
        print(f"[music_gen] Using cached: {out_path}")
        return out_path

    # Get channel-specific prompt
    prompt = CHANNEL_PROMPTS.get(channel.upper(), CHANNEL_PROMPTS["GG"])

    ok = generate_music(prompt, duration=min(duration, 300), out_path=out_path)
    return out_path if ok else None


def main():
    parser = argparse.ArgumentParser(description="Generate background music for Empire OS pipeline")
    parser.add_argument("--prompt", default=None, help="Custom music prompt")
    parser.add_argument("--channel", default="GG", choices=["GG", "LO", "IL", "ED"],
                        help="Channel preset (uses built-in prompt if --prompt not set)")
    parser.add_argument("--episode", default=None, help="Episode ID for caching (e.g. GG_EP012)")
    parser.add_argument("--duration", type=int, default=120, help="Duration in seconds (max 300)")
    parser.add_argument("--out", default=None, help="Output WAV file path")
    args = parser.parse_args()

    prompt = args.prompt or CHANNEL_PROMPTS.get(args.channel, CHANNEL_PROMPTS["GG"])

    if args.out:
        out = args.out
    elif args.episode:
        out = f"music/{args.episode.lower()}_bg.wav"
    else:
        out = f"music/{args.channel.lower()}_theme.wav"

    ok = generate_music(prompt, duration=args.duration, out_path=out)
    if ok:
        print(f"[music_gen] Done: {out}")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
