#!/usr/bin/env python3
"""
local_render.py

Empire Decoded — Local Video Production Engine
Generates finished MP4 episodes using FFmpeg + PIL.
No paid APIs required. Works entirely from local assets.

WHAT IT PRODUCES:
  - Title card (opening slate)
  - 6 cinematic scenes (Ken Burns zoom/pan on images, or dark card if no image)
  - Narration text burned as subtitles
  - Music track mixed under narration
  - Crossfade transitions between scenes
  - End card
  → Final EP_NNN.mp4

MOTION EFFECTS (applied to still images):
  zoom_in       - slow push-in (default)
  zoom_out      - slow pull-back
  pan_left      - slow drift left to right
  pan_right     - slow drift right to left
  pan_up        - slow drift bottom to top
  drift         - diagonal battlefield drift
  parallax      - layered depth zoom

USAGE:
  python3 local_render.py --episode 6
  python3 local_render.py --episode 6 --music path/to/music.mp3
  python3 local_render.py --episode 6 --narration-dir path/to/narrations/
  python3 local_render.py --episode 6 --preview        # first scene only
  python3 local_render.py --test                       # quick test render
"""

import argparse
import json
import os
import subprocess
import sys
import textwrap
import time
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter

ROOT = Path(__file__).parent
PROMPTS_DIR = ROOT / "prompts"
RENDERS_DIR = ROOT / "renders"
CHARACTER_IMAGES_DIR = ROOT / "character_images"
FONTS_DIR = ROOT / "assets" / "fonts"

# Video settings
W, H = 1920, 1080
FPS = 24
TRANSITION_DURATION = 0.5   # seconds crossfade between scenes
DEFAULT_SCENE_DURATION = 8   # seconds per scene if not specified

# Font paths (system fonts, DejaVu available everywhere)
FONT_BOLD   = "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf"
FONT_REGULAR = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"

# Colors (Empire Decoded dark cinematic palette)
COLOR_BG         = (8, 6, 4)        # near-black warm
COLOR_GOLD       = (201, 168, 76)   # gold accent
COLOR_WHITE      = (240, 235, 225)  # warm white text
COLOR_RED_ACCENT = (160, 40, 30)    # threat color
COLOR_SUBTITLE_BG = (0, 0, 0, 180) # semi-transparent black

MOTION_EFFECTS = [
    "zoom_in", "zoom_out", "pan_left", "pan_right", "pan_up", "drift"
]

# Scene type → motion effect mapping
SCENE_MOTION = {
    1: "zoom_out",    # Cold open / Threat — pull back to reveal scale
    2: "pan_right",   # Enemy Dominance — sweeping pan
    3: "drift",       # Crisis — diagonal unsteady drift
    4: "zoom_in",     # Turning Point — push in for intensity
    5: "pan_left",    # Victory — triumphant sweep
    6: "zoom_out",    # Legacy — pull back to show consequence
}

# Scene type → overlay color accent
SCENE_COLOR = {
    1: (100, 30, 20, 60),   # dark red tint — threat
    2: (20, 20, 60, 60),    # dark blue — enemy power
    3: (60, 40, 10, 80),    # dark orange — crisis
    4: (40, 60, 80, 40),    # steel blue — turning point
    5: (40, 70, 30, 40),    # dark green — victory
    6: (30, 30, 50, 50),    # dark purple — legacy
}


# ── PIL image generators ───────────────────────────────────────────────────────

def wrap_text(text: str, width: int) -> list[str]:
    """Wrap text to fit within pixel width (rough char estimate)."""
    chars_per_line = width // 22
    return textwrap.wrap(text, width=chars_per_line)


def make_title_card_image(
    title: str,
    subtitle: str = "",
    series: str = "EMPIRE DECODED",
    output_path: Path = None,
    accent_color: tuple = None,
) -> Path:
    """
    Generate a title card PNG: dark background, gold series name, white title.
    """
    accent_color = accent_color or COLOR_GOLD
    img = Image.new("RGB", (W, H), COLOR_BG)
    draw = ImageDraw.Draw(img)

    # Vignette overlay
    for i in range(200):
        alpha = int(120 * (i / 200) ** 2)
        draw.rectangle([i, i, W - i, H - i], outline=(0, 0, 0, alpha))

    # Horizontal gold line top
    draw.rectangle([120, 200, W - 120, 203], fill=accent_color)

    # Series name
    try:
        font_series = ImageFont.truetype(FONT_BOLD, 42)
    except Exception:
        font_series = ImageFont.load_default()
    draw.text((W // 2, 160), series, font=font_series, fill=accent_color, anchor="mm")

    # Main title
    try:
        font_title = ImageFont.truetype(FONT_BOLD, 88)
        font_title_sm = ImageFont.truetype(FONT_BOLD, 64)
    except Exception:
        font_title = font_title_sm = ImageFont.load_default()

    lines = wrap_text(title, W - 240)
    font = font_title if len(lines) <= 2 else font_title_sm
    y = H // 2 - (len(lines) * 70 // 2)
    for line in lines:
        draw.text((W // 2, y), line, font=font, fill=COLOR_WHITE, anchor="mm")
        y += 90

    # Horizontal gold line bottom
    draw.rectangle([120, H - 200, W - 120, H - 197], fill=accent_color)

    # Subtitle
    if subtitle:
        try:
            font_sub = ImageFont.truetype(FONT_REGULAR, 36)
        except Exception:
            font_sub = ImageFont.load_default()
        draw.text((W // 2, H - 165), subtitle, font=font_sub,
                  fill=(*accent_color, 200), anchor="mm")

    output_path = output_path or (RENDERS_DIR / "_tmp_title.png")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(str(output_path))
    return output_path


def make_scene_image(
    base_image_path: Path | None,
    caption: str,
    scene_number: int,
    scene_type_label: str,
    output_path: Path,
) -> Path:
    """
    Create a scene still PNG:
    - If base_image_path exists: use it, add cinematic color grade + caption
    - If not: dark card with scene type label + caption text
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    accent = SCENE_COLOR.get(scene_number, (40, 40, 60, 50))

    if base_image_path and base_image_path.exists():
        img = Image.open(str(base_image_path)).convert("RGB")
        # Fit to 16:9 canvas
        img = _fit_image_to_canvas(img, W, H)
        # Color grade overlay
        overlay = Image.new("RGBA", (W, H), accent)
        img = img.convert("RGBA")
        img = Image.alpha_composite(img, overlay).convert("RGB")
    else:
        img = _make_dark_scene_card(scene_type_label, scene_number)

    # Subtitle bar at bottom
    if caption:
        img = _add_subtitle(img, caption, scene_number)

    img.save(str(output_path))
    return output_path


def _fit_image_to_canvas(img: Image.Image, w: int, h: int) -> Image.Image:
    """Scale and crop image to fill w×h without distortion."""
    img_ratio = img.width / img.height
    canvas_ratio = w / h
    if img_ratio > canvas_ratio:
        new_h = h
        new_w = int(h * img_ratio)
    else:
        new_w = w
        new_h = int(w / img_ratio)
    img = img.resize((new_w, new_h), Image.LANCZOS)
    left = (new_w - w) // 2
    top = (new_h - h) // 2
    return img.crop((left, top, left + w, top + h))


def _make_dark_scene_card(scene_label: str, scene_number: int) -> Image.Image:
    """Dark cinematic placeholder card when no image is available."""
    img = Image.new("RGB", (W, H), COLOR_BG)
    draw = ImageDraw.Draw(img)

    # Scene number indicator (top left)
    try:
        font_num = ImageFont.truetype(FONT_BOLD, 28)
        font_label = ImageFont.truetype(FONT_BOLD, 72)
    except Exception:
        font_num = font_label = ImageFont.load_default()

    num_color = SCENE_COLOR.get(scene_number, (100, 100, 100, 255))[:3]

    draw.text((80, 60), f"SCENE {scene_number}", font=font_num, fill=num_color)
    draw.rectangle([80, 100, 280, 103], fill=num_color)

    # Scene label centered
    lines = wrap_text(scene_label.upper(), W - 300)
    y = H // 2 - len(lines) * 50
    for line in lines:
        draw.text((W // 2, y), line, font=font_label, fill=COLOR_WHITE, anchor="mm")
        y += 90

    return img


def _add_subtitle(img: Image.Image, text: str, scene_number: int) -> Image.Image:
    """Add subtitle text bar to bottom of image."""
    img = img.convert("RGBA")
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    try:
        font = ImageFont.truetype(FONT_REGULAR, 38)
    except Exception:
        font = ImageFont.load_default()

    lines = wrap_text(text, W - 160)[-3:]  # max 3 lines of subtitle
    line_h = 50
    bar_h = len(lines) * line_h + 40
    bar_y = H - bar_h - 40

    # Semi-transparent subtitle background
    draw.rectangle([0, bar_y - 10, W, H], fill=(0, 0, 0, 180))

    y = bar_y + 10
    for line in lines:
        draw.text((W // 2, y), line, font=font, fill=COLOR_WHITE, anchor="mm")
        y += line_h

    img = Image.alpha_composite(img, overlay)
    return img.convert("RGB")


# ── FFmpeg video clip builders ─────────────────────────────────────────────────

def _run_ffmpeg(cmd: list[str], label: str = "") -> bool:
    """Run an FFmpeg command, return True on success."""
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, check=True
        )
        return True
    except subprocess.CalledProcessError as e:
        print(f"  ✗ FFmpeg error ({label}): {e.stderr[-400:]}")
        return False


def ffmpeg_still_to_video(
    image_path: Path,
    output_path: Path,
    duration: float,
    effect: str = "zoom_in",
    fps: int = FPS,
) -> bool:
    """
    Convert a still image to a video clip with motion effect.
    Uses FFmpeg zoompan filter for Ken Burns-style movement.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    d_frames = int(duration * fps)

    # zoompan expressions per effect
    # z = zoom level, x/y = pan position, d = duration in frames
    # Start at 1.0 zoom, end at 1.08 for subtle movement
    effects = {
        "zoom_in": (
            f"z='if(lte(zoom,1.0),1.0,zoom-0.0008)':"
            f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={d_frames}"
        ),
        "zoom_out": (
            f"z='min(zoom+0.0008,1.08)':"
            f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={d_frames}"
        ),
        "pan_left": (
            f"z='1.05':"
            f"x='if(gte(x,iw*0.05),x-1,0)':y='ih/2-(ih/zoom/2)':d={d_frames}"
        ),
        "pan_right": (
            f"z='1.05':"
            f"x='if(lte(x,iw*0.02),x+1,iw*0.05)':y='ih/2-(ih/zoom/2)':d={d_frames}"
        ),
        "pan_up": (
            f"z='1.05':"
            f"x='iw/2-(iw/zoom/2)':y='if(gte(y,ih*0.05),y-1,0)':d={d_frames}"
        ),
        "drift": (
            f"z='1.04':"
            f"x='iw*0.02+n*0.3':y='ih*0.02+n*0.15':d={d_frames}"
        ),
    }

    zp = effects.get(effect, effects["zoom_in"])
    # Scale up image first so zoompan has room to move
    scale_filter = f"scale={W*2}:{H*2},zoompan={zp}:s={W}x{H},setsar=1,fps={fps}"

    cmd = [
        "ffmpeg", "-y",
        "-loop", "1",
        "-i", str(image_path),
        "-vf", scale_filter,
        "-t", str(duration),
        "-pix_fmt", "yuv420p",
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "22",
        str(output_path),
    ]
    return _run_ffmpeg(cmd, f"still→video {effect}")


def ffmpeg_add_text_overlay(
    video_path: Path,
    output_path: Path,
    text: str,
    position: str = "bottom",   # top | bottom | center
    font_size: int = 42,
    color: str = "white",
    box: bool = True,
    start_sec: float = 0.5,
    end_sec: float = None,
) -> bool:
    """Add text overlay / subtitle to an existing video."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Escape special chars for FFmpeg drawtext
    safe_text = text.replace("'", "\\'").replace(":", "\\:")

    # Wrap long text
    lines = wrap_text(text, 70)
    safe_text = "\\n".join(l.replace("'", "\\'").replace(":", "\\:") for l in lines)

    if position == "bottom":
        y_expr = f"h-th-80"
    elif position == "top":
        y_expr = "80"
    else:
        y_expr = "(h-th)/2"

    box_str = f":box=1:boxcolor=black@0.6:boxborderw=12" if box else ""
    enable_str = f":enable='between(t,{start_sec},{end_sec})'" if end_sec else f":enable='gte(t,{start_sec})'"

    vf = (
        f"drawtext=fontfile={FONT_REGULAR}"
        f":text='{safe_text}'"
        f":fontcolor={color}"
        f":fontsize={font_size}"
        f":x=(w-tw)/2"
        f":y={y_expr}"
        f":line_spacing=8"
        f"{box_str}"
        f"{enable_str}"
    )

    cmd = [
        "ffmpeg", "-y",
        "-i", str(video_path),
        "-vf", vf,
        "-c:v", "libx264", "-preset", "fast", "-crf", "22",
        "-c:a", "copy",
        str(output_path),
    ]
    return _run_ffmpeg(cmd, "text overlay")


def ffmpeg_concat_xfade(
    clips: list[Path],
    output_path: Path,
    transition_duration: float = TRANSITION_DURATION,
) -> bool:
    """
    Concatenate video clips with xfade crossfade transitions.
    Uses FFmpeg xfade filter chaining.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if len(clips) == 1:
        import shutil
        shutil.copy(str(clips[0]), str(output_path))
        return True

    # Get duration of each clip
    durations = []
    for clip in clips:
        dur = _get_video_duration(clip)
        if dur is None:
            print(f"  ✗ Could not get duration for {clip}")
            return False
        durations.append(dur)

    # Build xfade filter chain
    # xfade needs to know the offset (cumulative duration minus transition overlap)
    inputs = []
    for c in clips:
        inputs += ["-i", str(c)]

    if len(clips) == 2:
        offset = durations[0] - transition_duration
        filter_complex = (
            f"[0:v][1:v]xfade=transition=fade:duration={transition_duration}:offset={offset:.3f}[v]"
        )
        cmd = (
            ["ffmpeg", "-y"] + inputs +
            ["-filter_complex", filter_complex,
             "-map", "[v]",
             "-pix_fmt", "yuv420p",
             "-c:v", "libx264", "-preset", "fast", "-crf", "22",
             str(output_path)]
        )
        return _run_ffmpeg(cmd, "xfade 2 clips")

    # For 3+ clips, chain xfades
    filter_parts = []
    last_label = "[0:v]"
    cumulative = 0.0

    for i in range(len(clips) - 1):
        cumulative += durations[i] - transition_duration
        out_label = f"[v{i}]" if i < len(clips) - 2 else "[vout]"
        filter_parts.append(
            f"{last_label}[{i+1}:v]xfade=transition=fade:"
            f"duration={transition_duration}:offset={cumulative:.3f}{out_label}"
        )
        last_label = out_label

    filter_complex = ";".join(filter_parts)
    cmd = (
        ["ffmpeg", "-y"] + inputs +
        ["-filter_complex", filter_complex,
         "-map", "[vout]",
         "-pix_fmt", "yuv420p",
         "-c:v", "libx264", "-preset", "fast", "-crf", "22",
         str(output_path)]
    )
    return _run_ffmpeg(cmd, f"xfade {len(clips)} clips")


def ffmpeg_mix_audio(
    video_path: Path,
    output_path: Path,
    narration_path: Path | None = None,
    music_path: Path | None = None,
    narration_vol: float = 1.0,
    music_vol: float = 0.12,
) -> bool:
    """Mix narration and/or music onto video."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if not narration_path and not music_path:
        import shutil
        shutil.copy(str(video_path), str(output_path))
        return True

    inputs = ["-i", str(video_path)]
    if narration_path and narration_path.exists():
        inputs += ["-i", str(narration_path)]
    if music_path and music_path.exists():
        inputs += ["-i", str(music_path)]

    # Build audio filter
    audio_sources = []
    idx = 1
    if narration_path and narration_path.exists():
        audio_sources.append((idx, narration_vol))
        idx += 1
    if music_path and music_path.exists():
        audio_sources.append((idx, music_vol))
        idx += 1

    if len(audio_sources) == 1:
        src_idx, vol = audio_sources[0]
        af = f"[{src_idx}:a]volume={vol}[aout]"
    else:
        parts = []
        for src_idx, vol in audio_sources:
            parts.append(f"[{src_idx}:a]volume={vol}[a{src_idx}]")
        mix_inputs = "".join(f"[a{si}]" for si, _ in audio_sources)
        parts.append(f"{mix_inputs}amix=inputs={len(audio_sources)}:duration=first[aout]")
        af = ";".join(parts)

    cmd = (
        ["ffmpeg", "-y"] + inputs +
        ["-filter_complex", af,
         "-map", "0:v", "-map", "[aout]",
         "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
         "-shortest",
         str(output_path)]
    )
    return _run_ffmpeg(cmd, "audio mix")


def _get_video_duration(path: Path) -> float | None:
    """Get video duration in seconds using ffprobe."""
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(path),
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return float(result.stdout.strip())
    except Exception:
        return None


def ffmpeg_add_intro_slate(video_path: Path, output_path: Path,
                            slate_path: Path, slate_duration: float = 3.0) -> bool:
    """Prepend a slate (title card video) to the main video."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    concat_list = output_path.parent / "_slate_concat.txt"
    with open(concat_list, "w") as f:
        f.write(f"file '{slate_path}'\n")
        f.write(f"file '{video_path}'\n")
    cmd = [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0",
        "-i", str(concat_list),
        "-c:v", "libx264", "-preset", "fast", "-crf", "22",
        "-pix_fmt", "yuv420p",
        str(output_path),
    ]
    return _run_ffmpeg(cmd, "add intro slate")


# ── Main render pipeline ───────────────────────────────────────────────────────

class LocalRenderer:
    """
    Orchestrates the full local render pipeline for one episode.
    """

    def __init__(self, episode_number: int, music_path: Path | None = None,
                 narration_dir: Path | None = None, preview: bool = False):
        self.ep = episode_number
        self.ep_key = f"ep{episode_number:03d}"
        self.music_path = music_path
        self.narration_dir = narration_dir
        self.preview = preview

        # Directories
        self.work_dir = RENDERS_DIR / self.ep_key / "_work"
        self.work_dir.mkdir(parents=True, exist_ok=True)

        # Load episode script
        script_path = PROMPTS_DIR / f"scene_prompts.ep{episode_number:03d}.final.json"
        if not script_path.exists():
            raise FileNotFoundError(f"No script: {script_path}")
        with open(script_path) as f:
            self.episode = json.load(f)

        self.title = self.episode.get("title", f"Episode {episode_number}")
        self.scenes = self.episode.get("scenes", [])
        if self.preview:
            self.scenes = self.scenes[:1]

        # Character images available for this episode
        self.char_images = self._find_character_images()

    def _find_character_images(self) -> list[Path]:
        """Find PNG files in character_images/ that belong to this episode."""
        result = []
        ep_chars = self.episode.get("character_images", [])
        for char in ep_chars:
            p = CHARACTER_IMAGES_DIR / f"{char['label']}.png"
            if p.exists():
                result.append(p)
        # Also accept any loose PNGs if none matched
        if not result and CHARACTER_IMAGES_DIR.exists():
            result = list(CHARACTER_IMAGES_DIR.glob("*.png"))[:3]
        return result

    def _get_scene_image(self, scene_index: int) -> Path | None:
        """Pick a character image for a scene (cycle through available ones)."""
        if not self.char_images:
            return None
        return self.char_images[scene_index % len(self.char_images)]

    def _get_narration_audio(self, scene_number: int) -> Path | None:
        """Look for a narration audio file for this scene."""
        if not self.narration_dir:
            return None
        for pattern in [
            f"narration_s{scene_number:02d}.mp3",
            f"narration_{scene_number}.mp3",
            f"scene_{scene_number}_narration.mp3",
            f"s{scene_number:02d}.mp3",
        ]:
            p = Path(self.narration_dir) / pattern
            if p.exists():
                return p
        return None

    def render(self) -> Path:
        """Run the full pipeline. Returns path to final MP4."""
        print(f"\n{'='*60}")
        print(f"  Empire Decoded — Local Render")
        print(f"  Episode {self.ep:03d}: {self.title}")
        print(f"  Scenes: {len(self.scenes)}  Preview: {self.preview}")
        print(f"  Characters found: {len(self.char_images)}")
        print(f"{'='*60}\n")

        scene_clips = []

        for i, scene in enumerate(self.scenes):
            sn = scene.get("scene_number", i + 1)
            s_title = scene.get("title", f"Scene {sn}")
            narration = scene.get("narration", scene.get("description", ""))
            duration = float(scene.get("duration_sec", DEFAULT_SCENE_DURATION))
            effect = SCENE_MOTION.get(sn, "zoom_in")

            print(f"  Scene {sn}: {s_title} [{effect}, {duration}s]")

            # 1. Make scene still image (character + grade + subtitle)
            still_path = self.work_dir / f"still_s{sn:02d}.png"
            base_img = self._get_scene_image(i)
            make_scene_image(
                base_image_path=base_img,
                caption=narration,
                scene_number=sn,
                scene_type_label=s_title,
                output_path=still_path,
            )
            print(f"    ✓ Still image {'(character)' if base_img else '(text card)'}")

            # 2. Apply motion (Ken Burns / pan)
            motion_clip = self.work_dir / f"motion_s{sn:02d}.mp4"
            ok = ffmpeg_still_to_video(still_path, motion_clip, duration, effect=effect)
            if not ok:
                print(f"    ✗ Motion failed for scene {sn}, using static fallback")
                # fallback: simple loop
                cmd = [
                    "ffmpeg", "-y", "-loop", "1", "-i", str(still_path),
                    "-t", str(duration), "-pix_fmt", "yuv420p",
                    "-c:v", "libx264", "-preset", "fast",
                    str(motion_clip)
                ]
                _run_ffmpeg(cmd, "static fallback")

            print(f"    ✓ Motion clip ({effect})")

            # 3. Mix per-scene narration if available
            nar_audio = self._get_narration_audio(sn)
            if nar_audio:
                mixed_clip = self.work_dir / f"mixed_s{sn:02d}.mp4"
                ffmpeg_mix_audio(
                    video_path=motion_clip,
                    output_path=mixed_clip,
                    narration_path=nar_audio,
                    music_path=None,
                )
                scene_clips.append(mixed_clip)
                print(f"    ✓ Narration mixed")
            else:
                scene_clips.append(motion_clip)

        # ── Concatenate all scenes with crossfades ──────────────────────────
        print(f"\n  Concatenating {len(scene_clips)} scenes ...")
        assembled = self.work_dir / "assembled.mp4"
        ok = ffmpeg_concat_xfade(scene_clips, assembled, TRANSITION_DURATION)
        if not ok:
            print("  Falling back to simple concat (no transitions) ...")
            concat_list = self.work_dir / "concat.txt"
            with open(concat_list, "w") as f:
                for c in scene_clips:
                    f.write(f"file '{c}'\n")
            cmd = [
                "ffmpeg", "-y", "-f", "concat", "-safe", "0",
                "-i", str(concat_list), "-c", "copy", str(assembled)
            ]
            _run_ffmpeg(cmd, "simple concat")
        print(f"  ✓ Scenes assembled")

        # ── Title card ──────────────────────────────────────────────────────
        print(f"  Creating title card ...")
        title_img = self.work_dir / "title_card.png"
        make_title_card_image(
            title=self.title,
            subtitle="Empire Decoded",
            output_path=title_img,
        )
        title_clip = self.work_dir / "title_card.mp4"
        ffmpeg_still_to_video(title_img, title_clip, duration=4.0, effect="zoom_in")
        print(f"  ✓ Title card")

        # ── End card ────────────────────────────────────────────────────────
        end_img = self.work_dir / "end_card.png"
        make_title_card_image(
            title="Subscribe",
            subtitle="Empire Decoded — New Episode Every Week",
            accent_color=COLOR_GOLD,
            output_path=end_img,
        )
        end_clip = self.work_dir / "end_card.mp4"
        ffmpeg_still_to_video(end_img, end_clip, duration=3.0, effect="zoom_out")
        print(f"  ✓ End card")

        # ── Prepend title, append end card ──────────────────────────────────
        print(f"  Adding intro/outro ...")
        full_clips = [title_clip, assembled, end_clip]
        full_no_audio = self.work_dir / "full_no_audio.mp4"
        ok = ffmpeg_concat_xfade(full_clips, full_no_audio, 0.5)
        if not ok:
            concat_list2 = self.work_dir / "full_concat.txt"
            with open(concat_list2, "w") as f:
                for c in full_clips:
                    f.write(f"file '{c}'\n")
            cmd = [
                "ffmpeg", "-y", "-f", "concat", "-safe", "0",
                "-i", str(concat_list2), "-c", "copy", str(full_no_audio)
            ]
            _run_ffmpeg(cmd, "full concat")

        # ── Mix global music track ──────────────────────────────────────────
        final_path = RENDERS_DIR / f"EP_{self.ep:03d}.mp4"
        if self.preview:
            final_path = RENDERS_DIR / f"EP_{self.ep:03d}_preview.mp4"

        if self.music_path and Path(self.music_path).exists():
            print(f"  Mixing music track ...")
            ffmpeg_mix_audio(
                video_path=full_no_audio,
                output_path=final_path,
                music_path=Path(self.music_path),
                music_vol=0.12,
            )
            print(f"  ✓ Music mixed")
        else:
            import shutil
            shutil.copy(str(full_no_audio), str(final_path))
            print(f"  ⚠ No music track — video has no audio (upload music to add it)")

        # ── Result ──────────────────────────────────────────────────────────
        if final_path.exists():
            size_mb = final_path.stat().st_size / 1_000_000
            dur = _get_video_duration(final_path)
            print(f"\n{'='*60}")
            print(f"  ✓ DONE")
            print(f"  Output : {final_path}")
            print(f"  Size   : {size_mb:.1f} MB")
            if dur:
                print(f"  Length : {dur:.1f}s ({dur/60:.1f} min)")
            print(f"{'='*60}\n")
            return final_path
        else:
            raise RuntimeError(f"Render failed — output not found: {final_path}")


# ── Quick test render ──────────────────────────────────────────────────────────

def run_test_render():
    """
    Generate a 20-second test MP4 from scratch.
    No episode JSON required. Proves the pipeline works.
    """
    print("\n=== Empire Decoded — Test Render ===\n")
    RENDERS_DIR.mkdir(parents=True, exist_ok=True)
    work = RENDERS_DIR / "_test_work"
    work.mkdir(parents=True, exist_ok=True)

    test_scenes = [
        {"n": 1, "label": "THREAT",          "text": "Three hundred men. One narrow pass. One million enemies.", "effect": "zoom_out"},
        {"n": 2, "label": "ENEMY DOMINANCE", "text": "The Persian Empire stretched from Egypt to India. No army had ever stopped them.", "effect": "pan_right"},
        {"n": 3, "label": "TURNING POINT",   "text": "Leonidas held the pass for three days. History would never forget his name.", "effect": "zoom_in"},
    ]

    clips = []
    for s in test_scenes:
        # Create dark card image
        img_path = work / f"test_still_{s['n']}.png"
        still = _make_dark_scene_card(s["label"], s["n"])
        still = _add_subtitle(still, s["text"], s["n"])
        still.save(str(img_path))

        # Motion clip
        clip_path = work / f"test_clip_{s['n']}.mp4"
        ffmpeg_still_to_video(img_path, clip_path, duration=5.0, effect=s["effect"])
        clips.append(clip_path)
        print(f"  ✓ Scene {s['n']}: {s['label']}")

    # Title card
    title_img = work / "test_title.png"
    make_title_card_image("THE BATTLE OF THERMOPYLAE", "Empire Decoded — Test Render", output_path=title_img)
    title_clip = work / "test_title.mp4"
    ffmpeg_still_to_video(title_img, title_clip, duration=3.0, effect="zoom_in")

    # Assemble
    all_clips = [title_clip] + clips
    output = RENDERS_DIR / "TEST_RENDER.mp4"
    print(f"\n  Assembling {len(all_clips)} clips ...")
    ok = ffmpeg_concat_xfade(all_clips, output, 0.5)
    if not ok:
        concat_list = work / "test_concat.txt"
        with open(concat_list, "w") as f:
            for c in all_clips:
                f.write(f"file '{c}'\n")
        _run_ffmpeg(["ffmpeg", "-y", "-f", "concat", "-safe", "0",
                     "-i", str(concat_list), "-c", "copy", str(output)], "test concat")

    if output.exists():
        size = output.stat().st_size / 1_000_000
        dur = _get_video_duration(output)
        print(f"\n  ✓ TEST RENDER COMPLETE")
        print(f"  Output : {output}")
        print(f"  Size   : {size:.1f} MB")
        print(f"  Length : {dur:.1f}s")
        return output
    else:
        print("  ✗ Test render failed")
        return None


# ── CLI ────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Empire Decoded local video renderer")
    parser.add_argument("--episode", "-e", type=int, help="Episode number to render")
    parser.add_argument("--music", type=str, help="Path to music MP3 file")
    parser.add_argument("--narration-dir", type=str, help="Directory containing narration MP3 files")
    parser.add_argument("--preview", action="store_true", help="Render scene 1 only (quick preview)")
    parser.add_argument("--test", action="store_true", help="Run quick test render (no episode needed)")
    args = parser.parse_args()

    RENDERS_DIR.mkdir(parents=True, exist_ok=True)

    if args.test:
        out = run_test_render()
        if out:
            sys.exit(0)
        else:
            sys.exit(1)

    if not args.episode:
        parser.print_help()
        print("\nExamples:")
        print("  python3 local_render.py --test")
        print("  python3 local_render.py --episode 6")
        print("  python3 local_render.py --episode 6 --preview")
        print("  python3 local_render.py --episode 6 --music music.mp3 --narration-dir renders/ep006/")
        sys.exit(1)

    renderer = LocalRenderer(
        episode_number=args.episode,
        music_path=Path(args.music) if args.music else None,
        narration_dir=Path(args.narration_dir) if args.narration_dir else None,
        preview=args.preview,
    )
    output = renderer.render()
    print(f"MP4 ready: {output}")


if __name__ == "__main__":
    main()
