#!/usr/bin/env python3
"""
make_clip_windows.py — Standalone clip builder, no API keys required.
Uses: PIL (scene cards) + Windows SAPI TTS + FFmpeg

Usage:
    python make_clip_windows.py
    python make_clip_windows.py --episode GG_HIST_EP008
    python make_clip_windows.py --episode ML_EP001
    python make_clip_windows.py --scenes 5 6 7   # render specific scenes only
"""

import argparse
import json
import subprocess
import textwrap
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

# ── Config ────────────────────────────────────────────────────────────────────
WIDTH   = 1080
HEIGHT  = 1920
FPS     = 30
ZOOM    = 0.0005   # slow Ken Burns zoom rate

WINDOWS_FONTS = Path("C:/Windows/Fonts")
FONT_BOLD = WINDOWS_FONTS / "arialbd.ttf"
FONT_REG  = WINDOWS_FONTS / "arial.ttf"

BASE_DIR    = Path(__file__).resolve().parent
PROMPTS_DIR = BASE_DIR / "prompts"
WORK_DIR    = BASE_DIR / "work"
AUDIO_DIR   = BASE_DIR / "audio"
OUTPUT_DIR  = BASE_DIR / "output"


# ── Helpers ───────────────────────────────────────────────────────────────────
def hex_to_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))


def load_font(size, bold=False):
    primary = FONT_BOLD if bold else FONT_REG
    fallbacks = [
        Path("C:/Windows/Fonts/calibrib.ttf" if bold else "C:/Windows/Fonts/calibri.ttf"),
        Path("C:/Windows/Fonts/trebucbd.ttf" if bold else "C:/Windows/Fonts/trebuc.ttf"),
    ]
    for p in [primary] + fallbacks:
        try:
            return ImageFont.truetype(str(p), size)
        except Exception:
            pass
    return ImageFont.load_default()


def channel_label(channel, track=""):
    labels = {
        "GG": "GODS & GLORY",
        "ML": "MECH LEGENDS",
        "LO": "LITTLE OLYMPUS",
    }
    return labels.get(channel, channel)


# ── Scene card generator ──────────────────────────────────────────────────────
def make_card(scene, ep_meta, out_path):
    bg1 = hex_to_rgb(scene["bg_colors"][0])
    bg2 = hex_to_rgb(scene["bg_colors"][1])
    total = ep_meta["total_scenes"]
    channel = channel_label(ep_meta.get("channel", "GG"))
    ep_title = ep_meta["title"].upper()

    img = Image.new("RGB", (WIDTH, HEIGHT))
    draw = ImageDraw.Draw(img)

    # Gradient background
    for y in range(HEIGHT):
        t = y / HEIGHT
        r = int(bg1[0]*(1-t) + bg2[0]*t)
        g = int(bg1[1]*(1-t) + bg2[1]*t)
        b = int(bg1[2]*(1-t) + bg2[2]*t)
        draw.line([(0, y), (WIDTH, y)], fill=(r, g, b))

    # Vignette
    vig = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    vd = ImageDraw.Draw(vig)
    for i in range(300):
        a = int(200 * (1 - i/300))
        vd.rectangle([i, i, WIDTH-i, HEIGHT-i], outline=(0, 0, 0, a))
    img = Image.alpha_composite(img.convert("RGBA"), vig).convert("RGB")
    draw = ImageDraw.Draw(img)

    # Fonts
    title_font = load_font(86, bold=True)
    body_font  = load_font(52)
    brand_font = load_font(40, bold=True)
    num_font   = load_font(36)

    GOLD   = (200, 160, 50)
    WHITE  = (255, 255, 255)
    SILVER = (215, 215, 215)
    BLACK  = (0, 0, 0)

    # Scene counter top-left
    draw.text((70, 88), f"SCENE {scene['scene_number']:02d} / {total:02d}", font=num_font, fill=GOLD)

    # Channel brand top-right
    bb = draw.textbbox((0, 0), channel, font=brand_font)
    draw.text((WIDTH - 70 - (bb[2]-bb[0]), 82), channel, font=brand_font, fill=GOLD)

    # Top rule
    draw.line([(70, 172), (WIDTH-70, 172)], fill=GOLD, width=2)

    # Scene title — large, centered
    title_lines = textwrap.wrap(scene["title"].upper(), width=14)
    y = HEIGHT // 3 - 60
    for line in title_lines:
        bb = draw.textbbox((0, 0), line, font=title_font)
        tw = bb[2] - bb[0]
        x = (WIDTH - tw) // 2
        draw.text((x+4, y+4), line, font=title_font, fill=BLACK)
        draw.text((x, y), line, font=title_font, fill=WHITE)
        y += (bb[3] - bb[1]) + 16

    # Gold divider
    y += 32
    draw.line([(130, y), (WIDTH-130, y)], fill=GOLD, width=3)
    y += 52

    # Narration excerpt (shortened to fit)
    narration = scene["narration"]
    if len(narration) > 130:
        narration = narration[:130].rsplit(" ", 1)[0] + "…"
    for line in textwrap.wrap(narration, width=26):
        bb = draw.textbbox((0, 0), line, font=body_font)
        x = (WIDTH - (bb[2]-bb[0])) // 2
        draw.text((x+2, y+2), line, font=body_font, fill=BLACK)
        draw.text((x, y), line, font=body_font, fill=SILVER)
        y += (bb[3] - bb[1]) + 14

    # Bottom bar
    draw.rectangle([(0, HEIGHT-130), (WIDTH, HEIGHT)], fill=(8, 6, 6))
    bb = draw.textbbox((0, 0), ep_title, font=brand_font)
    draw.text(((WIDTH - (bb[2]-bb[0]))//2, HEIGHT - 96), ep_title, font=brand_font, fill=GOLD)

    img.save(str(out_path))
    print(f"  card  → {out_path.name}")


# ── Windows SAPI TTS ──────────────────────────────────────────────────────────
def tts_windows(text, wav_path):
    """Generate speech using Windows built-in SAPI via PowerShell."""
    safe = text.replace('"', "'").replace("\n", " ").replace("\\", "\\\\")
    ps = f"""
Add-Type -AssemblyName System.Speech
$s = New-Object System.Speech.Synthesis.SpeechSynthesizer
$s.Rate = -2
$s.Volume = 100
try {{ $s.SelectVoiceByHints([System.Speech.Synthesis.VoiceGender]::Male) }} catch {{}}
$s.SetOutputToWaveFile("{wav_path}")
$s.Speak("{safe}")
$s.Dispose()
"""
    result = subprocess.run(
        ["powershell", "-NoProfile", "-Command", ps],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        raise RuntimeError(f"TTS failed: {result.stderr}")
    print(f"  voice → {Path(wav_path).name}")


# ── FFmpeg scene segment ──────────────────────────────────────────────────────
def make_segment(img_path, audio_path, duration, out_path):
    zoom_expr = f"zoom='min(zoom+{ZOOM},1.08)':d={int(duration*FPS)}"
    vf = (
        f"scale={WIDTH}:{HEIGHT}:force_original_aspect_ratio=increase,"
        f"crop={WIDTH}:{HEIGHT},"
        f"zoompan={zoom_expr}:s={WIDTH}x{HEIGHT}:fps={FPS},"
        f"format=yuv420p"
    )
    subprocess.run([
        "ffmpeg", "-y",
        "-loop", "1", "-i", str(img_path),
        "-i", str(audio_path),
        "-t", str(duration),
        "-r", str(FPS),
        "-vf", vf,
        "-c:v", "libx264", "-preset", "medium", "-crf", "18",
        "-c:a", "aac", "-b:a", "192k",
        "-shortest", "-movflags", "+faststart",
        str(out_path),
    ], check=True, capture_output=True)
    print(f"  video → {out_path.name}")


# ── Main ──────────────────────────────────────────────────────────────────────
def find_episode_json(episode_id):
    matches = sorted(PROMPTS_DIR.glob(f"**/*{episode_id}*.json"))
    if not matches:
        raise FileNotFoundError(f"No JSON found for episode '{episode_id}' in {PROMPTS_DIR}")
    return matches[0]


def main():
    parser = argparse.ArgumentParser(description="Build a clip from episode JSON using Windows TTS.")
    parser.add_argument("--episode", default="GG_HIST_EP008",
                        help="Episode ID (default: GG_HIST_EP008)")
    parser.add_argument("--scenes", nargs="+", type=int, default=None,
                        help="Specific scene numbers to render (default: all)")
    parser.add_argument("--music", default=None,
                        help="Optional background music file (mp3/wav)")
    args = parser.parse_args()

    ep_path = find_episode_json(args.episode)
    ep = json.loads(ep_path.read_text(encoding="utf-8"))
    episode_id = ep["episode_id"]
    scenes = ep["scenes"]

    if args.scenes:
        scenes = [s for s in scenes if s["scene_number"] in args.scenes]
        print(f"Rendering scenes: {args.scenes}")

    ep_meta = {
        "title": ep["title"],
        "channel": ep.get("channel", "GG"),
        "total_scenes": len(ep["scenes"]),
    }

    cards_dir = WORK_DIR  / episode_id / "cards"
    audio_dir = AUDIO_DIR / episode_id
    segs_dir  = WORK_DIR  / episode_id / "segs"
    suffix    = "_standalone"
    out_path  = OUTPUT_DIR / f"{episode_id}{suffix}.mp4"

    for d in [cards_dir, audio_dir, segs_dir, OUTPUT_DIR]:
        d.mkdir(parents=True, exist_ok=True)

    print(f"\n{'='*50}")
    print(f"  {episode_id}  —  {ep['title']}")
    print(f"  Scenes: {len(scenes)}")
    print(f"  Output: {out_path.name}")
    print(f"{'='*50}\n")

    seg_paths = []
    for scene in scenes:
        n = scene["scene_number"]
        print(f"[{n:02d}/{ep_meta['total_scenes']:02d}] {scene['title']}")

        card_path = cards_dir / f"scene_{n:02d}.png"
        wav_path  = audio_dir / f"scene_{n:02d}.wav"
        seg_path  = segs_dir  / f"scene_{n:02d}_seg.mp4"

        make_card(scene, ep_meta, card_path)
        tts_windows(scene["narration"], str(wav_path))
        make_segment(card_path, wav_path, scene["duration_sec"], seg_path)
        seg_paths.append(seg_path)
        print()

    # Concatenate
    print("Concatenating scenes…")
    list_file = segs_dir / "list.txt"
    list_file.write_text("\n".join(f"file '{p}'" for p in seg_paths), encoding="utf-8")

    stitched = WORK_DIR / episode_id / f"{episode_id}_stitched.mp4"
    subprocess.run([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0",
        "-i", str(list_file), "-c", "copy", str(stitched),
    ], check=True, capture_output=True)

    # Optional background music
    if args.music:
        music_path = Path(args.music)
        if not music_path.is_absolute():
            music_path = BASE_DIR / music_path
        subprocess.run([
            "ffmpeg", "-y",
            "-i", str(stitched),
            "-stream_loop", "-1", "-i", str(music_path),
            "-filter_complex", "[1:a]volume=0.18[bgm];[0:a][bgm]amix=inputs=2:duration=first[a]",
            "-map", "0:v:0", "-map", "[a]",
            "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
            "-shortest", "-movflags", "+faststart",
            str(out_path),
        ], check=True, capture_output=True)
    else:
        import shutil
        shutil.copy2(stitched, out_path)

    size_mb = out_path.stat().st_size / 1024 / 1024
    print(f"\n{'='*50}")
    print(f"  DONE: {out_path}")
    print(f"  Size: {size_mb:.1f} MB")
    print(f"{'='*50}")
    print(f"\nReady to post: {out_path.name}")


if __name__ == "__main__":
    main()
